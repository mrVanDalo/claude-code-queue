# JJ Integration Implementation

## Overview

I've implemented automatic jj (Jujutsu) change creation when working in a jj repository. When a prompt is executed, the system will automatically create a new jj change based on the `main` bookmark with a descriptive message containing the queue ID and prompt content.

## Files Changed/Added

### New Files

1. **src/claude_code_queue/jj_integration.py**

   - New module for jj integration functionality
   - Contains `JujutsuIntegration` class with methods:
     - `is_jj_available()`: Checks if jj command is in PATH
     - `is_jj_repository(working_dir)`: Checks if directory is a jj repository
     - `create_new_change(working_dir, prompt_id, prompt_content)`: Creates new jj change
     - `should_create_change(working_dir)`: Determines if a change should be created

1. **test_jj_integration.py**

   - Test script to verify the jj integration functionality
   - Can be run directly with Python to test the implementation

1. **JJ_INTEGRATION_IMPLEMENTATION.md**

   - This file - documentation of the implementation

### Modified Files

1. **src/claude_code_queue/claude_interface.py**

   - Added import of `JujutsuIntegration`
   - Modified `execute_prompt()` method to check for jj repository and create change before execution
   - Change creation happens after changing to working directory but before running Claude command

1. **pyproject.toml**

   - Added setuptools package finding configuration to ensure all modules are discovered

1. **flake.nix**

   - Updated source handling to use `pkgs.lib.fileset` for better control over included files

## How It Works

When a prompt is executed:

1. The system changes to the working directory
1. Checks if jj is in PATH
1. Checks if the working directory is a jj repository (looks for `.jj` directory in current or parent directories)
1. If both checks pass:
   - Creates a new jj change based on the `main` bookmark
   - Uses description format: `[queue_id] short description`
   - The short description is the first 80 characters of the prompt content
1. Proceeds with normal prompt execution

## Testing

### Before Building

**IMPORTANT**: The new `jj_integration.py` file needs to be tracked by version control before Nix can build it.

To stage the changes for building:

```bash
# If using jj (recommended for this project)
jj new -m "Add jj integration feature" main

# The changes are now tracked and Nix can build
```

### Running Tests

1. **Test the module directly (before building)**:

   ```bash
   python3 test_jj_integration.py
   ```

1. **Build and test the package**:

   ```bash
   # After staging the jj_integration.py file
   nix build
   ./result/bin/claude-queue --help
   ```

1. **Test with a real prompt**:

   ```bash
   # In a jj repository
   ./result/bin/claude-queue add "Test prompt" --working-dir /path/to/jj/repo
   ./result/bin/claude-queue start
   ```

### Expected Behavior

When executing a prompt in a jj repository:

- You should see: `Created jj change: <change info>`
- A new jj change will be created with description like: `[abc123] Test prompt`

When executing a prompt in a non-jj repository:

- You should see: `Skipping jj change creation: not a jj repository`

When jj is not in PATH:

- You should see: `Skipping jj change creation: jj not in PATH`

## Description Format

The jj change description follows the same format as `claude-queue list` and `claude-queue status --detailed`:

```
[queue_id] short description...
```

Where:

- `queue_id` is the prompt ID (e.g., "abc123")
- `short description` is the first 80 characters of the prompt content
- If the content is longer than 80 chars, it's truncated at a word boundary with "..." appended

Examples:

- `[a1b2c3] Fix authentication bug in login endpoint`
- `[d4e5f6] Add new feature to handle automatic jj commit creation when working...`

## Notes

- The change is created based on the `main` bookmark
- If jj change creation fails, a warning is printed but execution continues
- The working directory is always used as the repository root for jj commands
- The feature automatically detects `.jj` directories in the working directory or any parent directory
