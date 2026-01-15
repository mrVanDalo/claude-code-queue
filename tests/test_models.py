"""Unit tests for models module."""

from datetime import datetime, timedelta

import pytest

from claude_code_queue.models import (
    VALID_PERMISSION_MODES,
    ExecutionResult,
    PromptStatus,
    QueuedPrompt,
    QueueState,
    RateLimitInfo,
)


class TestPromptStatus:
    """Test PromptStatus enum."""

    def test_all_statuses_exist(self):
        """Verify all expected statuses are defined."""
        expected = {
            "QUEUED",
            "EXECUTING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "RATE_LIMITED",
        }
        actual = {status.name for status in PromptStatus}
        assert actual == expected

    def test_status_values(self):
        """Verify status string values."""
        assert PromptStatus.QUEUED.value == "queued"
        assert PromptStatus.EXECUTING.value == "executing"
        assert PromptStatus.COMPLETED.value == "completed"
        assert PromptStatus.FAILED.value == "failed"
        assert PromptStatus.CANCELLED.value == "cancelled"
        assert PromptStatus.RATE_LIMITED.value == "rate_limited"


class TestQueuedPrompt:
    """Test QueuedPrompt class."""

    def test_default_initialization(self):
        """Test prompt creation with defaults."""
        prompt = QueuedPrompt()
        assert prompt.id  # Auto-generated ID
        assert prompt.content == ""
        assert prompt.working_directory == "."
        assert prompt.priority == 0
        assert prompt.status == PromptStatus.QUEUED
        assert prompt.retry_count == 0
        assert prompt.max_retries == 3
        assert prompt.context_files == []
        assert isinstance(prompt.created_at, datetime)

    def test_custom_initialization(self):
        """Test prompt creation with custom values."""
        now = datetime.now()
        prompt = QueuedPrompt(
            id="custom-123",
            content="Test content",
            priority=5,
            working_directory="/tmp/test",
            model="opus",
            permission_mode="acceptEdits",
            timeout=600,
        )
        assert prompt.id == "custom-123"
        assert prompt.content == "Test content"
        assert prompt.priority == 5
        assert prompt.working_directory == "/tmp/test"
        assert prompt.model == "opus"
        assert prompt.permission_mode == "acceptEdits"
        assert prompt.timeout == 600

    def test_valid_permission_modes(self):
        """Test all valid permission modes are accepted."""
        for mode in VALID_PERMISSION_MODES:
            prompt = QueuedPrompt(permission_mode=mode)
            assert prompt.permission_mode == mode

    def test_invalid_permission_mode_raises_error(self):
        """Test invalid permission mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid permission_mode"):
            QueuedPrompt(permission_mode="invalid_mode")

    def test_add_log(self):
        """Test adding log entries."""
        prompt = QueuedPrompt()
        prompt.add_log("Test message 1")
        prompt.add_log("Test message 2")

        assert "Test message 1" in prompt.execution_log
        assert "Test message 2" in prompt.execution_log
        assert prompt.execution_log.count("[") == 2  # Two timestamp entries

    def test_can_retry_when_failed_with_retries_remaining(self):
        """Test can_retry returns True for failed prompts with retries left."""
        prompt = QueuedPrompt(status=PromptStatus.FAILED, retry_count=1, max_retries=3)
        assert prompt.can_retry() is True

    def test_can_retry_when_rate_limited(self):
        """Test can_retry returns True for rate limited prompts."""
        prompt = QueuedPrompt(
            status=PromptStatus.RATE_LIMITED, retry_count=1, max_retries=3
        )
        assert prompt.can_retry() is True

    def test_cannot_retry_when_max_retries_exceeded(self):
        """Test can_retry returns False when max retries exceeded."""
        prompt = QueuedPrompt(status=PromptStatus.FAILED, retry_count=3, max_retries=3)
        assert prompt.can_retry() is False

    def test_cannot_retry_when_completed(self):
        """Test can_retry returns False for completed prompts."""
        prompt = QueuedPrompt(
            status=PromptStatus.COMPLETED, retry_count=0, max_retries=3
        )
        assert prompt.can_retry() is False

    def test_cannot_retry_when_cancelled(self):
        """Test can_retry returns False for cancelled prompts."""
        prompt = QueuedPrompt(
            status=PromptStatus.CANCELLED, retry_count=0, max_retries=3
        )
        assert prompt.can_retry() is False

    def test_should_execute_now_when_queued(self):
        """Test should_execute_now returns True for queued prompts."""
        prompt = QueuedPrompt(status=PromptStatus.QUEUED)
        assert prompt.should_execute_now() is True

    def test_should_execute_now_when_rate_limited_but_reset_time_passed(self):
        """Test should_execute_now returns True when reset time has passed."""
        past_time = datetime.now() - timedelta(hours=1)
        prompt = QueuedPrompt(
            status=PromptStatus.RATE_LIMITED,
            reset_time=past_time,
        )
        assert prompt.should_execute_now() is True

    def test_should_not_execute_when_rate_limited_and_reset_time_future(self):
        """Test should_execute_now returns False when reset time is in future."""
        future_time = datetime.now() + timedelta(hours=1)
        prompt = QueuedPrompt(
            status=PromptStatus.RATE_LIMITED,
            reset_time=future_time,
        )
        assert prompt.should_execute_now() is False

    def test_should_not_execute_when_rate_limited_no_reset_time(self):
        """Test should_execute_now returns False when rate limited with no reset time."""
        prompt = QueuedPrompt(status=PromptStatus.RATE_LIMITED)
        assert prompt.should_execute_now() is False


class TestRateLimitInfo:
    """Test RateLimitInfo class."""

    def test_default_initialization(self):
        """Test RateLimitInfo creation with defaults."""
        info = RateLimitInfo()
        assert info.is_rate_limited is False
        assert info.reset_time is None
        assert info.limit_message == ""
        assert info.timestamp is None

    def test_from_claude_response_no_rate_limit(self):
        """Test parsing response with no rate limit."""
        response = "Task completed successfully."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is False

    def test_from_claude_response_rate_limit_detected(self):
        """Test parsing response with rate limit indicator."""
        response = "Error: Rate limit exceeded. Please try again later."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True
        assert "rate limit" in info.limit_message.lower()
        assert info.timestamp is not None

    def test_from_claude_response_usage_limit(self):
        """Test parsing 'usage limit reached' message."""
        response = "Usage limit reached for this hour."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True

    def test_from_claude_response_too_many_requests(self):
        """Test parsing 'too many requests' message."""
        response = "Too many requests. Please wait."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True

    def test_from_claude_response_quota_exceeded(self):
        """Test parsing 'quota exceeded' message."""
        response = "API quota exceeded."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True

    def test_from_claude_response_limit_exceeded(self):
        """Test parsing 'limit exceeded' message."""
        response = "Limit exceeded. Try again in 30 minutes."
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True

    def test_from_claude_response_case_insensitive(self):
        """Test rate limit detection is case insensitive."""
        response = "RATE LIMIT EXCEEDED"
        info = RateLimitInfo.from_claude_response(response)
        assert info.is_rate_limited is True


class TestQueueState:
    """Test QueueState class."""

    def test_default_initialization(self):
        """Test QueueState creation with defaults."""
        state = QueueState()
        assert state.prompts == []
        assert state.last_processed is None
        assert state.total_processed == 0
        assert state.failed_count == 0
        assert state.rate_limited_count == 0
        assert state.current_rate_limit is None

    def test_add_prompt(self):
        """Test adding prompts to queue."""
        state = QueueState()
        prompt1 = QueuedPrompt(id="1", content="First")
        prompt2 = QueuedPrompt(id="2", content="Second")

        state.add_prompt(prompt1)
        state.add_prompt(prompt2)

        assert len(state.prompts) == 2
        assert state.prompts[0].id == "1"
        assert state.prompts[1].id == "2"

    def test_remove_prompt(self):
        """Test removing prompts from queue."""
        state = QueueState()
        prompt1 = QueuedPrompt(id="1")
        prompt2 = QueuedPrompt(id="2")
        state.add_prompt(prompt1)
        state.add_prompt(prompt2)

        removed = state.remove_prompt("1")
        assert removed is True
        assert len(state.prompts) == 1
        assert state.prompts[0].id == "2"

    def test_remove_nonexistent_prompt(self):
        """Test removing non-existent prompt returns False."""
        state = QueueState()
        removed = state.remove_prompt("nonexistent")
        assert removed is False

    def test_get_prompt(self):
        """Test getting prompt by ID."""
        state = QueueState()
        prompt = QueuedPrompt(id="test-123", content="Test")
        state.add_prompt(prompt)

        found = state.get_prompt("test-123")
        assert found is not None
        assert found.id == "test-123"
        assert found.content == "Test"

    def test_get_nonexistent_prompt(self):
        """Test getting non-existent prompt returns None."""
        state = QueueState()
        found = state.get_prompt("nonexistent")
        assert found is None

    def test_get_next_prompt_returns_highest_priority(self):
        """Test get_next_prompt returns highest priority (lowest number)."""
        state = QueueState()
        state.add_prompt(QueuedPrompt(id="1", priority=10, status=PromptStatus.QUEUED))
        state.add_prompt(QueuedPrompt(id="2", priority=5, status=PromptStatus.QUEUED))
        state.add_prompt(QueuedPrompt(id="3", priority=15, status=PromptStatus.QUEUED))

        next_prompt = state.get_next_prompt()
        assert next_prompt is not None
        assert next_prompt.id == "2"  # Priority 5 is highest

    def test_get_next_prompt_skips_executing(self):
        """Test get_next_prompt skips executing prompts."""
        state = QueueState()
        state.add_prompt(
            QueuedPrompt(id="1", priority=1, status=PromptStatus.EXECUTING)
        )
        state.add_prompt(QueuedPrompt(id="2", priority=5, status=PromptStatus.QUEUED))

        next_prompt = state.get_next_prompt()
        assert next_prompt.id == "2"

    def test_get_next_prompt_skips_completed(self):
        """Test get_next_prompt skips completed prompts."""
        state = QueueState()
        state.add_prompt(
            QueuedPrompt(id="1", priority=1, status=PromptStatus.COMPLETED)
        )
        state.add_prompt(QueuedPrompt(id="2", priority=5, status=PromptStatus.QUEUED))

        next_prompt = state.get_next_prompt()
        assert next_prompt.id == "2"

    def test_get_next_prompt_returns_none_when_empty(self):
        """Test get_next_prompt returns None when no executable prompts."""
        state = QueueState()
        next_prompt = state.get_next_prompt()
        assert next_prompt is None

    def test_get_next_prompt_retries_rate_limited_after_reset(self):
        """Test get_next_prompt returns rate limited prompt after reset time."""
        state = QueueState()
        past_time = datetime.now() - timedelta(hours=1)
        prompt = QueuedPrompt(
            id="1",
            priority=5,
            status=PromptStatus.RATE_LIMITED,
            reset_time=past_time,
            retry_count=1,
            max_retries=3,
        )
        state.add_prompt(prompt)

        next_prompt = state.get_next_prompt()
        assert next_prompt is not None
        assert next_prompt.id == "1"
        assert next_prompt.status == PromptStatus.QUEUED  # Status reset for retry

    def test_get_next_prompt_skips_rate_limited_future_reset(self):
        """Test get_next_prompt skips rate limited with future reset time."""
        state = QueueState()
        future_time = datetime.now() + timedelta(hours=1)
        state.add_prompt(
            QueuedPrompt(
                id="1",
                status=PromptStatus.RATE_LIMITED,
                reset_time=future_time,
            )
        )

        next_prompt = state.get_next_prompt()
        assert next_prompt is None

    def test_get_stats_empty_queue(self):
        """Test get_stats with empty queue."""
        state = QueueState()
        stats = state.get_stats()

        assert stats["total_prompts"] == 0
        assert stats["total_processed"] == 0
        assert stats["failed_count"] == 0
        assert stats["rate_limited_count"] == 0
        assert stats["last_processed"] is None

    def test_get_stats_with_prompts(self):
        """Test get_stats with various prompt statuses."""
        state = QueueState()
        state.add_prompt(QueuedPrompt(id="1", status=PromptStatus.QUEUED))
        state.add_prompt(QueuedPrompt(id="2", status=PromptStatus.QUEUED))
        state.add_prompt(QueuedPrompt(id="3", status=PromptStatus.EXECUTING))
        state.add_prompt(QueuedPrompt(id="4", status=PromptStatus.RATE_LIMITED))
        state.total_processed = 10
        state.failed_count = 2

        stats = state.get_stats()

        assert stats["total_prompts"] == 4
        assert stats["status_counts"]["queued"] == 2
        assert stats["status_counts"]["executing"] == 1
        assert stats["status_counts"]["rate_limited"] == 1
        assert stats["status_counts"]["completed"] == 10
        assert stats["status_counts"]["failed"] == 2
        assert stats["total_processed"] == 10
        assert stats["failed_count"] == 2

    def test_get_stats_with_current_rate_limit(self):
        """Test get_stats includes current rate limit info."""
        state = QueueState()
        reset_time = datetime.now() + timedelta(hours=1)
        state.current_rate_limit = RateLimitInfo(
            is_rate_limited=True,
            reset_time=reset_time,
        )

        stats = state.get_stats()

        assert stats["current_rate_limit"]["is_rate_limited"] is True
        assert stats["current_rate_limit"]["reset_time"] is not None


class TestExecutionResult:
    """Test ExecutionResult class."""

    def test_successful_execution(self):
        """Test ExecutionResult for successful execution."""
        result = ExecutionResult(
            success=True,
            output="Task completed",
            execution_time=5.5,
        )
        assert result.success is True
        assert result.output == "Task completed"
        assert result.error == ""
        assert result.execution_time == 5.5
        assert result.is_rate_limited is False

    def test_failed_execution(self):
        """Test ExecutionResult for failed execution."""
        result = ExecutionResult(
            success=False,
            output="",
            error="Command failed",
            execution_time=1.2,
        )
        assert result.success is False
        assert result.error == "Command failed"
        assert result.is_rate_limited is False

    def test_rate_limited_execution(self):
        """Test ExecutionResult with rate limit info."""
        rate_limit = RateLimitInfo(
            is_rate_limited=True,
            limit_message="Rate limit exceeded",
        )
        result = ExecutionResult(
            success=False,
            output="",
            error="Rate limited",
            rate_limit_info=rate_limit,
        )
        assert result.is_rate_limited is True
        assert result.success is False

    def test_is_rate_limited_property_false(self):
        """Test is_rate_limited property returns False when no rate limit."""
        result = ExecutionResult(success=True, output="Done")
        assert result.is_rate_limited is False

    def test_is_rate_limited_property_with_non_limited_info(self):
        """Test is_rate_limited property with non-limited RateLimitInfo."""
        rate_limit = RateLimitInfo(is_rate_limited=False)
        result = ExecutionResult(
            success=True,
            output="Done",
            rate_limit_info=rate_limit,
        )
        assert result.is_rate_limited is False
