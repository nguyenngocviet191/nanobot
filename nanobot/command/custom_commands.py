"""Custom slash commands loaded from markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter

from loguru import logger


class CustomCommandsLoader:
    """
    Load custom slash commands from markdown files.

    Directory: workspace/commands/*.md
    Each file defines one command with YAML frontmatter.
    """

    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?",
        re.DOTALL,
    )

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self.commands_dir = self.workspace / "commands"

    def get_command_content(self, name: str) -> str | None:
        """
        Get command content by name.

        Args:
            name: Command name (case-insensitive)

        Returns:
            Command content (markdown body after frontmatter) or None if not found
        """
        if not self.commands_dir.exists():
            return None

        file = self.commands_dir / f"{name.lower()}.md"
        if not file.exists():
            return None

        try:
            post = frontmatter.load(file)
            return post.content.strip()
        except Exception as e:
            logger.warning("Failed to load command {}: {}", name, e)
            return None

    def get_command_metadata(self, name: str) -> dict[str, Any] | None:
        """Get command metadata from frontmatter."""
        if not self.commands_dir.exists():
            return None

        file = self.commands_dir / f"{name.lower()}.md"
        if not file.exists():
            return None

        try:
            post = frontmatter.load(file)
            return dict(post.metadata)
        except Exception as e:
            logger.warning("Failed to load command metadata {}: {}", name, e)
            return None

    def list_commands(self) -> list[dict[str, str]]:
        """List all available commands with their metadata."""
        if not self.commands_dir.exists():
            return []

        commands = []
        for file in self.commands_dir.glob("*.md"):
            try:
                post = frontmatter.load(file)
                name = post.metadata.get("name", file.stem.lower())
                desc = post.metadata.get("description", "")
                commands.append({
                    "name": name,
                    "description": desc[:32] if desc else "",
                    "file": str(file),
                })
            except Exception:
                continue

        return commands

    def get_bot_commands(self) -> list[dict[str, str]]:
        """
        Get commands formatted for Telegram Bot API.
        Telegram limit: max 100 commands, description max 32 chars.
        """
        commands = self.list_commands()
        result = []
        for cmd in commands:
            result.append({
                "command": cmd["name"],
                "description": cmd["description"][:32],
            })
        return result[:100]

    def command_exists(self, name: str) -> bool:
        """Check if a command exists."""
        if not self.commands_dir.exists():
            return False
        return (self.commands_dir / f"{name.lower()}.md").exists()