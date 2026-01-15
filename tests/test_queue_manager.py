"""Integration tests for queue_manager module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_code_queue.models import (
    ExecutionResult,
    PromptStatus,
    QueuedPrompt,
    QueueState,
)
from claude_code_queue.queue_manager import QueueManager
from claude_code_queue.storage import QueueStorage


class TestQueueManager:
    """Test QueueManager class."""

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_initialization(self, mock_storage_class, mock_interface_class):
        """Test QueueManager initialization."""
        manager = QueueManager(
            storage_dir="/tmp/test-queue",
            claude_command="my-claude",
            check_interval=60,
            timeout=7200,
        )

        assert manager.check_interval == 60
        assert manager.running is False
        mock_storage_class.assert_called_once_with("/tmp/test-queue")
        mock_interface_class.assert_called_once_with("my-claude", 7200)

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_stop(self, mock_storage_class, mock_interface_class):
        """Test stopping the queue manager."""
        manager = QueueManager()
        manager.running = True

        manager.stop()

        assert manager.running is False

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_shutdown_saves_state(self, mock_storage_class, mock_interface_class):
        """Test shutdown saves queue state."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        manager = QueueManager()
        manager.state = QueueState()
        manager.state.prompts = [
            QueuedPrompt(id="1", status=PromptStatus.QUEUED),
            QueuedPrompt(id="2", status=PromptStatus.EXECUTING),
        ]

        manager._shutdown()

        # Executing prompt should be reset to queued
        assert manager.state.prompts[1].status == PromptStatus.QUEUED
        mock_storage.save_queue_state.assert_called_once()

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_shutdown_adds_log_to_interrupted_prompts(
        self, mock_storage_class, mock_interface_class
    ):
        """Test shutdown adds log entry to interrupted prompts."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        manager = QueueManager()
        manager.state = QueueState()
        prompt = QueuedPrompt(id="test", status=PromptStatus.EXECUTING)
        manager.state.prompts = [prompt]

        manager._shutdown()

        assert "interrupted" in prompt.execution_log.lower()

    @patch("claude_code_queue.queue_manager.time.sleep")
    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_start_checks_claude_connection(
        self, mock_storage_class, mock_interface_class, mock_sleep
    ):
        """Test start checks Claude connection before processing."""
        mock_interface = Mock()
        mock_interface.test_connection.return_value = (False, "Connection failed")
        mock_interface_class.return_value = mock_interface

        mock_storage = Mock()
        mock_storage.load_queue_state.return_value = QueueState()
        mock_storage_class.return_value = mock_storage

        manager = QueueManager()
        manager.start()

        # Should not start processing if connection fails
        mock_interface.test_connection.assert_called_once()
        assert manager.running is False

    @patch("claude_code_queue.queue_manager.time.sleep")
    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_process_queue_iteration_no_prompts(
        self, mock_storage_class, mock_interface_class, mock_sleep
    ):
        """Test processing iteration with no prompts."""
        mock_storage = Mock()
        mock_storage.load_queue_state.return_value = QueueState()
        mock_storage_class.return_value = mock_storage

        manager = QueueManager()
        manager.state = QueueState()

        callback = Mock()
        manager._process_queue_iteration(callback)

        # Callback should be called with state
        callback.assert_called_once_with(manager.state)
        # No execution should occur
        mock_storage.save_queue_state.assert_not_called()


class TestQueueManagerExecutionLifecycle:
    """Test prompt execution lifecycle in QueueManager."""

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_execute_prompt_success(self, mock_storage_class, mock_interface_class):
        """Test successful prompt execution."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        mock_result = ExecutionResult(
            success=True,
            output="Task completed",
            execution_time=5.0,
        )
        mock_interface.execute_prompt.return_value = mock_result
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        prompt = QueuedPrompt(id="test", content="Test task")
        manager.state = QueueState()

        manager._execute_prompt(prompt)

        assert prompt.status == PromptStatus.COMPLETED
        assert "completed" in prompt.execution_log.lower()
        mock_interface.execute_prompt.assert_called_once_with(prompt)

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_execute_prompt_failure(self, mock_storage_class, mock_interface_class):
        """Test failed prompt execution."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        mock_result = ExecutionResult(
            success=False,
            output="",
            error="Task failed",
            execution_time=2.0,
        )
        mock_interface.execute_prompt.return_value = mock_result
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        prompt = QueuedPrompt(
            id="test", content="Test task", retry_count=0, max_retries=3
        )
        manager.state = QueueState()

        manager._execute_prompt(prompt)

        # Should increment retry count and be queued for retry
        assert prompt.retry_count == 1
        assert prompt.status == PromptStatus.QUEUED  # Will retry

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_execute_prompt_rate_limited(
        self, mock_storage_class, mock_interface_class
    ):
        """Test prompt execution when rate limited."""
        from claude_code_queue.models import RateLimitInfo

        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        rate_limit = RateLimitInfo(
            is_rate_limited=True,
            reset_time=datetime.now() + timedelta(hours=1),
        )
        mock_result = ExecutionResult(
            success=False,
            output="",
            error="Rate limit exceeded",
            rate_limit_info=rate_limit,
        )
        mock_interface.execute_prompt.return_value = mock_result
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        prompt = QueuedPrompt(id="test", content="Test task")
        manager.state = QueueState()

        manager._execute_prompt(prompt)

        # Prompt stays queued, daemon-level rate limit is set
        assert prompt.status == PromptStatus.QUEUED
        assert manager.state.current_rate_limit is not None
        assert manager.state.current_rate_limit.is_rate_limited is True
        assert "rate limit" in prompt.execution_log.lower()

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_execute_prompt_updates_last_executed(
        self, mock_storage_class, mock_interface_class
    ):
        """Test execution updates last_executed timestamp."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        mock_result = ExecutionResult(success=True, output="Done", execution_time=1.0)
        mock_interface.execute_prompt.return_value = mock_result
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        prompt = QueuedPrompt(id="test", content="Test")
        manager.state = QueueState()

        manager._execute_prompt(prompt)

        assert prompt.last_executed is not None
        assert isinstance(prompt.last_executed, datetime)

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_execute_prompt_updates_state_counters(
        self, mock_storage_class, mock_interface_class
    ):
        """Test execution updates state counters."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        mock_result = ExecutionResult(success=True, output="Done", execution_time=1.0)
        mock_interface.execute_prompt.return_value = mock_result
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        prompt = QueuedPrompt(id="test", content="Test")
        manager.state = QueueState()
        initial_processed = manager.state.total_processed

        manager._execute_prompt(prompt)

        assert manager.state.total_processed == initial_processed + 1
        assert manager.state.last_processed is not None


class TestQueueManagerCallbacks:
    """Test callback functionality in QueueManager."""

    @patch("claude_code_queue.queue_manager.time.sleep")
    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_callback_called_on_iteration(
        self, mock_storage_class, mock_interface_class, mock_sleep
    ):
        """Test callback is called after each iteration."""
        mock_storage = Mock()
        mock_storage.load_queue_state.return_value = QueueState()
        mock_storage_class.return_value = mock_storage

        mock_interface = Mock()
        mock_interface.test_connection.return_value = (True, "Working")
        mock_interface_class.return_value = mock_interface

        manager = QueueManager()
        callback = Mock()

        # Stop after first iteration
        def stop_after_first_call(*args):
            manager.stop()

        callback.side_effect = stop_after_first_call

        manager.start(callback=callback)

        # Callback should have been called
        assert callback.call_count >= 1

    @patch("claude_code_queue.queue_manager.ClaudeCodeInterface")
    @patch("claude_code_queue.queue_manager.QueueStorage")
    def test_callback_receives_current_state(
        self, mock_storage_class, mock_interface_class
    ):
        """Test callback receives current queue state."""
        manager = QueueManager()
        manager.state = QueueState()
        manager.state.total_processed = 5

        callback = Mock()
        manager._process_queue_iteration(callback)

        callback.assert_called_once()
        state_arg = callback.call_args[0][0]
        assert isinstance(state_arg, QueueState)
        assert state_arg.total_processed == 5
