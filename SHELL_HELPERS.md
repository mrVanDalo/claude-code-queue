# Shell Helper Functions

Claude Code Queue includes convenient shell helper functions for Bash, Zsh, and Fish shells. These functions provide quick shortcuts for common operations.

## Installation

After building the package with `nix build`, the shell helper files are available at:

```
result/share/claude-code-queue/shell-helpers/
├── shell-helpers.bash  # For Bash and Zsh
├── shell-helpers.zsh   # Zsh-specific with advanced completions
└── shell-helpers.fish  # For Fish shell
```

### Bash

Add to your `~/.bashrc`:

```bash
source /path/to/result/share/claude-code-queue/shell-helpers/shell-helpers.bash
```

### Zsh

Add to your `~/.zshrc`:

```zsh
source /path/to/result/share/claude-code-queue/shell-helpers/shell-helpers.zsh
```

The Zsh version includes enhanced completions and can optionally bind `Ctrl-Q` for quick prompt adding:

```zsh
# Optional: Enable Ctrl-Q for quick prompt adding
bindkey '^Q' _cq_quick_add
```

### Fish

Add to your `~/.config/fish/config.fish`:

```fish
source /path/to/result/share/claude-code-queue/shell-helpers/shell-helpers.fish
```

Fish completions are automatically installed to `result/share/fish/vendor_completions.d/`.

## Available Functions

### Quick Commands

| Function | Description | Example |
|----------|-------------|---------|
| `cqa "prompt" [priority]` | Add prompt to queue | `cqa "Fix bug" 1` |
| `cqahere "prompt" [priority]` | Add prompt with current directory | `cqahere "Update docs"` |
| `cqs [--detailed] [--json]` | Show queue status | `cqs --detailed` |
| `cqsd` | Show detailed queue status | `cqsd` |
| `cqn [--verbose]` | Process next item | `cqn --verbose` |
| `cqstart [--verbose]` | Start queue processor | `cqstart` |
| `cql [--status] [--json]` | List all prompts | `cql --status failed` |
| `cqlq` | List queued prompts | `cqlq` |
| `cqlf` | List failed prompts | `cqlf` |
| `cqlc` | List completed prompts | `cqlc` |

### Prompt Management

| Function | Description | Example |
|----------|-------------|---------|
| `cqcancel <id>` | Cancel a prompt | `cqcancel abc123` |
| `cqdel <id>` | Delete a prompt permanently | `cqdel abc123` |
| `cqretry <id>` | Retry a failed prompt | `cqretry abc123` |
| `cqpath <id>` | Get path to prompt file | `cqpath abc123` |
| `cqedit <id>` | Edit prompt file in `$EDITOR` | `cqedit abc123` |

### Template Management

| Function | Description | Example |
|----------|-------------|---------|
| `cqtemplate <name> [priority]` | Create a template | `cqtemplate feature 2` |

### Bank Operations

| Function | Description | Example |
|----------|-------------|---------|
| `cqbank <command> [args...]` | Bank operations | `cqbank list` |
| `cqbsave <name> [priority]` | Save template to bank | `cqbsave update-docs 1` |
| `cqblist [--json]` | List bank templates | `cqblist` |
| `cqbuse <name>` | Use a bank template | `cqbuse update-docs` |
| `cqbdel <name>` | Delete a bank template | `cqbdel old-template` |

### Other

| Function | Description | Example |
|----------|-------------|---------|
| `cqtest` | Test Claude Code connection | `cqtest` |
| `cqhelp` | Show help message | `cqhelp` |

## Shell Completions

All three shell implementations include intelligent tab completions:

- **Command completion**: Type `claude-queue <TAB>` to see available commands
- **Option completion**: Type `claude-queue add --<TAB>` to see available options
- **Status filtering**: Type `claude-queue list --status <TAB>` to see status values
- **Model selection**: Type `claude-queue add "prompt" --model <TAB>` to see available models

### Zsh-Specific Features

The Zsh version includes:

- Detailed descriptions for each command and option
- Context-aware completions based on the current command
- File and directory completion for relevant options
- Optional widget for quick prompt adding (bind with `bindkey '^Q' _cq_quick_add`)

### Fish-Specific Features

The Fish version includes:

- Native Fish completions with descriptions
- Context-aware argument completion
- Automatic file and directory completion

## Examples

### Quick Workflow

```bash
# Add a quick task
cqa "Update README with new features" 1

# Check status
cqs

# Process the next item
cqn

# View detailed status
cqsd
```

### Working with Templates

```bash
# Create a template
cqtemplate my-feature 2

# Edit the template (opens in $EDITOR)
# ... make changes ...

# Save it to the bank for reuse
cqbsave my-feature 2

# Later, use the template
cqbuse my-feature
```

### Managing Failed Prompts

```bash
# List all failed prompts
cqlf

# Get details about a specific failed prompt
cqpath abc123

# Edit and retry
cqedit abc123
# ... fix the prompt ...
cqretry abc123
```

## Tips

1. **Use priorities wisely**: Lower numbers = higher priority (0 is highest)
1. **Use `cqahere`**: Automatically sets working directory to current location
1. **Check status frequently**: `cqs` shows overall queue health
1. **Edit before retrying**: Use `cqedit <id>` to modify failed prompts before retrying
1. **Bank common templates**: Save frequently-used prompts to the bank for quick reuse
1. **Use tab completion**: All shells support intelligent tab completion for commands and options

## Integration with Nix

When you install claude-code-queue via Nix, the shell helpers are automatically available in the package output:

```bash
# After nix build
ls -la result/share/claude-code-queue/shell-helpers/

# Or in a NixOS configuration
{ pkgs, ... }:
{
  environment.systemPackages = [ pkgs.claude-code-queue ];

  # The helpers are then available at:
  # /nix/store/.../share/claude-code-queue/shell-helpers/
}
```

## Development

If you're working on the shell helpers themselves:

```bash
# Enter development shell
nix develop

# The source files are in the repo root:
# - shell-helpers.bash
# - shell-helpers.zsh
# - shell-helpers.fish

# After making changes, rebuild
nix build

# Test the changes
source ./result/share/claude-code-queue/shell-helpers/shell-helpers.bash
```
