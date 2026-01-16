# JJ Integration Implementation

## Overview

claude-code-queue integrates with Jujutsu (jj), a Git-compatible version control system. When executing prompts in a jj repository, the system automatically creates new changes and manages bookmarks.

## Features

- **Automatic change creation**: Creates a new jj change before executing each prompt
- **Bookmark-based workflow**: Base changes on specified bookmarks or `main`
- **Bookmark setting on success**: Sets/moves bookmarks on successful prompt execution
- **Graceful degradation**: Works normally if jj is not available or directory is not a jj repo

## Module: jj_integration.py

### JujutsuIntegration Class

Located at `src/claude_code_queue/jj_integration.py`

**Methods:**

| Method | Description |
|--------|-------------|
| `is_jj_available()` | Checks if jj command is in PATH |
| `is_jj_repository(working_dir)` | Checks if directory is a jj repository (looks for `.jj`) |
| `create_new_change(working_dir, prompt_id, prompt_content, bookmark)` | Creates new jj change with descriptive message |
| `should_create_change(working_dir)` | Determines if a change should be created |
| `bookmark_exists(working_dir, bookmark)` | Checks if a bookmark exists |
| `set_bookmark(working_dir, bookmark)` | Sets/creates a bookmark on the current change |

## Workflow

### When a Prompt Executes

1. System changes to the working directory
1. Checks if jj is available (`which jj`)
1. Checks if directory is a jj repository (`.jj` directory exists)
1. If both checks pass:
   - Creates a new change based on bookmark (if specified) or `main`
   - Change description: `[queue_id] short description...`
1. Claude Code executes the prompt
1. On success: Sets/moves the bookmark to the resulting change

### Bookmark Behavior

**With `--bookmark` specified:**

```bash
claude-queue add "Implement feature" --bookmark feature-x --working-dir /path/to/jj-repo
```

- Creates change based on the `feature-x` bookmark (if exists) or `main`
- On success, sets `feature-x` bookmark on the resulting change
- Allows stacking changes on the same feature branch

**Without bookmark:**

- Creates change based on `main`
- No bookmark is set on success

## Change Description Format

```
[queue_id] short description...
```

- `queue_id`: The prompt's unique identifier (e.g., "abc123")
- `short description`: First 80 characters of prompt content (truncated at word boundary)

**Examples:**

```
[a1b2c3] Fix authentication bug in login endpoint
[d4e5f6] Add new feature to handle automatic jj commit creation when working...
```

## CLI Usage

### Add prompt with bookmark

```bash
claude-queue add "Implement feature X" --bookmark feature-x -d /path/to/jj-repo
```

### YAML frontmatter

```yaml
---
priority: 1
working_directory: /path/to/jj-repo
bookmark: feature-x
---

Implement feature X...
```

## Expected Output

**When creating change in jj repository:**

```
Created jj change: [abc123] Fix authentication bug
```

**When not a jj repository:**

```
Skipping jj change creation: not a jj repository
```

**When jj not available:**

```
Skipping jj change creation: jj not in PATH
```

**On successful execution with bookmark:**

```
Set bookmark 'feature-x' on current change
```

## Integration Points

### claude_interface.py

The `ClaudeCodeInterface.execute_prompt()` method:

1. Calls `JujutsuIntegration.should_create_change()` before execution
1. Calls `JujutsuIntegration.create_new_change()` if appropriate
1. Proceeds with normal Claude execution

### queue_manager.py

The `QueueManager._process_execution_result()` method:

1. On successful execution, checks if bookmark was specified
1. Calls `JujutsuIntegration.set_bookmark()` to set the bookmark

## Error Handling

- Change creation failures: Warning printed, execution continues
- Bookmark setting failures: Warning printed, prompt still marked successful
- jj unavailable: Silently skipped, normal execution proceeds

## Testing

Run tests for jj integration:

```bash
nix develop
pytest tests/test_jj_integration.py -v
```

Or test manually:

```bash
# In a jj repository
./result/bin/claude-queue add "Test prompt" --bookmark test-branch -d .
./result/bin/claude-queue start
jj log  # Verify change was created
```

## Notes

- Changes are created based on bookmark or `main` bookmark
- If the specified bookmark doesn't exist, falls back to `main`
- The `.jj` directory can be in the working directory or any parent
- All jj commands run in the prompt's working directory
