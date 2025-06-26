# Quick Test Instructions

Follow these steps to test the Claude Code Queue system:

## 1. Setup

```bash
cd /Users/jcjustin/Projects/claude-utils/claude-code-queue
pip install -r requirements.txt
```

## 2. Test Claude Code Connection

```bash
python claude_queue.py test
```
Expected output: `✓ Claude Code CLI is working`

## 3. Add a Simple Test Prompt

```bash
python claude_queue.py add "What is 2+2?" --priority 1
```
Expected output: `✓ Added prompt [id] to queue`

## 4. Create a Template for More Complex Prompt

```bash
python claude_queue.py template test-feature --priority 2
```

This creates `~/.claude-queue/queue/test-feature.md`. Edit it with:

```markdown
---
priority: 2
working_directory: .
context_files: []
max_retries: 3
estimated_tokens: null
---

# Test Feature

Please create a simple Python function that calculates the factorial of a number.

## Requirements
- Function should handle edge cases (0, negative numbers)
- Include basic error handling
- Add a docstring

## Expected Output
A complete Python function with documentation.
```

## 5. Check Queue Status

```bash
python claude_queue.py status --detailed
```

Expected output shows:
- 2 prompts in queue
- Status breakdown
- Detailed prompt list

## 6. List All Prompts

```bash
python claude_queue.py list
```

## 7. Start the Queue Processor (Test Run)

```bash
python claude_queue.py start --verbose
```

This will:
- Execute the first prompt (priority 1): "What is 2+2?"
- Then execute the template prompt (priority 2)
- Show verbose output of what's happening

**Press Ctrl+C to stop the queue processor**

## 8. Check Results

```bash
# Check final status
python claude_queue.py status --detailed

# Look at completed prompts
ls ~/.claude-queue/completed/

# Read a completed prompt to see the execution log
cat ~/.claude-queue/completed/*.md
```

## 9. Test Rate Limiting (Optional)

If you want to test rate limiting behavior, create several prompts:

```bash
python claude_queue.py add "Explain Python decorators" --priority 1
python claude_queue.py add "Write a sorting algorithm" --priority 2  
python claude_queue.py add "Create a REST API example" --priority 3
python claude_queue.py add "Explain machine learning basics" --priority 4

# Start processor - it will run until rate limited
python claude_queue.py start
```

When rate limited, you'll see:
- `⚠ Prompt [id] rate limited, reset in [time]`
- Queue will wait until reset time
- Then automatically resume processing

## 10. Cleanup (Optional)

```bash
# Remove queue directory
rm -rf ~/.claude-queue
```

## Expected Behavior

✅ **Success**: Prompts execute in priority order, results saved to completed directory
✅ **Rate Limiting**: System detects limits, waits for reset, then continues
✅ **Persistence**: Queue survives restarts (stop with Ctrl+C, restart with same command)
✅ **Error Handling**: Failed prompts are retried automatically

## Troubleshooting

**"Claude Code CLI not found"**:
- Make sure `claude` command works in terminal
- Use `--claude-command /path/to/claude` if needed

**"No prompts in queue"**:
- Check `python claude_queue.py list`
- Ensure prompts were added successfully

**Prompts stuck in "executing"**:
- Stop queue processor (Ctrl+C)
- Restart - executing prompts will reset to queued