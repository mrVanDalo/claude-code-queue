"""Pytest configuration and shared fixtures."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from claude_code_queue.models import (
    PromptStatus,
    QueuedPrompt,
    QueueState,
    RateLimitInfo,
)


@pytest.fixture
def sample_prompt():
    """Create a sample queued prompt for testing."""
    return QueuedPrompt(
        id="test-prompt-123",
        content="Test prompt content",
        priority=5,
        status=PromptStatus.QUEUED,
        created_at=datetime.now(),
        working_directory="/tmp/test",
        model="sonnet",
        permission_mode="acceptEdits",
    )


@pytest.fixture
def sample_prompts():
    """Create multiple sample prompts with different statuses."""
    now = datetime.now()
    return [
        QueuedPrompt(
            id="queued-1",
            content="Queued prompt 1",
            priority=10,
            status=PromptStatus.QUEUED,
            created_at=now,
            working_directory="/tmp/test",
        ),
        QueuedPrompt(
            id="queued-2",
            content="Queued prompt 2",
            priority=5,
            status=PromptStatus.QUEUED,
            created_at=now,
            working_directory="/tmp/test",
        ),
        QueuedPrompt(
            id="executing-1",
            content="Executing prompt",
            priority=8,
            status=PromptStatus.EXECUTING,
            created_at=now,
            working_directory="/tmp/test",
        ),
        QueuedPrompt(
            id="completed-1",
            content="Completed prompt",
            priority=7,
            status=PromptStatus.COMPLETED,
            created_at=now,
            working_directory="/tmp/test",
        ),
        QueuedPrompt(
            id="failed-1",
            content="Failed prompt",
            priority=6,
            status=PromptStatus.FAILED,
            created_at=now,
            working_directory="/tmp/test",
        ),
    ]


@pytest.fixture
def sample_queue_state(sample_prompts):
    """Create a sample queue state with multiple prompts."""
    return QueueState(prompts=sample_prompts)


@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create a temporary directory structure for queue storage."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / "queued").mkdir()
    (queue_dir / "executing").mkdir()
    (queue_dir / "completed").mkdir()
    (queue_dir / "failed").mkdir()
    (queue_dir / "cancelled").mkdir()
    (queue_dir / "rate_limited").mkdir()
    return queue_dir


@pytest.fixture
def mock_claude_output_success():
    """Sample successful Claude Code output."""
    return """Processing prompt...
Task completed successfully.
"""


@pytest.fixture
def mock_claude_output_rate_limit():
    """Sample Claude Code output with rate limit error."""
    return """Error: Rate limit exceeded.
Please try again in 1 hour and 30 minutes.
Your rate limit will reset at 2026-01-15 15:30:00.
"""


@pytest.fixture
def mock_claude_output_rate_limit_alt():
    """Alternative rate limit message format."""
    return """API Error: Too many requests.
Rate limit will reset in 45 minutes.
"""


@pytest.fixture
def sample_markdown_prompt():
    """Sample markdown file content with YAML frontmatter."""
    return """---
id: test-123
priority: 5
status: queued
created_at: '2026-01-15T10:00:00'
working_dir: /tmp/test
model: sonnet
permission_mode: auto
timeout: 300
retry_count: 0
max_retries: 3
---

# Test Prompt

This is a test prompt with markdown content.

## Details

- Item 1
- Item 2
"""


@pytest.fixture
def sample_markdown_with_context():
    """Sample markdown with context files."""
    return """---
id: test-with-context
priority: 7
status: queued
created_at: '2026-01-15T10:00:00'
working_dir: /tmp/test
context_files:
  - src/main.py
  - src/utils.py
allowed_tools:
  - Read
  - Edit
  - Bash
---

# Test Prompt with Context

Analyze these files and suggest improvements.
"""
