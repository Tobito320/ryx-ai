"""
Ryx AI - RAG Manager
Manages user profiles, document indexing, and context retrieval.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class UserProfile:
    """User profile for personalization."""

    name: str = "User"
    preferences: Dict[str, Any] = field(default_factory=dict)
    directories: Dict[str, str] = field(default_factory=dict)
    knowledge: List[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RAGManager:
    """
    Manages RAG (Retrieval-Augmented Generation) context.

    Features:
        - User profile loading from YAML
        - Document indexing by file extension
        - Conversation history storage
        - Context generation for LLM prompts

    Example:
        rag = RAGManager()
        await rag.load_profile()
        context = await rag.get_context("find python files")
    """

    # Configuration paths
    CONFIG_DIR = Path.home() / ".config" / "ryx"
    PROFILE_PATH = CONFIG_DIR / "profile.yaml"
    HISTORY_PATH = CONFIG_DIR / "history.json"

    # Supported file extensions for indexing
    SUPPORTED_EXTENSIONS = {
        ".py",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sh",
    }

    def __init__(self):
        """Initialize the RAG Manager."""
        self.profile: Optional[UserProfile] = None
        self.indexed_files: List[str] = []

        # Ensure config directory exists
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    async def load_profile(self) -> UserProfile:
        """
        Load user profile from YAML file.

        Creates default profile if not exists.

        Returns:
            UserProfile object
        """
        if not self.PROFILE_PATH.exists():
            # Create default profile
            self.profile = UserProfile(
                name="User",
                preferences={
                    "editor": "nvim",
                    "terminal": "kitty",
                    "shell": "zsh",
                },
                directories={
                    "config": "~/.config",
                    "projects": "~/projects",
                },
                knowledge=[],
            )
            await self.save_profile()
        else:
            # Load existing profile
            try:
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(self.PROFILE_PATH, "r") as f:
                        data = await f.read()
                else:
                    data = self.PROFILE_PATH.read_text()

                if YAML_AVAILABLE:
                    profile_data = yaml.safe_load(data)
                else:
                    profile_data = json.loads(data)

                self.profile = UserProfile(
                    name=profile_data.get("name", "User"),
                    preferences=profile_data.get("preferences", {}),
                    directories=profile_data.get("directories", {}),
                    knowledge=profile_data.get("knowledge", []),
                )
            except Exception:
                # Fall back to default
                self.profile = UserProfile()

        return self.profile

    async def save_profile(self) -> None:
        """Save user profile to YAML file."""
        if self.profile is None:
            return

        profile_data = asdict(self.profile)

        try:
            if YAML_AVAILABLE:
                content = yaml.dump(profile_data, default_flow_style=False)
            else:
                content = json.dumps(profile_data, indent=2)

            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self.PROFILE_PATH, "w") as f:
                    await f.write(content)
            else:
                self.PROFILE_PATH.write_text(content)
        except Exception:
            pass

    async def index_documents(
        self,
        directory: str,
        recursive: bool = True,
        max_files: int = 1000,
    ) -> List[str]:
        """
        Index documents in a directory.

        Args:
            directory: Directory to index
            recursive: Search recursively
            max_files: Maximum number of files to index

        Returns:
            List of indexed file paths

        Note:
            This is a basic implementation that only lists files.
            Full implementation would create vector embeddings.
        """
        dir_path = Path(directory).expanduser().resolve()

        if not dir_path.exists():
            return []

        files = []

        if recursive:
            for ext in self.SUPPORTED_EXTENSIONS:
                for file_path in dir_path.rglob(f"*{ext}"):
                    if len(files) >= max_files:
                        break
                    files.append(str(file_path))
        else:
            for file_path in dir_path.iterdir():
                if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                    if len(files) >= max_files:
                        break
                    files.append(str(file_path))

        self.indexed_files.extend(files)
        return files

    async def get_context(self, query: str) -> str:
        """
        Get context for a query.

        Args:
            query: User's query

        Returns:
            Context string for LLM prompt
        """
        context_parts = []

        # Add profile information
        if self.profile:
            context_parts.append("User Profile:")
            context_parts.append(f"  Name: {self.profile.name}")
            context_parts.append(
                f"  Editor: {self.profile.preferences.get('editor', 'unknown')}"
            )
            context_parts.append(
                f"  Terminal: {self.profile.preferences.get('terminal', 'unknown')}"
            )

            if self.profile.knowledge:
                context_parts.append("  Knowledge:")
                for k in self.profile.knowledge:
                    context_parts.append(f"    - {k}")

            context_parts.append("")

        # Add relevant files (simple keyword matching for now)
        if self.indexed_files:
            query_lower = query.lower()
            relevant_files = [
                f
                for f in self.indexed_files
                if any(word in f.lower() for word in query_lower.split())
            ][
                :10
            ]  # Limit to 10 files

            if relevant_files:
                context_parts.append("Relevant Files:")
                for f in relevant_files:
                    context_parts.append(f"  - {f}")
                context_parts.append("")

        # Add recent history
        history = await self.get_history(limit=3)
        if history:
            context_parts.append("Recent Conversation:")
            for turn in history:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")[:100]
                context_parts.append(f"  [{role}]: {content}...")
            context_parts.append("")

        return "\n".join(context_parts)

    async def save_history(self, role: str, content: str) -> None:
        """
        Save a conversation turn to history.

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        turn = ConversationTurn(role=role, content=content)

        # Load existing history
        history = []
        if self.HISTORY_PATH.exists():
            try:
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(self.HISTORY_PATH, "r") as f:
                        data = await f.read()
                else:
                    data = self.HISTORY_PATH.read_text()
                history = json.loads(data) if data else []
            except Exception:
                history = []

        # Append new turn
        history.append(asdict(turn))

        # Keep only last 100 turns
        history = history[-100:]

        # Save
        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self.HISTORY_PATH, "w") as f:
                    await f.write(json.dumps(history, indent=2))
            else:
                self.HISTORY_PATH.write_text(json.dumps(history, indent=2))
        except Exception:
            pass

    async def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.

        Args:
            limit: Maximum number of turns to return

        Returns:
            List of conversation turns
        """
        if not self.HISTORY_PATH.exists():
            return []

        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self.HISTORY_PATH, "r") as f:
                    data = await f.read()
            else:
                data = self.HISTORY_PATH.read_text()
            history = json.loads(data) if data else []
            return history[-limit:]
        except Exception:
            return []

    async def clear_history(self) -> None:
        """Clear conversation history."""
        if self.HISTORY_PATH.exists():
            self.HISTORY_PATH.unlink()

    def get_user_preference(self, key: str) -> Optional[str]:
        """
        Get a user preference value.

        Args:
            key: Preference key (e.g., "editor", "terminal")

        Returns:
            Preference value or None
        """
        if self.profile and self.profile.preferences:
            return self.profile.preferences.get(key)
        return None

    def get_directory(self, key: str) -> Optional[str]:
        """
        Get a configured directory path.

        Args:
            key: Directory key (e.g., "config", "projects")

        Returns:
            Expanded directory path or None
        """
        if self.profile and self.profile.directories:
            path = self.profile.directories.get(key)
            if path:
                return str(Path(path).expanduser())
        return None
