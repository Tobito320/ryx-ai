# Task 2.6: RAG Manager Skeleton

**Time:** 45 min | **Priority:** HIGH | **Agent:** Claude Opus

## Objective

Create a skeleton implementation of `RAGManager` that loads user profile from `~/.config/ryx/profile.yaml`, provides basic document indexing (file listing without vector DB), and returns context for queries.

## Output File(s)

- `ryx/core/rag_manager.py`
- `tests/test_rag_manager.py`

## Requirements

### Profile Loading

Load user profile from `~/.config/ryx/profile.yaml`:

```yaml
# Example profile.yaml
name: "User Name"
preferences:
  editor: "nvim"
  terminal: "alacritty"
  browser: "zen"
  theme: "dracula"
directories:
  config: "~/.config"
  projects: "~/projects"
  notes: "~/notes"
knowledge:
  - "Arch Linux user"
  - "Hyprland window manager"
  - "Python developer"
```

### Core Methods

1. `load_profile() -> Dict`
   - Load profile from YAML file
   - Create default profile if not exists
   - Return profile dictionary

2. `index_documents(directory: str) -> List[str]`
   - List files in directory (no vector indexing yet)
   - Support common file extensions
   - Return list of file paths

3. `get_context(query: str) -> str`
   - Return profile information
   - Return relevant file paths
   - Format as context string for LLM

4. `save_history(role: str, content: str) -> None`
   - Save conversation turn to JSON file
   - Location: `~/.config/ryx/history.json`
   - Append-only operation

5. `get_history(limit: int = 10) -> List[Dict]`
   - Get recent conversation history
   - Return list of {role, content, timestamp}

### File Structure

```
~/.config/ryx/
├── profile.yaml      # User profile
├── history.json      # Conversation history
└── audit.log         # Permission audit log (from Task 2.2)
```

## Code Template

```python
"""
Ryx AI - RAG Manager
Profile loading, document indexing, and context retrieval
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import yaml
import aiofiles


@dataclass
class UserProfile:
    """User profile configuration."""
    name: str = "User"
    preferences: Dict[str, str] = field(default_factory=lambda: {
        "editor": "nvim",
        "terminal": "alacritty",
        "browser": "firefox",
        "theme": "dracula",
    })
    directories: Dict[str, str] = field(default_factory=lambda: {
        "config": "~/.config",
        "projects": "~/projects",
        "notes": "~/notes",
    })
    knowledge: List[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RAGManager:
    """
    Manages RAG (Retrieval Augmented Generation) context.
    
    Features:
        - User profile loading from YAML
        - Basic document indexing (file listing)
        - Context generation for LLM queries
        - Conversation history management
    
    Note:
        This is a skeleton implementation. Full implementation
        would include vector indexing with ChromaDB or similar.
    
    Example:
        rag = RAGManager()
        await rag.load_profile()
        context = await rag.get_context("find my config files")
    """
    
    CONFIG_DIR = Path.home() / ".config" / "ryx"
    PROFILE_PATH = CONFIG_DIR / "profile.yaml"
    HISTORY_PATH = CONFIG_DIR / "history.json"
    
    # Supported file extensions for indexing
    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
        ".sh", ".bash", ".zsh",
        ".conf", ".config", ".ini",
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
        
        Returns:
            UserProfile object with user configuration
            
        Creates default profile if file doesn't exist.
        """
        if self.PROFILE_PATH.exists():
            try:
                async with aiofiles.open(self.PROFILE_PATH, 'r') as f:
                    content = await f.read()
                data = yaml.safe_load(content) or {}
                self.profile = UserProfile(
                    name=data.get("name", "User"),
                    preferences=data.get("preferences", {}),
                    directories=data.get("directories", {}),
                    knowledge=data.get("knowledge", []),
                )
            except Exception:
                self.profile = UserProfile()
        else:
            # Create default profile
            self.profile = UserProfile()
            await self._save_profile()
        
        return self.profile
    
    async def _save_profile(self) -> None:
        """Save current profile to YAML file."""
        if self.profile is None:
            return
        
        data = {
            "name": self.profile.name,
            "preferences": self.profile.preferences,
            "directories": self.profile.directories,
            "knowledge": self.profile.knowledge,
        }
        
        async with aiofiles.open(self.PROFILE_PATH, 'w') as f:
            await f.write(yaml.dump(data, default_flow_style=False))
    
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
            context_parts.append(f"  Editor: {self.profile.preferences.get('editor', 'unknown')}")
            context_parts.append(f"  Terminal: {self.profile.preferences.get('terminal', 'unknown')}")
            
            if self.profile.knowledge:
                context_parts.append("  Knowledge:")
                for k in self.profile.knowledge:
                    context_parts.append(f"    - {k}")
            
            context_parts.append("")
        
        # Add relevant files (simple keyword matching for now)
        if self.indexed_files:
            query_lower = query.lower()
            relevant_files = [
                f for f in self.indexed_files
                if any(word in f.lower() for word in query_lower.split())
            ][:10]  # Limit to 10 files
            
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
                async with aiofiles.open(self.HISTORY_PATH, 'r') as f:
                    data = await f.read()
                history = json.loads(data) if data else []
            except Exception:
                history = []
        
        # Append new turn
        history.append(asdict(turn))
        
        # Keep only last 100 turns
        history = history[-100:]
        
        # Save
        async with aiofiles.open(self.HISTORY_PATH, 'w') as f:
            await f.write(json.dumps(history, indent=2))
    
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
            async with aiofiles.open(self.HISTORY_PATH, 'r') as f:
                data = await f.read()
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
```

