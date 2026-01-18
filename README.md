# Claude Code Queue

Never wait for Claude Code token limits again. Queue your prompts, walk away, and let the system automatically execute them when limits reset.

## Why Use This?

**The Problem**: Claude Code has 5-hour token limit windows. When you hit the limit, you have to wait and manually retry your prompts.

**The Solution**: claude-code-queue runs prompts in the background, automatically detects rate limits, waits for the reset window, and resumes execution. You can queue up work for hours or overnight and come back to finished results.

## Key Features

- **Automatic Rate Limit Handling**: Detects when you hit limits and waits for the next reset window (5am, 10am, 3pm, 8pm)
- **Jujutsu (jj) Integration**: Automatically creates version control commits for each processed queue item - no manual commit management needed
- **Priority Queue**: Control execution order - run urgent fixes before large features
- **Markdown-Based**: Each prompt is just a `.md` file you can edit directly
- **Persistent & Reliable**: Survives system restarts, tracks retry counts, organizes completed/failed prompts
- **Model Selection**: Choose between Sonnet, Opus, and Haiku for different tasks

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

1. **Add Prompts**: Use `claude-queue add` or create markdown templates with detailed prompts
1. **Start Processing**: Run `claude-queue start` and the system processes prompts in priority order
1. **Smart Rate Limiting**: When Claude hits token limits, the system detects it, estimates the next reset window, and waits automatically
1. **Auto-Resume**: After the reset window, processing continues where it left off
1. **Version Control**: If you're using Jujutsu (jj), each prompt execution automatically creates a commit with the changes
1. **Organization**: Completed prompts move to `~/.claude-queue/completed/`, failed ones to `~/.claude-queue/failed/`

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

## Jujutsu (jj) Version Control Integration

**claude-code-queue understands Jujutsu** and automatically manages version control commits for you. When you queue prompts in a jj repository, each execution creates its own commit - no manual `jj new` or `jj commit` needed.

### How It Works

1. **Auto-Commit Creation**: Before executing each prompt, creates a new jj change based on `main` (or your specified bookmark)
1. **Smart Bookmarks**: Use `--bookmark feature-name` to automatically set a bookmark on the resulting commit
1. **Clean History**: Each queued task gets its own isolated commit, making history easier to review and manage
1. **Graceful Fallback**: Works perfectly fine in non-jj repositories too

### Example Workflow

```bash
# Queue multiple features, each gets its own commit
claude-queue add "Add user authentication" --bookmark auth --working-dir ~/my-project
claude-queue add "Add password reset" --bookmark pwd-reset --working-dir ~/my-project
claude-queue add "Add rate limiting" --bookmark rate-limit --working-dir ~/my-project

# Start processing - each task creates a separate jj commit with a bookmark
claude-queue start
```

Result: Three separate commits with bookmarks `auth`, `pwd-reset`, and `rate-limit`, each containing only its relevant changes.

### No jj? No Problem

If Jujutsu isn't available or you're using Git, the queue works normally without version control integration.

See [JJ_INTEGRATION_IMPLEMENTATION.md](JJ_INTEGRATION_IMPLEMENTATION.md) for technical details.

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

## Storage Organization

All queue data lives in `~/.claude-queue/`:

- `queue/` - Prompts waiting to be processed
- `completed/` - Successfully executed prompts (with full Claude output)
- `failed/` - Failed or cancelled prompts for review
- `queue-state.json` - Metadata, counters, and rate limit tracking

Each prompt is a markdown file you can view or edit directly.
