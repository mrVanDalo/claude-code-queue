"""Tests for CLI commands."""

from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_code_queue.cli import (
    handle_add,
    handle_bank_delete,
    handle_bank_list,
    handle_bank_save,
    handle_bank_use,
    handle_cancel,
    handle_list,
    handle_status,
    handle_test,
)
from claude_code_queue.models import PromptStatus, QueuedPrompt, QueueState


class TestHandleAdd:
    """Test handle_add CLI command."""

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_add_simple_prompt(self, mock_stdout, mock_storage_class):
        """Test adding a simple prompt."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.load_queue_state.return_value = QueueState()

        args = Namespace(
            prompt="Test prompt",
            priority=5,
            context_files=None,
            permission_mode=None,
            allowed_tools=None,
            timeout=None,
            model=None,
            working_dir=None,
        )

        handle_add(args)

        # Storage should save the state
        mock_storage.save_queue_state.assert_called_once()

        # Check output
        output = mock_stdout.getvalue()
        assert "added" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_prompt_with_priority(self, mock_storage_class):
        """Test adding prompt with custom priority."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(
            prompt="High priority task",
            priority=1,
            context_files=None,
            permission_mode=None,
            allowed_tools=None,
            timeout=None,
            model=None,
            working_dir=None,
        )

        handle_add(args)

        # Check that prompt was added with correct priority
        assert len(state.prompts) == 1
        assert state.prompts[0].priority == 1

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_prompt_with_context_files(self, mock_storage_class):
        """Test adding prompt with context files."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(
            prompt="Review files",
            priority=5,
            context_files=["file1.py", "file2.py"],
            permission_mode=None,
            allowed_tools=None,
            timeout=None,
            model=None,
            working_dir=None,
        )

        handle_add(args)

        assert state.prompts[0].context_files == ["file1.py", "file2.py"]

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_prompt_with_model(self, mock_storage_class):
        """Test adding prompt with specific model."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(
            prompt="Use Opus",
            priority=5,
            context_files=None,
            permission_mode=None,
            allowed_tools=None,
            timeout=None,
            model="opus",
            working_dir=None,
        )

        handle_add(args)

        assert state.prompts[0].model == "opus"

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_prompt_with_permission_mode(self, mock_storage_class):
        """Test adding prompt with permission mode."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(
            prompt="Plan mode task",
            priority=5,
            context_files=None,
            permission_mode="plan",
            allowed_tools=None,
            timeout=None,
            model=None,
            working_dir=None,
        )

        handle_add(args)

        assert state.prompts[0].permission_mode == "plan"


class TestHandleStatus:
    """Test handle_status CLI command."""

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_status_empty_queue(self, mock_stdout, mock_storage_class):
        """Test status with empty queue."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.load_queue_state.return_value = QueueState()

        args = Namespace(json=False)
        handle_status(args)

        output = mock_stdout.getvalue()
        assert "queue" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_status_with_prompts(self, mock_stdout, mock_storage_class):
        """Test status with prompts in queue."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        state = QueueState()
        state.prompts = [
            QueuedPrompt(id="1", status=PromptStatus.QUEUED),
            QueuedPrompt(id="2", status=PromptStatus.EXECUTING),
        ]
        state.total_processed = 10
        state.failed_count = 2

        mock_storage.load_queue_state.return_value = state

        args = Namespace(json=False)
        handle_status(args)

        output = mock_stdout.getvalue()
        assert "10" in output  # total_processed
        assert "2" in output  # failed_count

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_status_json_output(self, mock_stdout, mock_storage_class):
        """Test status with JSON output."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        state = QueueState()
        state.total_processed = 5
        mock_storage.load_queue_state.return_value = state

        args = Namespace(json=True)
        handle_status(args)

        output = mock_stdout.getvalue()
        # Should contain JSON
        assert "{" in output
        assert "}" in output


