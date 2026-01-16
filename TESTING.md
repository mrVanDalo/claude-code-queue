# Testing Documentation for claude-code-queue

## Overview

This project now has a comprehensive test suite using pytest that covers all major components of the claude-code-queue system.

## Test Framework

**Framework**: pytest
**Coverage Tool**: pytest-cov
**Test Location**: `tests/` directory

## Test Files

| File | Description | Test Count (approx) |
|------|-------------|---------------------|
| `tests/test_models.py` | Unit tests for data models | 45+ tests |
| `tests/test_storage.py` | Unit tests for storage layer | 30+ tests |
| `tests/test_claude_interface.py` | Unit tests for Claude CLI interface | 25+ tests |
| `tests/test_queue_manager.py` | Integration tests for queue manager | 15+ tests |
| `tests/test_cli.py` | CLI command handler tests | 20+ tests |

**Total**: 135+ comprehensive tests

## Running Tests

### Quick Start

```bash
# Enter Nix development environment
nix develop

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src/claude_code_queue --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/test_models.py -v

# Run specific test class
pytest tests/test_models.py::TestQueuedPrompt -v

# Run specific test
pytest tests/test_models.py::TestQueuedPrompt::test_can_retry_when_failed_with_retries_remaining -v
```

### Using the Test Runner Script

```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Test Coverage Areas

### 1. Data Models (`test_models.py`)

**QueuedPrompt**:

- Default and custom initialization
- Permission mode validation
- Log entry management
- Retry logic (`can_retry()`)
- Execution timing (`should_execute_now()`)

**QueueState**:

- Prompt management (add, remove, get)
- Next prompt selection with priority ordering
- Rate limit handling
- Statistics generation

**RateLimitInfo**:

- Rate limit detection from various message formats
- Pattern matching (case-insensitive)
- Timestamp parsing

**ExecutionResult**:

- Success/failure states
- Rate limit information
- Execution time tracking

### 2. Storage Layer (`test_storage.py`)

**MarkdownPromptParser**:

- YAML frontmatter parsing
- Prompt ID extraction from filenames
- Context files and metadata handling
- File writing with execution logs
- Filename sanitization

**QueueStorage**:

- Directory structure initialization
- State persistence (save/load)
- Prompt file organization by status
- File moving between directories
- Template creation

### 3. Claude Interface (`test_claude_interface.py`)

**ClaudeCodeInterface**:

- CLI availability verification
- Command construction with models, permissions, tools
- Working directory management
- Timeout handling (global and per-prompt)
- Rate limit detection from output
- Reset time estimation
- Context file references
- Exception handling

### 4. Queue Manager (`test_queue_manager.py`)

**QueueManager**:

- Initialization and configuration
- Graceful shutdown with state preservation
- Connection testing
- Execution lifecycle (success, failure, rate limit)
- Retry logic for rate-limited prompts
- State counter updates
- Callback functionality

### 5. CLI Commands (`test_cli.py`)

**Command Handlers**:

- `add`: Prompt creation with various options
- `status`: Queue statistics (text and JSON output)
- `list`: Filtering by status
- `cancel`: Prompt cancellation
- `delete`: Permanent prompt deletion (supports multiple IDs)
- `retry`: Retry failed prompts
- `path`: Get prompt file path
- `test`: Connection testing

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src/claude_code_queue
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests for individual components
    integration: Integration tests for component interactions
    cli: CLI command tests
    slow: Slow-running tests
```

### Fixtures (conftest.py)

Common test fixtures:

- `sample_prompt`: Basic QueuedPrompt
- `sample_prompts`: Multiple prompts with different statuses
- `sample_queue_state`: QueueState with sample data
- `temp_queue_dir`: Temporary directory structure
- `mock_claude_output_*`: Sample Claude outputs for testing

## Mocking Strategy

Tests use `unittest.mock` to mock external dependencies:

1. **Subprocess calls**: Mock `subprocess.run` for Claude CLI interactions
1. **File I/O**: Use pytest's `tmp_path` fixture for isolated file operations
1. **Time-dependent tests**: Mock `datetime.now()` for consistent timing
1. **Signal handling**: Mock signal handlers in queue manager tests

## Coverage Goals

- **Unit Tests**: 80%+ coverage on core logic
- **Integration Tests**: 60%+ coverage overall
- **Critical Paths**: 100% coverage for queue execution, retry logic, rate limit handling

## Continuous Integration

Tests should be run as part of CI/CD:

```bash
nix flake check  # Runs Nix build checks
pytest           # Runs test suite
nix fmt          # Formats code
```

## Best Practices

1. **Descriptive Names**: Test names follow `test_<what>_<when>_<expected>` pattern
1. **Docstrings**: Each test has a docstring explaining what it verifies
1. **Isolation**: Tests don't depend on each other or external state
1. **Fixtures**: Reuse common test data via fixtures
1. **Assertions**: Clear, specific assertions with meaningful messages
1. **Mocking**: Mock external dependencies, test real logic

## Adding New Tests

When adding features:

1. Write tests first (TDD approach recommended)
1. Follow existing file organization
1. Add fixtures to `conftest.py` if reusable
1. Update this documentation
1. Ensure coverage doesn't decrease

## Troubleshooting

### Import Errors

Ensure you're in the Nix development environment:

```bash
nix develop
```

### Coverage Not Found

Install pytest-cov:

```bash
# Already included in flake.nix dev environment
nix develop
```

### Tests Failing

Check that you've formatted code:

```bash
nix fmt
```

## Future Improvements

Potential test enhancements:

- [ ] End-to-end tests with real Claude CLI (optional integration tests)
- [ ] Performance/load testing for large queues
- [ ] Concurrency tests for file locking
- [ ] Property-based testing with Hypothesis
- [ ] Mutation testing for test quality verification

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
