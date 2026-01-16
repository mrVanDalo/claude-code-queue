"""
Queue manager with execution loop.
"""

import signal
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from .claude_interface import ClaudeCodeInterface
from .jj_integration import JujutsuIntegration
from .models import ExecutionResult, PromptStatus, QueuedPrompt, QueueState
from .storage import QueueStorage


class QueueManager:
    """Manages the queue execution lifecycle."""

    def __init__(
        self,
        storage_dir: str = "~/.claude-queue",
        claude_command: str = "claude",
        check_interval: int = 30,
        timeout: int = 3600,
    ):
        self.storage = QueueStorage(storage_dir)
        self.claude_interface = ClaudeCodeInterface(claude_command, timeout)
        self.check_interval = check_interval
        self.running = False
        self.state: Optional[QueueState] = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.stop()

    def start(self, callback: Optional[Callable[[QueueState], None]] = None) -> None:
        """Start the queue processing loop."""
        print("Starting Claude Code Queue Manager...")

        is_working, message = self.claude_interface.test_connection()
        if not is_working:
            print(f"Error: {message}")
            return

        print(f"✓ {message}")

        self.state = self.storage.load_queue_state()
        print(f"✓ Loaded queue with {len(self.state.prompts)} prompts")

        self.running = True

        try:
            while self.running:
                self._process_queue_iteration(callback)

                if self.running:
                    # Calculate optimal sleep interval based on next reset time
                    sleep_interval = self._calculate_sleep_interval()
                    if sleep_interval > 0:
                        time.sleep(sleep_interval)

        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Error in queue processing: {e}")
        finally:
            self._shutdown()

    def process_next(
        self, callback: Optional[Callable[[QueueState], None]] = None
    ) -> int:
        """Process only the next queue item and stop."""
        print("Processing next queue item...")

        is_working, message = self.claude_interface.test_connection()
        if not is_working:
            print(f"Error: {message}")
            return 1

        print(f"✓ {message}")

        self.state = self.storage.load_queue_state()
        print(f"✓ Loaded queue with {len(self.state.prompts)} prompts")

        try:
            self._process_queue_iteration(callback)
            return 0

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            return 130
        except Exception as e:
            print(f"Error in queue processing: {e}")
            return 1
        finally:
            if self.state:
                for prompt in self.state.prompts:
                    if prompt.status == PromptStatus.EXECUTING:
                        prompt.status = PromptStatus.QUEUED
                        prompt.add_log("Execution interrupted")

                self.storage.save_queue_state(self.state)
                print("✓ Queue state saved")

    def stop(self) -> None:
        """Stop the queue processing loop."""
        self.running = False

    def _shutdown(self) -> None:
        """Clean shutdown procedure."""
        print("Shutting down...")

        if self.state:
            for prompt in self.state.prompts:
                if prompt.status == PromptStatus.EXECUTING:
                    prompt.status = PromptStatus.QUEUED
                    prompt.add_log("Execution interrupted during shutdown")

            self.storage.save_queue_state(self.state)
            print("✓ Queue state saved")

        print("Queue manager stopped")

    def _process_queue_iteration(
        self, callback: Optional[Callable[[QueueState], None]] = None
    ) -> None:
        """Process one iteration of the queue."""
        previous_total_processed = self.state.total_processed if self.state else 0
        previous_failed_count = self.state.failed_count if self.state else 0
        previous_rate_limited_count = self.state.rate_limited_count if self.state else 0
        previous_last_processed = self.state.last_processed if self.state else None

        # fixme : this is very bad hack, and should be properly done.
        # self.state should have a reload_queue_state function, which does this here internally.
        if self.state:
            current_rate_limit = self.state.current_rate_limit
            self.state = self.storage.load_queue_state()
            self.state.current_rate_limit = current_rate_limit
        else:
            self.state = self.storage.load_queue_state()

        self.state.total_processed = max(
            self.state.total_processed, previous_total_processed
        )
        self.state.failed_count = max(self.state.failed_count, previous_failed_count)
        self.state.rate_limited_count = max(
            self.state.rate_limited_count, previous_rate_limited_count
        )
        if previous_last_processed and (
            not self.state.last_processed
            or self.state.last_processed < previous_last_processed
        ):
            self.state.last_processed = previous_last_processed

        # Check if rate limit has expired
        if self.state.clear_rate_limit_if_expired():
            print("Rate limit expired, resuming queue processing")

        next_prompt = self.state.get_next_prompt()

        if next_prompt is None:
            # Check if we're rate limited
            if self.state.is_rate_limited():
                queued_count = len(
                    [p for p in self.state.prompts if p.status == PromptStatus.QUEUED]
                )
                if (
                    self.state.current_rate_limit
                    and self.state.current_rate_limit.reset_time
                ):
                    now = datetime.now()
                    seconds_until_reset = (
                        self.state.current_rate_limit.reset_time - now
                    ).total_seconds()
                    if seconds_until_reset > 0:
                        reset_str = self._format_duration(seconds_until_reset)
                        print(
                            f"Rate limited ({queued_count} prompts queued, reset in {reset_str})"
                        )
                    else:
                        print(f"Rate limited ({queued_count} prompts queued)")
                else:
                    print(f"Rate limited ({queued_count} prompts queued)")
            else:
                print("No prompts in queue")

            if callback:
                callback(self.state)
            return

        print(f"⏳ Executing prompt {next_prompt.id}: {next_prompt.content[:50]}...")
        self._execute_prompt(next_prompt)

        self.storage.save_queue_state(self.state)

        if callback:
            callback(self.state)

    def _execute_prompt(self, prompt: QueuedPrompt) -> None:
        """Execute a single prompt."""
        prompt.status = PromptStatus.EXECUTING
        prompt.last_executed = datetime.now()
        prompt.add_log(
            f"Started execution (attempt {prompt.retry_count + 1}/{prompt.max_retries})"
        )

        self.storage.save_queue_state(self.state)

        result = self.claude_interface.execute_prompt(prompt)

        self._process_execution_result(prompt, result)

    def _process_execution_result(
        self, prompt: QueuedPrompt, result: ExecutionResult
    ) -> None:
        """Process the result of prompt execution."""
        execution_summary = f"Execution completed in {result.execution_time:.1f}s"

        if result.success:
            prompt.status = PromptStatus.COMPLETED
            prompt.add_log(f"{execution_summary} - SUCCESS")
            if result.output:
                prompt.add_log(f"Output:\n{result.output}")

            # Handle jj bookmark setting on success
            if result.jj_bookmark_to_set and result.jj_working_dir:
                bookmark_exists = JujutsuIntegration.bookmark_exists(
                    result.jj_working_dir, result.jj_bookmark_to_set
                )
                success, message = JujutsuIntegration.set_bookmark(
                    result.jj_working_dir,
                    result.jj_bookmark_to_set,
                    create=not bookmark_exists,
                )
                if success:
                    print(f"🥷 {message}")
                    prompt.add_log(f"jj bookmark: {message}")
                else:
                    print(f"🥷 Warning: {message}")
                    prompt.add_log(f"jj bookmark warning: {message}")

            self.state.total_processed += 1
            print(
                f"✓ Prompt {prompt.id} completed successfully ({result.execution_time:.1f}s)"
            )

        elif result.is_rate_limited:
            # Keep prompt in queued state - rate limit is a daemon-level concern
            prompt.status = PromptStatus.QUEUED
            prompt.add_log(
                f"{execution_summary} - RATE LIMITED (will retry when limit resets)"
            )

            if result.rate_limit_info and result.rate_limit_info.limit_message:
                prompt.add_log(f"Message: {result.rate_limit_info.limit_message}")

            # Set daemon-level rate limit
            self.state.current_rate_limit = result.rate_limit_info
            self.state.rate_limited_count += 1

            if result.rate_limit_info and result.rate_limit_info.reset_time:
                time_until_reset = (
                    result.rate_limit_info.reset_time - datetime.now()
                ).total_seconds()
                reset_str = self._format_duration(time_until_reset)
                print(f"⚠ Rate limited, will resume in {reset_str}")
            else:
                print("⚠ Rate limited, will retry later")

        else:
            prompt.retry_count += 1

            if prompt.can_retry():
                prompt.status = PromptStatus.QUEUED
                prompt.add_log(f"{execution_summary} - FAILED (will retry)")
                if result.error:
                    prompt.add_log(f"Error: {result.error}")
                print(
                    f"✗ Prompt {prompt.id} failed, will retry ({prompt.retry_count}/{prompt.max_retries}) ({result.execution_time:.1f}s)"
                )
            else:
                prompt.status = PromptStatus.FAILED
                prompt.add_log(f"{execution_summary} - FAILED (max retries exceeded)")
                if result.error:
                    prompt.add_log(f"Error: {result.error}")

                self.state.failed_count += 1
                print(
                    f"✗ Prompt {prompt.id} failed permanently after {prompt.max_retries} attempts ({result.execution_time:.1f}s)"
                )

        self.state.last_processed = datetime.now()

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format."""
        if seconds < 0:
            return "now"

        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes}m"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if minutes == 0:
                return f"{hours}h"
            return f"{hours}h {minutes}m"

    def _calculate_sleep_interval(self) -> int:
        """Calculate optimal sleep interval based on queue state and reset times."""
        if not self.state:
            return self.check_interval

        # Check if we're rate limited at the daemon level
        if self.state.is_rate_limited():
            if (
                self.state.current_rate_limit
                and self.state.current_rate_limit.reset_time
            ):
                now = datetime.now()
                seconds_until_reset = (
                    self.state.current_rate_limit.reset_time - now
                ).total_seconds()

                if seconds_until_reset <= 0:
                    # Reset time has passed, check immediately
                    return 0

                # Wait until reset time, but cap at check_interval to allow for interrupts
                # Add a small buffer (5 seconds) to ensure we don't check too early
                wait_time = min(seconds_until_reset + 5, self.check_interval)

                # If the wait time is significant, log it
                if wait_time > 60:
                    reset_str = self._format_duration(seconds_until_reset)
                    print(f"Waiting {reset_str} until rate limit reset...")

                return int(wait_time)

        # Check if there are any queued prompts
        queued_prompts = [
            p for p in self.state.prompts if p.status == PromptStatus.QUEUED
        ]
        if not queued_prompts:
            # No prompts waiting, use normal check interval
            return self.check_interval

        # If there are queued prompts and no rate limit, use the normal check interval
        return self.check_interval

    def add_prompt(self, prompt: QueuedPrompt) -> bool:
        """Add a prompt to the queue."""
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            self.state.add_prompt(prompt)

            success = self.storage.save_queue_state(self.state)
            if success:
                print(f"✓ Added prompt {prompt.id} to queue")
            else:
                print(f"✗ Failed to save prompt {prompt.id}")

            return success

        except Exception as e:
            print(f"Error adding prompt: {e}")
            return False

    def remove_prompt(self, prompt_id: str) -> bool:
        """Remove a prompt from the queue."""
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            prompt = self.state.get_prompt(prompt_id)
            if prompt:
                if prompt.status == PromptStatus.EXECUTING:
                    print(f"Cannot remove executing prompt {prompt_id}")
                    return False

                prompt.status = PromptStatus.CANCELLED
                prompt.add_log("Cancelled by user")

                success = self.storage.save_queue_state(self.state)
                if success:
                    print(f"✓ Cancelled prompt {prompt_id}")
                else:
                    print(f"✗ Failed to cancel prompt {prompt_id}")

                return success
            else:
                print(f"Prompt {prompt_id} not found")
                return False

        except Exception as e:
            print(f"Error removing prompt: {e}")
            return False

    def delete_prompt(self, prompt_id: str) -> bool:
        """Permanently delete a prompt from storage (hard delete)."""
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            prompt = self.state.get_prompt(prompt_id)
            if prompt:
                if prompt.status == PromptStatus.EXECUTING:
                    print(f"Cannot delete executing prompt {prompt_id}")
                    return False

                # Remove from state
                removed_from_state = self.state.delete_prompt(prompt_id)

                # Delete files from storage
                files_deleted = self.storage.delete_prompt_files(prompt_id)

                if removed_from_state or files_deleted:
                    # Save updated state
                    self.storage.save_queue_state(self.state)
                    print(f"✓ Deleted prompt {prompt_id}")
                    return True
                else:
                    print(f"✗ Failed to delete prompt {prompt_id}")
                    return False
            else:
                # Prompt not in memory, but might exist in files - try deleting files anyway
                files_deleted = self.storage.delete_prompt_files(prompt_id)
                if files_deleted:
                    print(f"✓ Deleted prompt {prompt_id} (files only)")
                    return True
                else:
                    print(f"Prompt {prompt_id} not found")
                    return False

        except Exception as e:
            print(f"Error deleting prompt: {e}")
            return False

    def retry_prompt(self, prompt_id: str, delete_after_success: bool = False) -> bool:
        """Retry a failed prompt by creating a new task with the same parameters.

        Args:
            prompt_id: The ID of the prompt to retry
            delete_after_success: If True, delete the original prompt after successfully creating the new one

        Returns:
            True if the retry was successful, False otherwise
        """
        try:
            if not self.state:
                self.state = self.storage.load_queue_state()

            original_prompt = self.state.get_prompt(prompt_id)
            if not original_prompt:
                print(f"Prompt {prompt_id} not found")
                return False

            # Create a new prompt with the same parameters
            new_prompt = QueuedPrompt(
                content=original_prompt.content,
                working_directory=original_prompt.working_directory,
                priority=original_prompt.priority,
                context_files=original_prompt.context_files,
                max_retries=original_prompt.max_retries,
                estimated_tokens=original_prompt.estimated_tokens,
                permission_mode=original_prompt.permission_mode,
                allowed_tools=original_prompt.allowed_tools,
                timeout=original_prompt.timeout,
                model=original_prompt.model,
                bookmark=original_prompt.bookmark,
            )

            self.state.add_prompt(new_prompt)

            success = self.storage.save_queue_state(self.state)
            if success:
                print(f"✓ Created new prompt {new_prompt.id} based on {prompt_id}")

                # Only delete the original if the new prompt was successfully created
                if delete_after_success:
                    # Remove from state
                    removed_from_state = self.state.delete_prompt(prompt_id)

                    # Delete files from storage
                    files_deleted = self.storage.delete_prompt_files(prompt_id)

                    if removed_from_state or files_deleted:
                        # Save updated state again after deletion
                        self.storage.save_queue_state(self.state)
                        print(f"✓ Deleted original prompt {prompt_id}")
                    else:
                        print(
                            f"⚠ Warning: Failed to delete original prompt {prompt_id}"
                        )
            else:
                print(f"✗ Failed to save new prompt based on {prompt_id}")

            return success

        except Exception as e:
            print(f"Error retrying prompt: {e}")
            return False

    def get_status(self) -> QueueState:
        """Get current queue status."""
        if not self.state:
            self.state = self.storage.load_queue_state()
        return self.state

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information."""
        if not self.state:
            self.state = self.storage.load_queue_state()

        current_time = datetime.now()
        is_rate_limited = self.state.is_rate_limited()

        info = {
            "current_time": current_time,
            "is_rate_limited": is_rate_limited,
            "rate_limited_count": self.state.rate_limited_count,
        }

        if is_rate_limited and self.state.current_rate_limit:
            info["reset_time"] = self.state.current_rate_limit.reset_time
            info["limit_message"] = self.state.current_rate_limit.limit_message

        return info

    def get_prompt_path(self, prompt_id: str) -> Optional[str]:
        """Get the file path for a prompt by ID."""
        file_path = self.storage.get_prompt_path(prompt_id)
        return str(file_path) if file_path else None

    def get_next_prompt_id(self) -> Optional[str]:
        """Get the ID of the next prompt that would be processed."""
        if not self.state:
            self.state = self.storage.load_queue_state()

        # Check if rate limit has expired
        self.state.clear_rate_limit_if_expired()

        next_prompt = self.state.get_next_prompt()
        return next_prompt.id if next_prompt else None
