# Claude Code Queue

A tool to queue Claude Code prompts and automatically execute them when token limits reset, preventing manual waiting during 5-hour limit windows.

## Features

- **Markdown-based Queue**: Each prompt is a `.md` file with YAML frontmatter
- **Automatic Rate Limit Handling**: Detects rate limits and waits for reset windows
- **Priority System**: Execute high-priority prompts first
- **Retry Logic**: Automatically retry failed prompts
- **Persistent Storage**: Queue survives system restarts
- **CLI Interface**: Simple command-line interface
- **Jujutsu Integration**: Auto-create jj changes for prompts in jj repositories
- **Model Selection**: Choose between Sonnet, Opus, and Haiku models

## Installation

### NixOS / Nix Flakes (Recommended)

```bash
# Run directly without installing
nix run github:mrVanDalo/claude-code-queue

# Or from local directory
nix run .

# Install to your profile
nix profile install github:mrVanDalo/claude-code-queue

# Enter development shell with all tools
nix develop
```

For NixOS, add to your `flake.nix` inputs and use the package.

### PyPI

```bash
pip install claude-code-queue
```

## Shell Helper Functions

For a better user experience, claude-code-queue includes convenient shell helper functions for Bash, Zsh, and Fish shells. These provide quick shortcuts for common operations.

**Quick installation:**

After building with Nix, the shell helpers are available at:

```bash
# Bash
source result/share/claude-code-queue/shell-helpers/shell-helpers.bash

# Zsh
source result/share/claude-code-queue/shell-helpers/shell-helpers.zsh

# Fish
source result/share/claude-code-queue/shell-helpers/shell-helpers.fish
```

**Example usage:**

```bash
cqa "Fix authentication bug" 1    # Quick add with priority
cqs                                # Show status
cqn                                # Process next item
cqlf                               # List failed prompts
cqhelp                             # Show all available functions
```

See [SHELL_HELPERS.md](SHELL_HELPERS.md) for complete documentation of all helper functions and shell completions.

## Quick Start

After installation, use the `claude-queue` command:

1. **Test Claude Code connection:**

   ```bash
   claude-queue test
   ```

1. **Add a quick prompt:**

   ```bash
   claude-queue add "Fix the authentication bug" --priority 1
   ```

1. **Create a detailed prompt template:**

   ```bash
   claude-queue template my-feature --priority 2
   # Edit ~/.claude-queue/queue/my-feature.md with your prompt
   ```

1. **Start the queue processor:**

   ```bash
   claude-queue start
   ```

## Usage

### Adding Prompts

**Quick prompt:**

```bash
claude-queue add "Implement user authentication" --priority 1 --working-dir /path/to/project
```

**With model selection:**

```bash
claude-queue add "Complex refactoring task" --model opus --priority 1
```

**With jj bookmark (for Jujutsu repositories):**

```bash
claude-queue add "Add new feature" --bookmark feature-branch --working-dir /path/to/jj-repo
```

**Template for detailed prompt:**

```bash
claude-queue template auth-feature
```

This creates `~/.claude-queue/queue/auth-feature.md`:

```markdown
---
priority: 0
working_directory: .
context_files: []
max_retries: 3
estimated_tokens: null
permission_mode: acceptEdits
allowed_tools: []
timeout: 3600
model: sonnet
bookmark: null
---

# Prompt Title

Write your prompt here...

## Context

Any additional context or requirements...

## Expected Output

What should be delivered...
```

### Managing the Queue

**Check status:**

```bash
claude-queue status --detailed
```

**List prompts:**

```bash
claude-queue list --status queued
```

**Cancel a prompt:**

```bash
claude-queue cancel abc123
```

**Delete prompts permanently:**

```bash
claude-queue delete abc123 def456
```

### Running the Queue

**Start processing:**

```bash
claude-queue start
```

**Start with verbose output:**

```bash
claude-queue start --verbose
```

**Process single item:**

```bash
claude-queue next
```

## How It Works

1. **Queue Processing**: Runs prompts in priority order (lower number = higher priority)
1. **Rate Limit Detection**: Monitors Claude Code output for rate limit messages
1. **Smart Reset Estimation**: Estimates reset time based on 5-hour windows (5am, 10am, 3pm, 8pm)
1. **Automatic Waiting**: When rate limited, waits until estimated reset time then resumes
1. **Retry Logic**: Failed prompts are retried up to `max_retries` times
1. **File Organization**:
   - `~/.claude-queue/queue/` - Pending prompts
   - `~/.claude-queue/completed/` - Successful executions
   - `~/.claude-queue/failed/` - Failed prompts
   - `~/.claude-queue/queue-state.json` - Queue metadata

## Configuration

### Command Line Options

```bash
claude-queue --help
```

Key options:

