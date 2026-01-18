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
        working_dir: str,
        prompt_id: str,
        prompt_content: str,
        bookmark: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Create a new jj change based on a bookmark or main.

        If a bookmark is provided:
          - If the bookmark exists, create the change based on that bookmark
          - If the bookmark doesn't exist, create the change based on main

        Args:
            working_dir: Path to the working directory
            prompt_id: The queue prompt ID
            prompt_content: The prompt content for the description
            bookmark: Optional bookmark name to base the change on

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

            # Determine the base revision
            if bookmark and JujutsuIntegration.bookmark_exists(working_dir, bookmark):
                base_revision = bookmark
            else:
                base_revision = "main"

            # Run jj new command
            cmd = [
                "jj",
                "new",
                "-m",
                description,
                base_revision,
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
                base_info = f" (based on {base_revision})"
                return True, f"Created jj change: {change_info}{base_info}"
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

    @staticmethod
    def bookmark_exists(working_dir: str, bookmark_name: str) -> bool:
        """
        Check if a bookmark exists in the repository.

        Args:
            working_dir: Path to the working directory
            bookmark_name: Name of the bookmark to check

        Returns:
            True if the bookmark exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["jj", "bookmark", "list", "--all"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False

            # Parse the output to check for the bookmark
            # jj bookmark list output format: "bookmark_name: commit_id"
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Extract bookmark name (before the colon or first whitespace)
                    parts = line.split(":")
                    if parts:
                        existing_bookmark = parts[0].strip()
                        if existing_bookmark == bookmark_name:
                            return True

            return False

        except Exception:
            return False

    @staticmethod
    def set_bookmark(
        working_dir: str, bookmark_name: str, create: bool = False
    ) -> Tuple[bool, str]:
        """
        Set a bookmark to point to the current working copy commit.

        Args:
            working_dir: Path to the working directory
            bookmark_name: Name of the bookmark to set
            create: If True, create the bookmark if it doesn't exist

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["jj", "bookmark"]
            if create:
                cmd.append("create")
            else:
                cmd.append("set")

            cmd.append(bookmark_name)

            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                action = "Created and set" if create else "Set"
                return True, f"{action} bookmark '{bookmark_name}'"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, f"Failed to set bookmark: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Timeout while setting bookmark"
        except FileNotFoundError:
            return False, "jj command not found in PATH"
        except Exception as e:
            return False, f"Error setting bookmark: {str(e)}"

    @staticmethod
    def has_working_copy_changes(working_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the working copy has any changes (modified, added, or removed files).

        Uses 'jj status' to detect if there are any uncommitted changes
        in the working directory, including untracked files.

        Args:
            working_dir: Path to the working directory

        Returns:
            Tuple of (has_changes, error_message_if_failed)
            - (True, None) if there are changes
            - (False, None) if there are no changes
            - (False, "error message") if jj command failed
        """
        try:
            # Check if this is a jj repository first
            if not JujutsuIntegration.is_jj_repository(working_dir):
                return False, "not a jj repository"

            # Use jj status to check for changes (includes untracked files)
            result = subprocess.run(
                ["jj", "status"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, f"jj status failed: {error_msg}"

            # Parse jj status output to detect changes
            # Status shows "Working copy changes:" if there are changes
            # And "Working copy : <change-id>" with "No changes."/"The working copy is clean." if clean
            output = result.stdout.strip()

            # Check for indicators of changes (including untracked files)
            has_changes = (
                "Working copy changes:" in output
                or "Added " in output
                or "Modified " in output
                or "Removed " in output
            )

            # Also check for "clean" indicators to be sure
            is_clean = "No changes." in output or "The working copy is clean." in output

            return has_changes and not is_clean, None

        except subprocess.TimeoutExpired:
            return False, "Timeout while checking for changes"
        except FileNotFoundError:
            return False, "jj command not found in PATH"
        except Exception as e:
            return False, f"Error checking for changes: {str(e)}"
