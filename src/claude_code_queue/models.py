"""
Data structures for Claude Code Queue system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PromptStatus(Enum):
    """Status of a queued prompt."""

    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_PERMISSION_MODES = {
    "acceptEdits",
    "bypassPermissions",
    "default",
    "delegate",
    "dontAsk",
    "plan",
}


@dataclass
class QueuedPrompt:
    """Represents a prompt in the queue."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    working_directory: str = "."
    created_at: datetime = field(default_factory=datetime.now)
    priority: int = 0  # Lower number = higher priority
    context_files: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_count: int = 0
    status: PromptStatus = PromptStatus.QUEUED
    execution_log: str = ""
    estimated_tokens: Optional[int] = None
    last_executed: Optional[datetime] = None
    permission_mode: Optional[str] = None  # "acceptEdits", "bypassPermissions", etc.
    allowed_tools: Optional[List[str]] = None  # ["Edit", "Write", "Bash(git:*)"]
    timeout: Optional[int] = None  # Per-prompt timeout override
    model: Optional[str] = (
        None  # Claude model to use: "sonnet" (default), "opus", "haiku"
    )
    bookmark: Optional[str] = None  # jj bookmark name for dependent queue items

    def __post_init__(self):
        """Validate permission_mode if provided."""
        if self.permission_mode is not None:
            if self.permission_mode not in VALID_PERMISSION_MODES:
                raise ValueError(
                    f"Invalid permission_mode: {self.permission_mode}. "
                    f"Must be one of: {', '.join(sorted(VALID_PERMISSION_MODES))}"
                )

    def add_log(self, message: str) -> None:
        """Add a log entry with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.execution_log += f"[{timestamp}] {message}\n"

    def can_retry(self) -> bool:
        """Check if this prompt can be retried."""
        return (
            self.retry_count < self.max_retries and self.status == PromptStatus.FAILED
        )


@dataclass
class RateLimitInfo:
    """Information about rate limiting from Claude Code response."""

    is_rate_limited: bool = False
    reset_time: Optional[datetime] = None
    limit_message: str = ""
    timestamp: Optional[datetime] = None

    @classmethod
    def from_claude_response(cls, response_text: str) -> "RateLimitInfo":
        """Parse rate limit info from Claude Code response."""
        # Common rate limit indicators in Claude Code responses
        rate_limit_indicators = [
            "usage limit reached",
            "rate limit",
            "too many requests",
            "quota exceeded",
            "limit exceeded",
        ]

        is_limited = any(
            indicator in response_text.lower() for indicator in rate_limit_indicators
        )

        if is_limited:
            return cls(
                is_rate_limited=True,
                limit_message=response_text.strip(),
                timestamp=datetime.now(),
            )

        return cls(is_rate_limited=False)


@dataclass
class QueueState:
    """Overall state of the queue system."""

    prompts: List[QueuedPrompt] = field(default_factory=list)
    last_processed: Optional[datetime] = None
    total_processed: int = 0
    failed_count: int = 0
    rate_limited_count: int = 0
    current_rate_limit: Optional[RateLimitInfo] = None

    def is_rate_limited(self) -> bool:
        """Check if the queue is currently rate limited."""
        if not self.current_rate_limit:
            return False
        if not self.current_rate_limit.is_rate_limited:
            return False
        # Check if rate limit has expired
        if self.current_rate_limit.reset_time:
            return datetime.now() < self.current_rate_limit.reset_time
        return True

    def clear_rate_limit_if_expired(self) -> bool:
        """Clear rate limit if it has expired. Returns True if cleared."""
        if not self.current_rate_limit or not self.current_rate_limit.is_rate_limited:
            return False
        if (
            self.current_rate_limit.reset_time
            and datetime.now() >= self.current_rate_limit.reset_time
        ):
            self.current_rate_limit = None
            return True
        return False

    def get_next_prompt(self) -> Optional[QueuedPrompt]:
        """Get the next prompt to execute (highest priority, not rate limited)."""
        # Don't return any prompt if we're rate limited
        if self.is_rate_limited():
            return None

        executable_prompts = [
            p for p in self.prompts if p.status == PromptStatus.QUEUED
        ]

        if not executable_prompts:
            return None

        # Return highest priority prompt (lowest number)
        return min(executable_prompts, key=lambda p: p.priority)

    def add_prompt(self, prompt: QueuedPrompt) -> None:
        """Add a prompt to the queue."""
        self.prompts.append(prompt)

    def remove_prompt(self, prompt_id: str) -> bool:
        """Remove a prompt from the queue."""
        original_count = len(self.prompts)
        self.prompts = [p for p in self.prompts if p.id != prompt_id]
        return len(self.prompts) < original_count

    def delete_prompt(self, prompt_id: str) -> bool:
        """Permanently delete a prompt from the queue (hard delete)."""
        return self.remove_prompt(prompt_id)

    def get_prompt(self, prompt_id: str) -> Optional[QueuedPrompt]:
        """Get a prompt by ID."""
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for status in PromptStatus:
            if status == PromptStatus.COMPLETED:
                # Use persistent counter for completed prompts
                status_counts[status.value] = self.total_processed
            elif status == PromptStatus.FAILED:
                # Use persistent counter for failed prompts
                status_counts[status.value] = self.failed_count
            else:
                # Count active prompts for other statuses
                status_counts[status.value] = len(
                    [p for p in self.prompts if p.status == status]
                )

        return {
            "total_prompts": len(self.prompts),
            "status_counts": status_counts,
            "total_processed": self.total_processed,
            "failed_count": self.failed_count,
            "rate_limited_count": self.rate_limited_count,
            "last_processed": (
                self.last_processed.isoformat() if self.last_processed else None
            ),
            "current_rate_limit": {
                "is_rate_limited": (
                    self.current_rate_limit.is_rate_limited
                    if self.current_rate_limit
                    else False
                ),
                "reset_time": (
                    self.current_rate_limit.reset_time.isoformat()
                    if self.current_rate_limit and self.current_rate_limit.reset_time
                    else None
                ),
            },
        }


@dataclass
class ExecutionResult:
    """Result of executing a prompt."""

    success: bool
    output: str
    error: str = ""
    rate_limit_info: Optional[RateLimitInfo] = None
    execution_time: float = 0.0
    jj_bookmark_to_set: Optional[str] = None  # Bookmark to set on success
    jj_working_dir: Optional[str] = None  # Working directory for jj operations

    @property
    def is_rate_limited(self) -> bool:
        """Check if this execution was rate limited."""
        return self.rate_limit_info is not None and self.rate_limit_info.is_rate_limited
