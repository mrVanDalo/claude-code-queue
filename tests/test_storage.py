"""Unit tests for storage module."""

from datetime import datetime
from pathlib import Path

import pytest

from claude_code_queue.models import PromptStatus, QueuedPrompt, QueueState
from claude_code_queue.storage import MarkdownPromptParser, QueueStorage


class TestMarkdownPromptParser:
    """Test MarkdownPromptParser class."""

    def test_parse_simple_prompt(self, tmp_path):
        """Test parsing a simple markdown prompt without frontmatter."""
        content = "# Test Prompt\n\nThis is a simple prompt."
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        prompt = MarkdownPromptParser.parse_prompt_file(file_path)

        assert prompt is not None
        assert prompt.id == "test"
        assert "Test Prompt" in prompt.content
        assert prompt.working_directory == "."
        assert prompt.priority == 0

    def test_parse_prompt_with_frontmatter(self, tmp_path):
        """Test parsing prompt with YAML frontmatter."""
        content = """---
priority: 5
working_directory: /tmp/test
max_retries: 5
permission_mode: acceptEdits
model: opus
timeout: 600
context_files:
  - src/main.py
  - src/utils.py
---

# Test Prompt

This is a test prompt with frontmatter.
"""
        file_path = tmp_path / "test-123.md"
        file_path.write_text(content)

        prompt = MarkdownPromptParser.parse_prompt_file(file_path)

        assert prompt is not None
        assert prompt.id == "test"
        assert "Test Prompt" in prompt.content
        assert prompt.priority == 5
        assert prompt.working_directory == "/tmp/test"
        assert prompt.max_retries == 5
        assert prompt.permission_mode == "acceptEdits"
        assert prompt.model == "opus"
        assert prompt.timeout == 600
        assert prompt.context_files == ["src/main.py", "src/utils.py"]

    def test_parse_prompt_with_allowed_tools(self, tmp_path):
        """Test parsing prompt with allowed_tools in frontmatter."""
        content = """---
priority: 3
allowed_tools:
  - Read
  - Edit
  - Bash(git:*)
---

# Test Prompt

Test content.
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        prompt = MarkdownPromptParser.parse_prompt_file(file_path)

        assert prompt is not None
        assert prompt.allowed_tools == ["Read", "Edit", "Bash(git:*)"]

    def test_parse_prompt_id_from_filename(self, tmp_path):
        """Test extracting prompt ID from filename."""
        content = "Test content"

        file1 = tmp_path / "abc123.md"
        file1.write_text(content)
        prompt1 = MarkdownPromptParser.parse_prompt_file(file1)
        assert prompt1.id == "abc123"

        file2 = tmp_path / "xyz789-description.md"
        file2.write_text(content)
        prompt2 = MarkdownPromptParser.parse_prompt_file(file2)
        assert prompt2.id == "xyz789"

    def test_parse_invalid_yaml_frontmatter(self, tmp_path):
        """Test parsing prompt with invalid YAML frontmatter."""
        content = """---
invalid: yaml: content: here
priority = 5
---

# Test