- `--storage-dir`: Queue storage location (default: `~/.claude-queue`)
- `--claude-command`: Claude CLI command (default: `claude`)
- `--check-interval`: Check interval in seconds (default: 30)
- `--timeout`: Command timeout in seconds (default: 3600)

### Prompt Configuration

Each prompt supports these YAML frontmatter options:

```yaml
---
priority: 1                      # Execution priority (0 = highest)
working_directory: /path/to/project
context_files:                   # Files to include as context
    - src/main.py
    - README.md
max_retries: 3                   # Maximum retry attempts
estimated_tokens: 1000           # Estimated token usage (optional)
permission_mode: acceptEdits     # Permission mode (default: acceptEdits)
allowed_tools:                   # Specific tools to allow (optional)
    - Edit
    - Write
    - Read
    - Bash(git:*)
timeout: 3600                    # Timeout in seconds (optional)
model: sonnet                    # Model: sonnet, opus, or haiku
bookmark: feature-branch         # jj bookmark name (optional)
---
```

**Permission Modes:**

- `acceptEdits` (default): Auto-accepts file edits, prompts for other operations
- `bypassPermissions`: Skip all permission checks (like old behavior)
- `dontAsk`: Don't ask for permissions, proceed automatically
- `default`: Use standard interactive prompts (not recommended for queue)
- `delegate`: Delegate permission decisions
- `plan`: Plan mode

**Allowed Tools Examples:**

- `["Edit", "Write", "Read"]` - Only file operations
- `["Bash(git:*)"]` - Only git commands
- `["Edit", "Bash(npm:*)", "Bash(pytest:*)"]` - Edits and specific commands
- Leave empty `[]` to allow no tools, or omit to allow all tools

**Model Options:**

- `sonnet` (default): Balanced speed and capability
- `opus`: Most capable model
- `haiku`: Fastest, most efficient model

## Examples

### Basic Usage

```bash
# Add a simple prompt
claude-queue add "Run tests and fix any failures" --priority 1

# Create template for complex prompt
claude-queue template database-migration --priority 2

# Start processing
claude-queue start
```

### Complex Prompt Template

```markdown
---
priority: 1
working_directory: /Users/me/my-project
context_files:
    - src/auth.py
    - tests/test_auth.py
    - docs/auth-requirements.md
max_retries: 2
estimated_tokens: 2000
model: opus
---

# Fix Authentication Bug

There's a bug in the user authentication system where users can't log in with special characters in their passwords.

## Context

-   The issue affects passwords containing @, #, $ symbols
-   Error occurs in the password validation function
-   Tests are failing in test_auth.py

## Requirements

1. Fix the password validation to handle special characters
2. Update tests to cover edge cases
3. Ensure backward compatibility

## Expected Output

-   Fixed authentication code
-   Updated test cases
-   Documentation update if needed
```

## Rate Limit Handling

The system automatically detects Claude Code rate limits by monitoring:

- "usage limit reached" messages
- Claude's reset time information
- Standard rate limit error patterns

When rate limited:

1. Prompt returns to QUEUED status (preserving retry count)
1. System estimates the next reset window (5-hour intervals)
1. Waits until estimated reset time (with small buffer)
1. Automatically resumes processing

The rate limit state persists across restart, so the daemon remembers if it was rate limited.

## Jujutsu (jj) Integration

When working in a Jujutsu repository, claude-code-queue can automatically create new changes for each prompt execution:

- **Automatic change creation**: Creates a new change based on `main` or specified bookmark
- **Bookmark support**: Use `--bookmark` to specify which bookmark to base the change on
- **Bookmark setting**: On successful execution, sets a bookmark on the resulting change
- **Graceful degradation**: Works normally if jj is not available

```bash
# Add prompt with jj bookmark
claude-queue add "Implement feature X" --bookmark feature-x --working-dir /path/to/jj-repo
```

See [JJ_INTEGRATION_IMPLEMENTATION.md](JJ_INTEGRATION_IMPLEMENTATION.md) for details.

## Troubleshooting

**Queue not processing:**

```bash
# Check Claude Code connection
claude-queue test

# Check queue status
claude-queue status --detailed
```

**Prompts stuck in executing state:**

- Stop queue processor (Ctrl+C)
- Restart with `claude-queue start`
- Executing prompts will be processed on restart

**Rate limit not detected:**

- Check if Claude Code output format changed
- File an issue with the error message you received

## Directory Structure

```
~/.claude-queue/
├── queue/               # Pending prompts
│   ├── 001-fix-bug.md
│   └── 002-feature.executing.md
├── completed/           # Successful executions
│   └── 001-fix-bug-completed.md
├── failed/              # Failed prompts
│   └── 003-failed-task.md
└── queue-state.json     # Queue metadata
```
