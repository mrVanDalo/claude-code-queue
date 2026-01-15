"""Unit tests for claude_interface module."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_code_queue.claude_interface import ClaudeCodeInterface
from claude_code_queue.models import ExecutionResult, QueuedPrompt


class TestClaudeCodeInterface:
    """Test ClaudeCodeInterface class."""

    @patch("subprocess.run")
    def test_initialization_success(self, mock_run):
        """Test successful initialization when Claude CLI is available."""
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0", stderr="")

        interface = ClaudeCodeInterface()

        assert interface.claude_command == "claude"
        assert interface.timeout == 3600
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_initialization_custom_command(self, mock_run):
        """Test initialization with custom Claude command."""
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0", stderr="")

        interface = ClaudeCodeInterface(claude_command="my-claude", timeout=7200)

        assert interface.claude_command == "my-claude"
        assert interface.timeout == 7200

    @patch("subprocess.run")
    def test_initialization_claude_not_found(self, mock_run):
        """Test initialization fails when Claude CLI not found."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="Claude Code CLI not found"):
            ClaudeCodeInterface()

    @patch("subprocess.run")
    def test_initialization_claude_returns_error(self, mock_run):
        """Test initialization fails when Claude CLI returns error."""
        mock_run.return_value = Mock(returncode=1, stderr="Error message")

        with pytest.raises(RuntimeError, match="Claude Code CLI not available"):
            ClaudeCodeInterface()

    @patch("subprocess.run")
    def test_execute_prompt_basic(self, mock_run):
        """Test executing a basic prompt."""
        # Mock verification call
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0", stderr="")
        interface = ClaudeCodeInterface()

        # Mock execution call
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Task completed successfully",
            stderr="",
        )

        prompt = QueuedPrompt(
            content="Test prompt",
            working_directory=".",
        )

        result = interface.execute_prompt(prompt)

        assert result.success is True
        assert "Task completed successfully" in result.output
        assert result.error == ""
        assert result.execution_time > 0

    @patch("subprocess.run")
    def test_execute_prompt_with_model(self, mock_run):
        """Test executing prompt with specific model."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        prompt = QueuedPrompt(content="Test", model="opus")

        interface.execute_prompt(prompt)

        # Check that model was passed to command
        call_args = mock_run.call_args_list[-1][0][0]
        assert "--model" in call_args
        assert "opus" in call_args

    @patch("subprocess.run")
    def test_execute_prompt_with_permission_mode(self, mock_run):
        """Test executing prompt with permission mode."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        prompt = QueuedPrompt(content="Test", permission_mode="plan")

        interface.execute_prompt(prompt)

        call_args = mock_run.call_args_list[-1][0][0]
        assert "--permission-mode" in call_args
        assert "plan" in call_args

    @patch("subprocess.run")
    def test_execute_prompt_with_allowed_tools(self, mock_run):
        """Test executing prompt with allowed tools."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        prompt = QueuedPrompt(
            content="Test",
            allowed_tools=["Read", "Edit", "Bash(git:*)"],
        )

        interface.execute_prompt(prompt)

        call_args = mock_run.call_args_list[-1][0][0]
        assert "--allowed-tools" in call_args
        # Tools should be joined with commas
        tools_index = call_args.index("--allowed-tools") + 1
        assert "Read,Edit,Bash(git:*)" in call_args[tools_index]

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_execute_prompt_changes_working_directory(
        self, mock_getcwd, mock_chdir, mock_run
    ):
        """Test that execution changes to working directory."""
        mock_getcwd.return_value = "/original/dir"
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        prompt = QueuedPrompt(content="Test", working_directory="/tmp/test")

        interface.execute_prompt(prompt)

        # Should change to working dir and back
        assert mock_chdir.call_count >= 2

    @patch("subprocess.run")
    def test_execute_prompt_timeout(self, mock_run):
        """Test prompt execution timeout."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Mock timeout on execution
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)

        prompt = QueuedPrompt(content="Test", timeout=10)

        result = interface.execute_prompt(prompt)

        assert result.success is False
        assert "timed out" in result.error.lower()

    @patch("subprocess.run")
    def test_execute_prompt_uses_per_prompt_timeout(self, mock_run):
        """Test that per-prompt timeout overrides global timeout."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface(timeout=3600)

        prompt = QueuedPrompt(content="Test", timeout=1200)

        interface.execute_prompt(prompt)

        # Check timeout parameter in subprocess.run call
        call_kwargs = mock_run.call_args_list[-1][1]
        assert call_kwargs.get("timeout") == 1200

    @patch("subprocess.run")
    def test_execute_prompt_uses_global_timeout_when_not_specified(self, mock_run):
        """Test that global timeout is used when prompt timeout not specified."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface(timeout=7200)

        prompt = QueuedPrompt(content="Test")  # No timeout specified

        interface.execute_prompt(prompt)

        call_kwargs = mock_run.call_args_list[-1][1]
        assert call_kwargs.get("timeout") == 7200

    @patch("subprocess.run")
    def test_detect_rate_limit_usage_limit(self, mock_run):
        """Test rate limit detection for 'usage limit reached'."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        output = "Error: Usage limit reached. Please try again later."
        rate_limit = interface._detect_rate_limit(output)

        assert rate_limit.is_rate_limited is True
        assert "usage limit" in rate_limit.limit_message.lower()

    @patch("subprocess.run")
    def test_detect_rate_limit_rate_exceeded(self, mock_run):
        """Test rate limit detection for 'rate limit exceeded'."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        output = "Rate limit exceeded"
        rate_limit = interface._detect_rate_limit(output)

        assert rate_limit.is_rate_limited is True

    @patch("subprocess.run")
    def test_detect_rate_limit_too_many_requests(self, mock_run):
        """Test rate limit detection for 'too many requests'."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        output = "Too many requests. Please wait."
        rate_limit = interface._detect_rate_limit(output)

        assert rate_limit.is_rate_limited is True

    @patch("subprocess.run")
    def test_detect_rate_limit_no_limit(self, mock_run):
        """Test rate limit detection returns False for normal output."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        output = "Task completed successfully"
        rate_limit = interface._detect_rate_limit(output)

        assert rate_limit.is_rate_limited is False

    @patch("subprocess.run")
    def test_estimate_reset_time_morning(self, mock_run):
        """Test reset time estimation in morning hours."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Mock current time to 3 AM
        with patch("claude_code_queue.claude_interface.datetime") as mock_dt:
            mock_now = datetime(2026, 1, 15, 3, 30, 0)
            mock_dt.now.return_value = mock_now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.fromisoformat = datetime.fromisoformat

            reset_time = interface._estimate_reset_time("")

            # Should estimate next window at 5 AM
            assert reset_time.hour == 5
            assert reset_time.minute == 0

    @patch("subprocess.run")
    def test_estimate_reset_time_afternoon(self, mock_run):
        """Test reset time estimation in afternoon hours."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        with patch("claude_code_queue.claude_interface.datetime") as mock_dt:
            mock_now = datetime(2026, 1, 15, 12, 30, 0)
            mock_dt.now.return_value = mock_now

            reset_time = interface._estimate_reset_time("")

            # Should estimate next window at 3 PM (15:00)
            assert reset_time.hour == 15

    @patch("subprocess.run")
    def test_estimate_reset_time_evening(self, mock_run):
        """Test reset time estimation in evening hours."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        with patch("claude_code_queue.claude_interface.datetime") as mock_dt:
            mock_now = datetime(2026, 1, 15, 22, 30, 0)
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            reset_time = interface._estimate_reset_time("")

            # Should estimate next window at midnight next day
            assert reset_time.day == 16
            assert reset_time.hour == 0

    @patch("subprocess.run")
    def test_test_connection_success(self, mock_run):
        """Test connection test succeeds."""
        mock_run.return_value = Mock(returncode=0, stdout="Help text", stderr="")

        interface = ClaudeCodeInterface()
        success, message = interface.test_connection()

        assert success is True
        assert "working" in message.lower()

    @patch("subprocess.run")
    def test_test_connection_failure(self, mock_run):
        """Test connection test fails."""
        # First call for init
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Second call for test_connection
        mock_run.return_value = Mock(returncode=1, stderr="Error")

        success, message = interface.test_connection()

        assert success is False
        assert "error" in message.lower()

    @patch("subprocess.run")
    def test_test_connection_not_found(self, mock_run):
        """Test connection test when CLI not found."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        mock_run.side_effect = FileNotFoundError()

        success, message = interface.test_connection()

        assert success is False
        assert "not found" in message.lower()

    @patch("subprocess.run")
    def test_execute_simple_prompt(self, mock_run):
        """Test executing a simple prompt without QueuedPrompt object."""
        mock_run.return_value = Mock(returncode=0, stdout="Done", stderr="")
        interface = ClaudeCodeInterface()

        result = interface.execute_simple_prompt("Test prompt", working_dir="/tmp")

        assert result.success is True
        assert result.output == "Done"

    @patch("subprocess.run")
    def test_execute_prompt_with_context_files(self, mock_run, tmp_path):
        """Test executing prompt with context files."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Create test files
        test_file1 = tmp_path / "file1.py"
        test_file1.write_text("print('test')")
        test_file2 = tmp_path / "file2.py"
        test_file2.write_text("print('test2')")

        prompt = QueuedPrompt(
            content="Review these files",
            working_directory=str(tmp_path),
            context_files=["file1.py", "file2.py"],
        )

        interface.execute_prompt(prompt)

        # Check that context files were referenced in command
        call_args = mock_run.call_args_list[-1][0][0]
        prompt_text = call_args[-1]
        assert "@file1.py" in prompt_text
        assert "@file2.py" in prompt_text

    @patch("subprocess.run")
    def test_execute_prompt_rate_limited_response(self, mock_run):
        """Test that rate limited responses are properly detected."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Execution returns rate limit message
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: Rate limit exceeded. Try again later.",
        )

        prompt = QueuedPrompt(content="Test")
        result = interface.execute_prompt(prompt)

        assert result.success is False
        assert result.is_rate_limited is True
        assert result.rate_limit_info is not None
        assert result.rate_limit_info.is_rate_limited is True

    @patch("subprocess.run")
    def test_execute_prompt_creates_working_directory(self, mock_run, tmp_path):
        """Test that non-existent working directory is created."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        new_dir = tmp_path / "new_working_dir"
        assert not new_dir.exists()

        prompt = QueuedPrompt(content="Test", working_directory=str(new_dir))
        interface.execute_prompt(prompt)

        assert new_dir.exists()

    @patch("subprocess.run")
    def test_execute_prompt_exception_handling(self, mock_run):
        """Test that exceptions during execution are properly handled."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        interface = ClaudeCodeInterface()

        # Mock exception during execution
        mock_run.side_effect = Exception("Unexpected error")

        prompt = QueuedPrompt(content="Test")
        result = interface.execute_prompt(prompt)

        assert result.success is False
        assert "failed" in result.error.lower()
        assert "Unexpected error" in result.error
