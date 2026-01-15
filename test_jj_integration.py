#!/usr/bin/env python3
"""
Test script for jj integration functionality.
Run this after staging the jj_integration.py file.
"""

import os
import sys

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from claude_code_queue.jj_integration import JujutsuIntegration


def test_jj_integration():
    """Test the jj integration functionality."""
    print("Testing JJ Integration")
    print("=" * 50)

    # Test 1: Check if jj is available
    print("\n1. Checking if jj is in PATH...")
    is_available = JujutsuIntegration.is_jj_available()
    print(f"   Result: {is_available}")

    # Test 2: Check if current directory is a jj repository
    print("\n2. Checking if current directory is a jj repository...")
    is_repo = JujutsuIntegration.is_jj_repository(".")
    print(f"   Result: {is_repo}")

    # Test 3: Check should_create_change
    print("\n3. Checking if we should create a change...")
    should_create, reason = JujutsuIntegration.should_create_change(".")
    print(f"   Should create: {should_create}")
    if reason:
        print(f"   Reason: {reason}")

    # Test 4: Test create_new_change (dry run - would actually create a change)
    print("\n4. Testing change creation logic (format only, not actually creating)...")
    test_prompt_id = "abc123"
    test_prompt_content = "Add a new feature to handle automatic jj commit creation when working in a jj repository"

    short_desc = test_prompt_content[:80]
    if len(test_prompt_content) > 80:
        last_space = short_desc.rfind(" ")
        if last_space > 60:
            short_desc = short_desc[:last_space] + "..."
        else:
            short_desc = short_desc + "..."

    description = f"[{test_prompt_id}] {short_desc}"
    print(f"   Generated description: {description}")

    print("\n" + "=" * 50)
    print("All tests completed!")

    return 0


if __name__ == "__main__":
    sys.exit(test_jj_integration())