class TestHandleList:
    """Test handle_list CLI command."""

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_list_all_prompts(self, mock_stdout, mock_storage_class):
        """Test listing all prompts."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        state = QueueState()
        state.prompts = [
            QueuedPrompt(id="1", content="Prompt 1", status=PromptStatus.QUEUED),
            QueuedPrompt(id="2", content="Prompt 2", status=PromptStatus.EXECUTING),
        ]
        mock_storage.load_queue_state.return_value = state

        args = Namespace(status=None, json=False)
        handle_list(args)

        output = mock_stdout.getvalue()
        assert "Prompt 1" in output
        assert "Prompt 2" in output

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_list_filtered_by_status(self, mock_stdout, mock_storage_class):
        """Test listing prompts filtered by status."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        state = QueueState()
        state.prompts = [
            QueuedPrompt(id="1", content="Queued", status=PromptStatus.QUEUED),
            QueuedPrompt(id="2", content="Executing", status=PromptStatus.EXECUTING),
        ]
        mock_storage.load_queue_state.return_value = state

        args = Namespace(status="queued", json=False)
        handle_list(args)

        output = mock_stdout.getvalue()
        assert "Queued" in output
        # Should not show executing prompt
        assert "Executing" not in output

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_list_empty_queue(self, mock_stdout, mock_storage_class):
        """Test listing when queue is empty."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.load_queue_state.return_value = QueueState()

        args = Namespace(status=None, json=False)
        handle_list(args)

        output = mock_stdout.getvalue()
        assert "no prompts" in output.lower() or "empty" in output.lower()


class TestHandleCancel:
    """Test handle_cancel CLI command."""

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_cancel_existing_prompt(self, mock_stdout, mock_storage_class):
        """Test cancelling an existing prompt."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        state = QueueState()
        prompt = QueuedPrompt(
            id="test-123", content="To cancel", status=PromptStatus.QUEUED
        )
        state.prompts = [prompt]
        mock_storage.load_queue_state.return_value = state

        args = Namespace(prompt_id="test-123")
        handle_cancel(args)

        # Prompt should be cancelled
        assert prompt.status == PromptStatus.CANCELLED
        mock_storage.save_queue_state.assert_called_once()

        output = mock_stdout.getvalue()
        assert "cancelled" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_cancel_nonexistent_prompt(self, mock_stdout, mock_storage_class):
        """Test cancelling a non-existent prompt."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.load_queue_state.return_value = QueueState()

        args = Namespace(prompt_id="nonexistent")
        handle_cancel(args)

        output = mock_stdout.getvalue()
        assert "not found" in output.lower()


class TestHandleTest:
    """Test handle_test CLI command."""

    @patch("claude_code_queue.cli.ClaudeCodeInterface")
    @patch("sys.stdout", new_callable=StringIO)
    def test_test_connection_success(self, mock_stdout, mock_interface_class):
        """Test successful connection test."""
        mock_interface = Mock()
        mock_interface.test_connection.return_value = (True, "Working")
        mock_interface_class.return_value = mock_interface

        args = Namespace(claude_command="claude", timeout=3600)
        handle_test(args)

        output = mock_stdout.getvalue()
        assert "working" in output.lower() or "success" in output.lower()

    @patch("claude_code_queue.cli.ClaudeCodeInterface")
    @patch("sys.stdout", new_callable=StringIO)
    def test_test_connection_failure(self, mock_stdout, mock_interface_class):
        """Test failed connection test."""
        mock_interface = Mock()
        mock_interface.test_connection.return_value = (False, "Connection failed")
        mock_interface_class.return_value = mock_interface

        args = Namespace(claude_command="claude", timeout=3600)
        handle_test(args)

        output = mock_stdout.getvalue()
        assert "failed" in output.lower()


class TestHandleBankCommands:
    """Test bank-related CLI commands."""

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_save(self, mock_stdout, mock_storage_class):
        """Test saving a template to bank."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.save_prompt_to_bank.return_value = "/path/to/template.md"

        args = Namespace(name="test-template", priority=5)
        handle_bank_save(args)

        mock_storage.save_prompt_to_bank.assert_called_once_with(
            "test-template", priority=5
        )

        output = mock_stdout.getvalue()
        assert "saved" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_list(self, mock_stdout, mock_storage_class):
        """Test listing bank templates."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.list_bank_templates.return_value = [
            {"name": "template1", "title": "Template 1", "priority": 5},
            {"name": "template2", "title": "Template 2", "priority": 3},
        ]

        args = Namespace(json=False)
        handle_bank_list(args)

        output = mock_stdout.getvalue()
        assert "template1" in output
        assert "template2" in output

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_list_empty(self, mock_stdout, mock_storage_class):
        """Test listing bank when empty."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.list_bank_templates.return_value = []

        args = Namespace(json=False)
        handle_bank_list(args)

        output = mock_stdout.getvalue()
        assert "no templates" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_use(self, mock_stdout, mock_storage_class):
        """Test using a bank template."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        template_prompt = QueuedPrompt(
            id="new-123",
            content="Template content",
            priority=7,
        )
        mock_storage.use_bank_template.return_value = template_prompt

        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(name="test-template", working_dir=None)
        handle_bank_use(args)

        # Prompt should be added to queue
        assert len(state.prompts) == 1
        mock_storage.save_queue_state.assert_called_once()

        output = mock_stdout.getvalue()
        assert "added" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_use_nonexistent(self, mock_stdout, mock_storage_class):
        """Test using a non-existent bank template."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.use_bank_template.return_value = None

        args = Namespace(name="nonexistent", working_dir=None)
        handle_bank_use(args)

        output = mock_stdout.getvalue()
        assert "not found" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_delete(self, mock_stdout, mock_storage_class):
        """Test deleting a bank template."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.delete_bank_template.return_value = True

        args = Namespace(name="test-template")
        handle_bank_delete(args)

        mock_storage.delete_bank_template.assert_called_once_with("test-template")

        output = mock_stdout.getvalue()
        assert "deleted" in output.lower()

    @patch("claude_code_queue.cli.QueueStorage")
    @patch("sys.stdout", new_callable=StringIO)
    def test_bank_delete_nonexistent(self, mock_stdout, mock_storage_class):
        """Test deleting a non-existent bank template."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.delete_bank_template.return_value = False

        args = Namespace(name="nonexistent")
        handle_bank_delete(args)

        output = mock_stdout.getvalue()
        assert "not found" in output.lower()


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_with_invalid_permission_mode_raises_error(self, mock_storage_class):
        """Test that invalid permission mode raises error during add."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage.load_queue_state.return_value = QueueState()

        args = Namespace(
            prompt="Test",
            priority=5,
            context_files=None,
            permission_mode="invalid_mode",
            allowed_tools=None,
            timeout=None,
            model=None,
            working_dir=None,
        )

        # Should raise ValueError due to invalid permission mode
        with pytest.raises(ValueError):
            handle_add(args)

    @patch("claude_code_queue.cli.QueueStorage")
    def test_add_with_allowed_tools_list(self, mock_storage_class):
        """Test adding prompt with allowed tools list."""
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        state = QueueState()
        mock_storage.load_queue_state.return_value = state

        args = Namespace(
            prompt="Test",
            priority=5,
            context_files=None,
            permission_mode=None,
            allowed_tools=["Read", "Edit"],
            timeout=None,
            model=None,
            working_dir=None,
        )

        handle_add(args)

        assert state.prompts[0].allowed_tools == ["Read", "Edit"]