Content
"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        prompt = MarkdownPromptParser.parse_prompt_file(file_path)

        # Should still parse, but with default metadata
        assert prompt is not None
        assert prompt.priority == 0  # Default when YAML is invalid

    def test_write_prompt_file_basic(self, tmp_path):
        """Test writing a basic prompt to file."""
        prompt = QueuedPrompt(
            id="test-123",
            content="# Test Prompt\n\nTest content here.",
            priority=5,
            working_directory="/tmp/test",
        )

        file_path = tmp_path / "test.md"
        success = MarkdownPromptParser.write_prompt_file(prompt, file_path)

        assert success is True
        assert file_path.exists()

        content = file_path.read_text()
        assert "---" in content
        assert "priority: 5" in content
        assert "working_directory: /tmp/test" in content
        assert "Test Prompt" in content

    def test_write_prompt_file_with_metadata(self, tmp_path):
        """Test writing prompt with full metadata."""
        now = datetime.now()
        prompt = QueuedPrompt(
            id="test-456",
            content="Test content",
            priority=3,
            working_directory="/home/user",
            context_files=["file1.py", "file2.py"],
            permission_mode="plan",
            allowed_tools=["Read", "Edit"],
            timeout=1200,
            model="haiku",
            max_retries=5,
            retry_count=2,
            last_executed=now,
        )

        file_path = tmp_path / "test.md"
        success = MarkdownPromptParser.write_prompt_file(prompt, file_path)

        assert success is True

        content = file_path.read_text()
        assert "priority: 3" in content
        assert "context_files:" in content
        assert "file1.py" in content
        assert "permission_mode: plan" in content
        assert "allowed_tools:" in content
        assert "timeout: 1200" in content
        assert "model: haiku" in content
        assert "max_retries: 5" in content
        assert "retry_count: 2" in content

    def test_write_prompt_with_execution_log(self, tmp_path):
        """Test writing prompt with execution log."""
        prompt = QueuedPrompt(id="test", content="Test")
        prompt.add_log("First log entry")
        prompt.add_log("Second log entry")

        file_path = tmp_path / "test.md"
        MarkdownPromptParser.write_prompt_file(prompt, file_path)

        content = file_path.read_text()
        assert "## Execution Log" in content
        assert "First log entry" in content
        assert "Second log entry" in content

    def test_get_base_filename(self):
        """Test generating base filename from prompt."""
        prompt = QueuedPrompt(
            id="abc123",
            content="This is a test prompt with a long title that should be truncated",
        )

        filename = MarkdownPromptParser.get_base_filename(prompt)

        assert filename.startswith("abc123-")
        assert filename.endswith(".md")
        assert len(filename) <= 58  # id + dash + 50 chars + .md

    def test_get_base_filename_sanitized(self):
        """Test filename sanitization removes invalid characters."""
        prompt = QueuedPrompt(
            id="test",
            content="Test with <invalid> chars: /\\|?*",
        )

        filename = MarkdownPromptParser.get_base_filename(prompt)

        assert "<" not in filename
        assert ">" not in filename
        assert "/" not in filename
        assert "\\" not in filename
        assert "|" not in filename
        assert "?" not in filename
        assert "*" not in filename


