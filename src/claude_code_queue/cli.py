#!/usr/bin/env python3
"""
Claude Code Queue - Main CLI entry point.

A tool to queue Claude Code prompts and automatically execute them when token limits reset.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .models import PromptStatus, QueuedPrompt
from .queue_manager import QueueManager
from .storage import MarkdownPromptParser


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Queue - Queue prompts and execute when limits reset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start the queue processor
  claude-queue start

  # Add a quick prompt
  claude-queue add "Fix the authentication bug" --priority 1

  # Check queue status
  claude-queue status

  # Cancel a prompt (marks as cancelled)
  claude-queue cancel abc123

  # Permanently delete one or more prompts
  claude-queue delete abc123
  claude-queue delete abc123 def456 ghi789

  # Test Claude Code connection
  claude-queue test
        """,
    )

    parser.add_argument(
        "--storage-dir",
        default="~/.claude-queue",
        help="Storage directory for queue data (default: ~/.claude-queue)",
    )

    parser.add_argument(
        "--claude-command",
        default="claude",
        help="Claude Code CLI command (default: claude)",
    )

    parser.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="Check interval in seconds (default: 30)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Command timeout in seconds (default: 3600)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    start_parser = subparsers.add_parser("start", help="Start the queue processor")
    start_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    next_parser = subparsers.add_parser(
        "next", help="Process only the next queue item and stop"
    )
    next_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    add_parser = subparsers.add_parser("add", help="Add a prompt to the queue")
    add_parser.add_argument("prompt", help="The prompt text")
    add_parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=0,
        help="Priority (lower = higher priority)",
    )
    add_parser.add_argument(
        "--working-dir", "-d", default=os.getcwd(), help="Working directory"
    )
    add_parser.add_argument(
        "--context-files", "-f", nargs="*", default=[], help="Context files to include"
    )
    add_parser.add_argument(
        "--max-retries", "-r", type=int, default=3, help="Maximum retry attempts"
    )
    add_parser.add_argument(
        "--estimated-tokens", "-t", type=int, help="Estimated token usage"
    )
    add_parser.add_argument(
        "--permission-mode",
        choices=[
            "acceptEdits",
            "bypassPermissions",
            "default",
            "delegate",
            "dontAsk",
            "plan",
        ],
        help="Permission mode for this prompt (default: acceptEdits)",
    )
    add_parser.add_argument(
        "--allowed-tools",
        nargs="*",
        help='Allowed tools (e.g. "Edit" "Write" "Bash(git:*)")',
    )
    add_parser.add_argument(
        "--prompt-timeout",
        type=int,
        dest="prompt_timeout",
        help="Timeout in seconds for this prompt (overrides global --timeout)",
    )
    add_parser.add_argument(
        "--model",
        "-m",
        choices=["sonnet", "opus", "haiku"],
        help="Claude model to use (default: sonnet)",
    )
    add_parser.add_argument(
        "--bookmark",
        "-b",
        help="jj bookmark name for dependent queue items",
    )

    # Edit command - opens $EDITOR to compose a prompt
    edit_parser = subparsers.add_parser("edit", help="Open $EDITOR to compose a prompt")
    edit_parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=0,
        help="Priority (lower = higher priority)",
    )
    edit_parser.add_argument(
        "--working-dir", "-d", default=os.getcwd(), help="Working directory"
    )
    edit_parser.add_argument(
        "--context-files", "-f", nargs="*", default=[], help="Context files to include"
    )
    edit_parser.add_argument(
        "--max-retries", "-r", type=int, default=3, help="Maximum retry attempts"
    )
    edit_parser.add_argument(
        "--estimated-tokens", "-t", type=int, help="Estimated token usage"
    )
    edit_parser.add_argument(
        "--permission-mode",
        choices=[
            "acceptEdits",
            "bypassPermissions",
            "default",
            "delegate",
            "dontAsk",
            "plan",
        ],
        help="Permission mode for this prompt (default: acceptEdits)",
    )
    edit_parser.add_argument(
        "--allowed-tools",
        nargs="*",
        help='Allowed tools (e.g. "Edit" "Write" "Bash(git:*)")',
    )
    edit_parser.add_argument(
        "--prompt-timeout",
        type=int,
        dest="prompt_timeout",
        help="Timeout in seconds for this prompt (overrides global --timeout)",
    )
    edit_parser.add_argument(
        "--model",
        "-m",
        choices=["sonnet", "opus", "haiku"],
        help="Claude model to use (default: sonnet)",
    )
    edit_parser.add_argument(
        "--bookmark",
        "-b",
        help="jj bookmark name for dependent queue items",
    )

    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    status_parser.add_argument(
        "--detailed", "-d", action="store_true", help="Show detailed prompt info"
    )

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a prompt")
    cancel_parser.add_argument("prompt_id", help="Prompt ID to cancel")

    delete_parser = subparsers.add_parser(
        "delete", help="Permanently delete one or more prompts from storage"
    )
    delete_parser.add_argument("prompt_ids", nargs="+", help="Prompt ID(s) to delete")

    retry_parser = subparsers.add_parser("retry", help="Retry a failed prompt")
    retry_parser.add_argument("prompt_id", help="Prompt ID to retry")
    retry_parser.add_argument(
        "--delete",
        "-d",
        action="store_true",
        help="Delete the original prompt after successful retry",
    )

    path_parser = subparsers.add_parser("path", help="Get the file path for a prompt")
    path_parser.add_argument("prompt_id", help="Prompt ID")

    list_parser = subparsers.add_parser("list", help="List prompts")
    list_parser.add_argument(
        "--status", choices=[s.value for s in PromptStatus], help="Filter by status"
    )
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.add_argument(
        "--all", "-a", action="store_true", help="Include completed prompts"
    )

    test_parser = subparsers.add_parser("test", help="Test Claude Code connection")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        manager = QueueManager(
            storage_dir=args.storage_dir,
            claude_command=args.claude_command,
            check_interval=args.check_interval,
            timeout=args.timeout,
        )

        if args.command == "start":
            return cmd_start(manager, args)
        elif args.command == "next":
            return cmd_next(manager, args)
        elif args.command == "add":
            return cmd_add(manager, args)
        elif args.command == "edit":
            return cmd_edit(manager, args)
        elif args.command == "status":
            return cmd_status(manager, args)
        elif args.command == "cancel":
            return cmd_cancel(manager, args)
        elif args.command == "delete":
            return cmd_delete(manager, args)
        elif args.command == "retry":
            return cmd_retry(manager, args)
        elif args.command == "path":
            return cmd_path(manager, args)
        elif args.command == "list":
            return cmd_list(manager, args)
        elif args.command == "test":
            return cmd_test(manager, args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_start(manager: QueueManager, args) -> int:
    """Start the queue processor."""

    def status_callback(state):
        if args.verbose:
            stats = state.get_stats()
            print(f"Queue status: {stats['status_counts']}")

    manager.start(callback=status_callback if args.verbose else None)
    return 0


def cmd_next(manager: QueueManager, args) -> int:
    """Process only the next queue item and stop."""

    def status_callback(state):
        if args.verbose:
            stats = state.get_stats()
            print(f"Queue status: {stats['status_counts']}")

    return manager.process_next(callback=status_callback if args.verbose else None)


def cmd_add(manager: QueueManager, args) -> int:
    """Add a prompt to the queue."""
    prompt = QueuedPrompt(
        content=args.prompt,
        working_directory=args.working_dir,
        priority=args.priority,
        context_files=args.context_files,
        max_retries=args.max_retries,
        estimated_tokens=args.estimated_tokens,
        permission_mode=getattr(args, "permission_mode", None),
        allowed_tools=getattr(args, "allowed_tools", None),
        timeout=getattr(args, "prompt_timeout", None),
        model=getattr(args, "model", None),
        bookmark=getattr(args, "bookmark", None),
    )

    success = manager.add_prompt(prompt)
    return 0 if success else 1


def cmd_edit(manager: QueueManager, args) -> int:
    """Open $EDITOR to compose a prompt."""
    # Check if EDITOR is set
    editor = os.environ.get("EDITOR")
    if not editor:
        print("Error: $EDITOR environment variable is not set", file=sys.stderr)
        print(
            "Set it with: export EDITOR=vim (or your preferred editor)", file=sys.stderr
        )
        return 1

    # Create a temporary prompt with all the defaults
    prompt = QueuedPrompt(
        content="",  # Empty content, user will fill this in
        working_directory=args.working_dir,
        priority=args.priority,
        context_files=args.context_files,
        max_retries=args.max_retries,
        estimated_tokens=args.estimated_tokens,
        permission_mode=getattr(args, "permission_mode", None),
        allowed_tools=getattr(args, "allowed_tools", None),
        timeout=getattr(args, "prompt_timeout", None),
        model=getattr(args, "model", None),
        bookmark=getattr(args, "bookmark", None),
    )

    # Create temporary file with the prompt template
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        prefix=prompt.id + "-",
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        # Write the template using the existing parser
        MarkdownPromptParser.write_prompt_file(prompt, tmp_path)

    try:
        # Get mtime before opening editor
        mtime_before = tmp_path.stat().st_mtime

        # Open the editor
        result = subprocess.run([editor, str(tmp_path)])
        if result.returncode != 0:
            print(f"Editor exited with code {result.returncode}", file=sys.stderr)
            return 1

        # Check if file was modified
        mtime_after = tmp_path.stat().st_mtime
        if mtime_after == mtime_before:
            print("File was not modified, aborting")
            return 0

        # Parse the edited file
        edited_prompt = MarkdownPromptParser.parse_prompt_file(tmp_path)
        if not edited_prompt:
            print("Error: Could not parse the edited file", file=sys.stderr)
            return 1

        # Check if content is empty
        if not edited_prompt.content.strip():
            print("Error: Prompt content is empty, aborting", file=sys.stderr)
            return 1

        # Add to queue using the manager's storage
        success = manager.storage.add_prompt_from_markdown(tmp_path)
        if success:
            print(f"Added prompt {success.id} to queue")
            return 0
        else:
            print("Error: Failed to add prompt to queue", file=sys.stderr)
            return 1

    finally:
        # Clean up temp file if it still exists (add_prompt_from_markdown moves it)
        if tmp_path.exists():
            tmp_path.unlink()


def cmd_status(manager: QueueManager, args) -> int:
    """Show queue status."""
    state = manager.get_status()
    stats = state.get_stats()

    if args.json:
        print(json.dumps(stats, indent=2))
        return 0

    print("Claude Code Queue Status")
    print("=" * 40)
    print(f"Total prompts: {stats['total_prompts']}")
    print(f"Total processed: {stats['total_processed']}")
    print(f"Failed count: {stats['failed_count']}")
    print(f"Rate limited count: {stats['rate_limited_count']}")

    if stats["last_processed"]:
        last_processed = datetime.fromisoformat(stats["last_processed"])
        print(f"Last processed: {last_processed.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\nStatus breakdown:")
    for status, count in stats["status_counts"].items():
        if count > 0:
            print(f"  {status}: {count}")

    if stats["current_rate_limit"]["is_rate_limited"]:
        reset_time = stats["current_rate_limit"]["reset_time"]
        if reset_time:
            reset_dt = datetime.fromisoformat(reset_time)
            print(f"\nRate limited until: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.detailed:
        # Show failed prompts sorted by creation date
        failed_prompts = [p for p in state.prompts if p.status == PromptStatus.FAILED]

        if failed_prompts:
            print("\nFailed Prompts (sorted by creation date):")
            print("-" * 80)
            for prompt in sorted(failed_prompts, key=lambda p: p.created_at):
                print(f"❌ {prompt.id} (P{prompt.priority})")
                print(
                    f"   {prompt.content[:70]}{'...' if len(prompt.content) > 70 else ''}"
                )
                print(f"   Created: {prompt.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Retries: {prompt.retry_count}/{prompt.max_retries}")
                print(f"   Working directory: {prompt.working_directory}")
                if prompt.execution_log:
                    # Show last log entry
                    log_lines = prompt.execution_log.strip().split("\n")
                    if log_lines:
                        print(f"   Last log: {log_lines[-1]}")
                print()
        else:
            print("\nNo failed prompts")

        # Also show other prompts for context
        other_prompts = [p for p in state.prompts if p.status != PromptStatus.FAILED]
        if other_prompts:
            print("\nOther Prompts (sorted by priority):")
            print("-" * 80)
            for prompt in sorted(other_prompts, key=lambda p: p.priority):
                status_icon = {
                    PromptStatus.QUEUED: "⏳",
                    PromptStatus.EXECUTING: "▶️",
                    PromptStatus.COMPLETED: "✅",
                    PromptStatus.CANCELLED: "🚫",
                }.get(prompt.status, "❓")

                print(
                    f"{status_icon} {prompt.id} (P{prompt.priority}) - {prompt.status.value}"
                )
                print(
                    f"   {prompt.content[:70]}{'...' if len(prompt.content) > 70 else ''}"
                )
                print(f"   Working directory: {prompt.working_directory}")
                if prompt.retry_count > 0:
                    print(f"   Retries: {prompt.retry_count}/{prompt.max_retries}")
                print()

    return 0


def cmd_cancel(manager: QueueManager, args) -> int:
    """Cancel a prompt."""
    success = manager.remove_prompt(args.prompt_id)
    return 0 if success else 1


def cmd_delete(manager: QueueManager, args) -> int:
    """Permanently delete one or more prompts from storage."""
    all_success = True
    for prompt_id in args.prompt_ids:
        success = manager.delete_prompt(prompt_id)
        if not success:
            all_success = False
    return 0 if all_success else 1


def cmd_retry(manager: QueueManager, args) -> int:
    """Retry a failed prompt by creating a new task with the same parameters."""
    delete_original = getattr(args, "delete", False)
    success = manager.retry_prompt(args.prompt_id, delete_after_success=delete_original)
    return 0 if success else 1


def cmd_path(manager: QueueManager, args) -> int:
    """Get the file path for a prompt."""
    # Handle special case: "next" returns the path of the next prompt to be processed
    if args.prompt_id == "next":
        next_prompt_id = manager.get_next_prompt_id()
        if next_prompt_id:
            file_path = manager.get_prompt_path(next_prompt_id)
            if file_path:
                print(file_path)
                return 0
            else:
                print(
                    f"Path not found for next prompt {next_prompt_id}", file=sys.stderr
                )
                return 1
        else:
            print("No prompts in queue", file=sys.stderr)
            return 1

    # Normal case: get path by prompt ID
    file_path = manager.get_prompt_path(args.prompt_id)
    if file_path:
        print(file_path)
        return 0
    else:
        print(f"Prompt {args.prompt_id} not found", file=sys.stderr)
        return 1


def cmd_list(manager: QueueManager, args) -> int:
    """List prompts."""
    include_completed = getattr(args, "all", False)
    state = manager.get_status(include_completed=include_completed)
    prompts = state.prompts

    if args.status:
        status_filter = PromptStatus(args.status)
        prompts = [p for p in prompts if p.status == status_filter]

    if args.json:
        prompt_data = []
        for prompt in prompts:
            prompt_data.append(
                {
                    "id": prompt.id,
                    "content": prompt.content,
                    "status": prompt.status.value,
                    "priority": prompt.priority,
                    "working_directory": prompt.working_directory,
                    "created_at": prompt.created_at.isoformat(),
                    "retry_count": prompt.retry_count,
                    "max_retries": prompt.max_retries,
                }
            )
        print(json.dumps(prompt_data, indent=2))
    else:
        if not prompts:
            print("No prompts found")
            return 0

        print(f"Found {len(prompts)} prompts:")
        print("-" * 80)
        for prompt in sorted(prompts, key=lambda p: p.priority):
            status_icon = {
                PromptStatus.QUEUED: "⏳",
                PromptStatus.EXECUTING: "▶️",
                PromptStatus.COMPLETED: "✅",
                PromptStatus.FAILED: "❌",
                PromptStatus.CANCELLED: "🚫",
            }.get(prompt.status, "❓")

            print(
                f"{status_icon} {prompt.id} | P{prompt.priority} | {prompt.status.value}"
            )
            print(
                f"   {prompt.content[:70]}{'...' if len(prompt.content) > 70 else ''}"
            )
            print(f"   Working directory: {prompt.working_directory}")
            print(f"   Created: {prompt.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

    return 0


def cmd_test(manager: QueueManager, args) -> int:
    """Test Claude Code connection."""
    is_working, message = manager.claude_interface.test_connection()
    print(message)
    return 0 if is_working else 1


if __name__ == "__main__":
    main()
