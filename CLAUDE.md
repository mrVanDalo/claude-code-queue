# Claude Code Instructions for claude-code-queue

A tool to queue Claude Code prompts and automatically execute them when token limits reset, preventing manual waiting during 5-hour limit windows.

## Project Overview

**Purpose**: Queue management system for Claude Code prompts with persistent storage, automatic rate limit detection, retry logic, and Jujutsu (jj) version control integration.

**Core Architecture**:

- **State-based workflow**: Prompts flow through QUEUED -> EXECUTING -> COMPLETED/FAILED/CANCELLED
- **Priority queue**: Lower priority number = higher execution priority
- **Markdown storage**: Each prompt is a `.md` file with YAML frontmatter
- **Rate limit awareness**: Automatic detection and wait-for-reset handling

## Critical Development Rules

### DO NOT USE PIP INSTALL

**NEVER run `pip install` in this project.** This project must be built and tested using Nix only. Do not use pip install, pip install -e ., or any pip commands.

### ALWAYS RUN NIX FMT

At the end of EVERY task that modifies code, you MUST run `nix fmt` to format all code. This is mandatory.

```bash
nix fmt
```

## Development Environment

```bash
nix develop    # Enter dev shell with all tools
```

## Build and Test Commands

```bash
nix flake check          # Check flake for errors
nix build                # Build the package
nix run . -- --help      # Run directly
./result/bin/claude-queue --help  # Test built binary
```

## Code Quality

```bash
nix fmt     # Format all code (required after changes)
mypy src/   # Type checking (inside nix develop)
pytest      # Run tests (inside nix develop)
```

## Project Structure

```
src/claude_code_queue/
├── __init__.py
├── models.py           # Data models: QueuedPrompt, QueueState, RateLimitInfo, ExecutionResult
├── storage.py          # Persistence: MarkdownPromptParser, QueueStorage
├── claude_interface.py # Claude CLI execution: ClaudeCodeInterface
├── jj_integration.py   # Jujutsu VCS integration: JujutsuIntegration
├── queue_manager.py    # Core queue processing: QueueManager
└── cli.py              # CLI commands and argument parsing

tests/
├── conftest.py         # Shared fixtures
├── test_models.py      # Model unit tests
├── test_storage.py     # Storage unit tests
├── test_claude_interface.py
├── test_queue_manager.py
└── test_cli.py

shell-helpers.bash      # Bash/Zsh helper functions
shell-helpers.zsh       # Zsh-specific helpers with completions
shell-helpers.fish      # Fish shell helpers

flake.nix               # Nix flake definition
pyproject.toml          # Python project metadata
treefmt.nix             # Code formatting configuration
```

## Key Modules

### models.py

- `PromptStatus`: Enum (QUEUED, EXECUTING, COMPLETED, FAILED, CANCELLED)
- `QueuedPrompt`: Single prompt with metadata (priority, working_dir, max_retries, etc.)
- `QueueState`: Overall queue state with counters and rate limit info
- `RateLimitInfo`: Rate limit detection and reset time tracking
- `ExecutionResult`: Execution outcome (success, failure, rate_limited)

### storage.py

- `MarkdownPromptParser`: Parses/writes markdown files with YAML frontmatter
- `QueueStorage`: File-based persistence in `~/.claude-queue/`
  - `queue/` - Pending and executing prompts
  - `completed/` - Successful executions
  - `failed/` - Failed/cancelled prompts
  - `queue-state.json` - Metadata and counters

### claude_interface.py

- `ClaudeCodeInterface`: Executes prompts via subprocess
  - Rate limit detection from Claude output
  - Reset time estimation (5-hour windows)
  - Support for permission modes, models, allowed tools

### jj_integration.py

- `JujutsuIntegration`: Auto-creates jj changes for prompts
  - Creates change based on bookmark or main branch
  - Sets bookmarks on successful execution
  - Gracefully skips if jj unavailable

### queue_manager.py

- `QueueManager`: Orchestrates queue processing
  - Main loop with rate limit awareness
  - Retry logic and counter management
  - Signal handling for graceful shutdown

### cli.py

Commands: `start`, `next`, `add`, `template`, `status`, `list`, `cancel`, `delete`, `retry`, `path`, `test`

## CLI Options Reference

```bash
# Global options
--storage-dir PATH      # Queue storage (default: ~/.claude-queue)
--claude-command CMD    # Claude CLI command (default: claude)
--check-interval SECS   # Check interval (default: 30)
--timeout SECS          # Global timeout (default: 3600)

# Add command options
--priority/-p N         # Priority (lower = higher, default: 0)
--working-dir/-d PATH   # Working directory
--context-files/-f FILE # Include context files
--max-retries/-r N      # Max retries (default: 3)
--permission-mode MODE  # acceptEdits|bypassPermissions|default|delegate|dontAsk|plan
--allowed-tools TOOLS   # Restrict allowed tools
--prompt-timeout SECS   # Per-prompt timeout
--model/-m MODEL        # sonnet|opus|haiku
--bookmark/-b NAME      # jj bookmark name
```

## Testing Changes Workflow

1. Create new jj change: `jj new -m "<summary of task>" main`
2. Enter dev environment: `nix develop`
3. Make changes
4. Format code: `nix fmt`
5. Build: `nix build`
6. Verify: `./result/bin/claude-queue --help`
7. Run tests: `pytest`
8. Check flake: `nix flake check`

## Rate Limit Handling

The system detects rate limits via patterns in Claude's output and estimates reset times based on 5-hour windows (5am, 10am, 3pm, 8pm relative to execution). When rate limited:

1. Prompt returns to QUEUED status
2. Rate limit state persists at daemon level
3. System sleeps until estimated reset time
4. Processing resumes automatically

## Permission Modes

- `acceptEdits` (default): Auto-accepts file edits, prompts for other operations
- `bypassPermissions`: Skip all permission checks
- `dontAsk`: Proceed automatically without asking
- `default`: Standard interactive prompts (not recommended for queue)
- `delegate`: Delegate permission decisions
- `plan`: Plan mode

## Dependencies

- PyYAML >= 6.0
- Python >= 3.8
- Claude CLI (external)
- jj (Jujutsu) - optional, for VCS integration