## Unit Tests

```python
import pytest
import tempfile
from pathlib import Path
import yaml
import json

from ryx.core.rag_manager import RAGManager, UserProfile


@pytest.fixture
def rag_manager(tmp_path):
    manager = RAGManager()
    manager.CONFIG_DIR = tmp_path
    manager.PROFILE_PATH = tmp_path / "profile.yaml"
    manager.HISTORY_PATH = tmp_path / "history.json"
    return manager


class TestProfileLoading:
    @pytest.mark.asyncio
    async def test_create_default_profile(self, rag_manager):
        profile = await rag_manager.load_profile()
        
        assert profile is not None
        assert profile.name == "User"
        assert rag_manager.PROFILE_PATH.exists()
    
    @pytest.mark.asyncio
    async def test_load_existing_profile(self, rag_manager):
        # Create profile file
        profile_data = {
            "name": "Test User",
            "preferences": {"editor": "vim"},
            "knowledge": ["Python developer"],
        }
        rag_manager.PROFILE_PATH.write_text(yaml.dump(profile_data))
        
        profile = await rag_manager.load_profile()
        
        assert profile.name == "Test User"
        assert profile.preferences["editor"] == "vim"
        assert "Python developer" in profile.knowledge


class TestDocumentIndexing:
    @pytest.mark.asyncio
    async def test_index_python_files(self, rag_manager, tmp_path):
        # Create test files
        (tmp_path / "test.py").write_text("# test")
        (tmp_path / "readme.md").write_text("# readme")
        (tmp_path / "data.json").write_text("{}")
        
        files = await rag_manager.index_documents(str(tmp_path))
        
        assert len(files) == 3
    
    @pytest.mark.asyncio
    async def test_index_respects_max_files(self, rag_manager, tmp_path):
        # Create many files
        for i in range(10):
            (tmp_path / f"test{i}.py").write_text("# test")
        
        files = await rag_manager.index_documents(str(tmp_path), max_files=5)
        
        assert len(files) == 5


class TestContextGeneration:
    @pytest.mark.asyncio
    async def test_get_context_includes_profile(self, rag_manager):
        await rag_manager.load_profile()
        rag_manager.profile.name = "Test User"
        
        context = await rag_manager.get_context("test query")
        
        assert "Test User" in context


class TestHistory:
    @pytest.mark.asyncio
    async def test_save_and_get_history(self, rag_manager):
        await rag_manager.save_history("user", "Hello")
        await rag_manager.save_history("assistant", "Hi there!")
        
        history = await rag_manager.get_history()
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_clear_history(self, rag_manager):
        await rag_manager.save_history("user", "Hello")
        await rag_manager.clear_history()
        
        history = await rag_manager.get_history()
        assert len(history) == 0
```

## Acceptance Criteria

- [ ] `UserProfile` dataclass with name, preferences, directories, knowledge
- [ ] `ConversationTurn` dataclass with role, content, timestamp
- [ ] `load_profile()` loads from `~/.config/ryx/profile.yaml`
- [ ] `load_profile()` creates default profile if not exists
- [ ] `index_documents()` lists files by extension
- [ ] `index_documents()` supports recursive search
- [ ] `index_documents()` respects max_files limit
- [ ] `get_context()` returns profile information
- [ ] `get_context()` returns relevant file paths
- [ ] `save_history()` appends to JSON file
- [ ] `get_history()` returns recent conversation turns
- [ ] History limited to 100 turns maximum
- [ ] Config directory created if not exists
- [ ] Unit tests passing

## Notes

- This is a skeleton implementation without vector embeddings
- Full implementation would use ChromaDB or similar for semantic search
- Profile YAML should be human-editable
- History is JSON for easy inspection
- Use `aiofiles` for all file operations
- Context generation is keyword-based for now