class TestQueueStorage:
    """Test QueueStorage class."""

    def test_initialization(self, tmp_path):
        """Test QueueStorage initialization creates directories."""
        storage = QueueStorage(str(tmp_path / "queue"))

        assert storage.base_dir.exists()
        assert storage.queue_dir.exists()
        assert storage.completed_dir.exists()
        assert storage.failed_dir.exists()

    def test_save_and_load_queue_state(self, tmp_path):
        """Test saving and loading queue state."""
        storage = QueueStorage(str(tmp_path / "queue"))

        # Create state with some data
        state = QueueState()
        state.total_processed = 10
        state.failed_count = 2
        state.rate_limited_count = 1
        state.last_processed = datetime.now()

        # Save state
        success = storage.save_queue_state(state)
        assert success is True

        # Load state
        loaded_state = storage.load_queue_state()
        assert loaded_state.total_processed == 10
        assert loaded_state.failed_count == 2
        assert loaded_state.rate_limited_count == 1
        assert loaded_state.last_processed is not None

    def test_save_single_prompt_queued(self, tmp_path):
        """Test saving a queued prompt."""
        storage = QueueStorage(str(tmp_path / "queue"))
        prompt = QueuedPrompt(
            id="test-123",
            content="Test prompt",
            status=PromptStatus.QUEUED,
        )

        success = storage._save_single_prompt(prompt)
        assert success is True

        # Check file exists in queue directory
        files = list(storage.queue_dir.glob("test-123*.md"))
        assert len(files) == 1
        assert not files[0].name.endswith(".executing.md")
        assert not files[0].name.endswith(".rate-limited.md")

    def test_save_single_prompt_executing(self, tmp_path):
        """Test saving an executing prompt."""
        storage = QueueStorage(str(tmp_path / "queue"))
        prompt = QueuedPrompt(
            id="test-456",
            content="Executing prompt",
            status=PromptStatus.EXECUTING,
        )

        storage._save_single_prompt(prompt)

        # Check file has .executing suffix
        files = list(storage.queue_dir.glob("test-456*.executing.md"))
        assert len(files) == 1

    def test_save_single_prompt_completed(self, tmp_path):
        """Test saving a completed prompt moves it to completed directory."""
        storage = QueueStorage(str(tmp_path / "queue"))
        prompt = QueuedPrompt(
            id="test-complete",
            content="Completed prompt",
            status=PromptStatus.COMPLETED,
        )

        storage._save_single_prompt(prompt)

        # Check file is in completed directory, not queue
        assert len(list(storage.completed_dir.glob("test-complete*.md"))) == 1
        assert len(list(storage.queue_dir.glob("test-complete*.md"))) == 0

    def test_save_single_prompt_failed(self, tmp_path):
        """Test saving a failed prompt moves it to failed directory."""
        storage = QueueStorage(str(tmp_path / "queue"))
        prompt = QueuedPrompt(
            id="test-fail",
            content="Failed prompt",
            status=PromptStatus.FAILED,
        )

        storage._save_single_prompt(prompt)

        # Check file is in failed directory
        assert len(list(storage.failed_dir.glob("test-fail*.md"))) == 1
        assert len(list(storage.queue_dir.glob("test-fail*.md"))) == 0

    def test_load_prompts_from_files(self, tmp_path):
        """Test loading prompts from markdown files."""
        storage = QueueStorage(str(tmp_path / "queue"))

        # Create some test files
        (storage.queue_dir / "test1-prompt.md").write_text("# Test 1")
        (storage.queue_dir / "test2-prompt.executing.md").write_text("# Test 2")

        prompts = storage._load_prompts_from_files()

        assert len(prompts) == 2

        # Check statuses are set correctly
        statuses = {p.id: p.status for p in prompts}
        assert statuses["test1"] == PromptStatus.QUEUED
        assert statuses["test2"] == PromptStatus.EXECUTING

    def test_remove_prompt_files(self, tmp_path):
        """Test removing all files for a prompt ID."""
        storage = QueueStorage(str(tmp_path / "queue"))

        # Create multiple files for same prompt ID
        (storage.queue_dir / "test-123-prompt.md").write_text("Test")
        (storage.queue_dir / "test-123-prompt.executing.md").write_text("Test")
        (storage.queue_dir / "test-123-#old.md").write_text("Test")

        storage._remove_prompt_files("test-123", storage.queue_dir)

        # All files should be removed
        assert len(list(storage.queue_dir.glob("test-123*.md"))) == 0

    def test_sanitize_filename_static(self):
        """Test filename sanitization."""
        sanitized = QueueStorage._sanitize_filename_static(
            "Test <file>: name/with\\chars|?*"
        )

        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized

    def test_sanitize_filename_truncates(self):
        """Test filename sanitization truncates to 50 chars."""
        long_text = "a" * 100
        sanitized = QueueStorage._sanitize_filename_static(long_text)

        assert len(sanitized) == 50

    def test_create_prompt_template(self, tmp_path):
        """Test creating a prompt template."""
        storage = QueueStorage(str(tmp_path / "queue"))

        file_path = storage.create_prompt_template("my-template", priority=5)

        assert file_path.exists()
        assert file_path.name == "my-template.md"

        content = file_path.read_text()
        assert "priority: 5" in content
        assert "Prompt Title" in content
        assert "permission_mode" in content

    def test_add_prompt_from_markdown(self, tmp_path):
        """Test adding a prompt from an existing markdown file."""
        storage = QueueStorage(str(tmp_path / "queue"))

        # Create a markdown file outside queue directory
        external_file = tmp_path / "external.md"
        external_file.write_text("---\npriority: 8\n---\n\n# Test")

        prompt = storage.add_prompt_from_markdown(external_file)

        assert prompt is not None
        assert prompt.status == PromptStatus.QUEUED
        assert prompt.priority == 8
        # File should be moved to queue directory
        assert not external_file.exists()
        assert len(list(storage.queue_dir.glob("external.md"))) == 1
