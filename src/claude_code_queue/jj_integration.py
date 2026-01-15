"""
Jujutsu (jj) integration utilities for automatic change creation.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class JujutsuIntegration:
    """Handles Jujutsu version control integration."""

    @staticmethod
    def is_jj_available() -> bool:
        """Check if jj command is available in PATH."""
        return shutil.which("jj") is not None

    @staticmethod
    def is_jj_repository(working_dir: str) -> bool:
        """
        Check if the working directory is a jj repository.

        Args:
            working_dir: Path to the working directory

        Returns:
            True if the directory is a jj repository, False otherwise
        """
        try:
            working_path = Path(working_dir).resolve()
            if not working_path.exists():
                return False

            # Check if .jj directory exists in this or any parent directory
            current = working_path
            while current != current.parent:
                jj_dir = current / ".jj"
                if jj_dir.exists() and jj_dir.is_dir():
                    return True
                current = current.parent

            return False
        except Exception:
            return False

    @staticmethod
    def create_new_change(
        working_dir: str, prompt_id: str, prompt_content: str
    ) -> Tuple[bool, str]:
        """
        Create a new jj change based on the main bookmark.

        Args:
            working_dir: Path to the working directory
            prompt_id: The queue prompt ID
            prompt_content: The prompt content for the description

        Returns:
            Tuple of (success, message)
        """
        try:
            # Format the description like in list/status --detailed
            # Extract first line or first 80 chars for short description
            short_desc = prompt_content[:80]
            if len(prompt_content) > 80:
                # Try to break at a word boundary
                last_space = short_desc.rfind(" ")
                if last_space > 60:
                    short_desc = short_desc[:last_space] + "..."
                else:
                    short_desc = short_desc + "..."

            # Create description in the format: [queue_id] short description
            description = f"[{prompt_id}] {short_desc}"

            # Run jj new command
            cmd = [
                "jj",
                "new",
                "-m",
                description,
                "main",
            ]

            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Extract change ID from output if possible
                change_info = result.stdout.strip() if result.stdout else "created"
                return True, f"Created jj change: {change_info}"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, f"Failed to create jj change: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Timeout while creating jj change"
        except FileNotFoundError:
            return False, "jj command not found in PATH"
        except Exception as e:
            return False, f"Error creating jj change: {str(e)}"

    @staticmethod
    def should_create_change(working_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if a jj change should be created.

        Args:
            working_dir: Path to the working directory

        Returns:
            Tuple of (should_create, reason_if_not)
        """
        # Check if jj is in PATH
        if not JujutsuIntegration.is_jj_available():
            return False, "jj not in PATH"

        # Check if working directory is a jj repository
        if not JujutsuIntegration.is_jj_repository(working_dir):
            return False, "not a jj repository"

        return True, None
