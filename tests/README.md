# Test Suite for claude-code-queue

This directory contains comprehensive tests for the claude-code-queue project.

## Test Organization

- `conftest.py` - Shared pytest fixtures and configuration
- `test_models.py` - Unit tests for data models (QueuedPrompt, QueueState, RateLimitInfo, ExecutionResult)
- `test_storage.py` - Unit tests for storage layer (MarkdownPromptParser, QueueStorage)
- `test_claude_interface.py` - Unit tests for Claude Code CLI interface
- `test_queue_manager.py` - Integration tests for queue management and execution lifecycle
- `test_cli.py` - Tests for CLI commands and argument handling

## Running Tests

### Using Nix (recommended)

```bash
# Enter development environment
nix develop

# Run all tests
pytest

# Run with coverage
pytest --cov=src/claude_code_queue --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py -v

# Run specific test
pytest tests/test_models.py::TestQueuedPrompt::test_can_retry_when_failed_with_retries_remaining -v
```

### Using the test runner script

```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Test Coverage

The test suite aims for comprehensive coverage:

- **Unit Tests**: Test individual components in isolation

  - Models: Data structures, validation, state transitions
  - Storage: File I/O, markdown parsing, persistence
  - Claude Interface: Command building, timeout handling, rate limit detection

- **Integration Tests**: Test component interactions

  - Queue Manager: Execution lifecycle, retry logic, signal handling
  - CLI: Command handlers, argument parsing, output formatting

## Fixtures

Common fixtures are defined in `conftest.py`:

- `sample_prompt` - Basic QueuedPrompt for testing
- `sample_prompts` - Multiple prompts with different statuses
- `sample_queue_state` - QueueState with sample data
- `temp_queue_dir` - Temporary directory structure for storage tests
- `mock_claude_output_*` - Sample Claude Code outputs for testing

## Markers

Tests are marked with pytest markers for filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.cli` - CLI tests
- `@pytest.mark.slow` - Slow-running tests

Run specific markers:

```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention: `test_<module>.py`
1. Group related tests in classes: `class TestFeatureName`
1. Use descriptive test names: `test_feature_does_what_when_condition`
1. Add docstrings to explain what the test verifies
1. Use fixtures from conftest.py where appropriate
1. Mock external dependencies (subprocess calls, file I/O when needed)

Example:

```python
class TestMyFeature:
    """Test MyFeature class."""

    def test_feature_succeeds_with_valid_input(self, sample_prompt):
        """Test that feature works correctly with valid input."""
        result = my_feature(sample_prompt)
        assert result.success is True
```

## Continuous Integration

These tests should be run as part of CI/CD:

```bash
nix flake check  # Runs Nix build checks
pytest           # Runs test suite
nix fmt          # Formats code
```
