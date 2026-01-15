#!/usr/bin/env bash
# Test runner script for claude-code-queue

set -e

echo "Running tests for claude-code-queue..."
echo ""

# Run pytest with coverage
python -m pytest tests/ -v --cov=src/claude_code_queue --cov-report=term-missing --cov-report=html

echo ""
echo "Test run complete!"
