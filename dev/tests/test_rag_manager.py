"""
Tests for RAG Manager module.
"""

import pytest
import tempfile
from pathlib import Path
import json

from ryx_pkg.core.rag_manager import RAGManager, UserProfile


@pytest.fixture
def rag_manager(tmp_path):
    """Create a RAG manager with temp paths."""
    manager = RAGManager()
    manager.CONFIG_DIR = tmp_path
    manager.PROFILE_PATH = tmp_path / "profile.yaml"
    manager.HISTORY_PATH = tmp_path / "history.json"
    return manager


class TestProfileLoading:
    """Tests for profile loading."""
    
    @pytest.mark.asyncio
    async def test_create_default_profile(self, rag_manager):
        """Test creating default profile."""
        profile = await rag_manager.load_profile()
        
        assert profile is not None
        assert profile.name == "User"
        assert rag_manager.PROFILE_PATH.exists()
    
    @pytest.mark.asyncio
    async def test_load_existing_profile(self, rag_manager):
        """Test loading existing profile."""
        # Create profile file (JSON format for testing without yaml)
        profile_data = {
            "name": "Test User",
            "preferences": {"editor": "vim"},
            "directories": {},
            "knowledge": ["Python developer"],
        }
        rag_manager.PROFILE_PATH.write_text(json.dumps(profile_data))
        
        profile = await rag_manager.load_profile()
        
        assert profile.name == "Test User"
    
    @pytest.mark.asyncio
    async def test_profile_has_preferences(self, rag_manager):
        """Test profile has default preferences."""
        profile = await rag_manager.load_profile()
        
        assert "editor" in profile.preferences
        assert "terminal" in profile.preferences


class TestDocumentIndexing:
    """Tests for document indexing."""
    
    @pytest.mark.asyncio
    async def test_index_python_files(self, rag_manager, tmp_path):
        """Test indexing Python files."""
        # Create test files
        (tmp_path / "test.py").write_text("# test")
        (tmp_path / "readme.md").write_text("# readme")
        (tmp_path / "data.json").write_text("{}")
        
        files = await rag_manager.index_documents(str(tmp_path))
        
        assert len(files) == 3
    
    @pytest.mark.asyncio
    async def test_index_respects_max_files(self, rag_manager, tmp_path):
        """Test max_files limit."""
        # Create many files
        for i in range(10):
            (tmp_path / f"test{i}.py").write_text("# test")
        
        files = await rag_manager.index_documents(str(tmp_path), max_files=5)
        
        assert len(files) == 5
    
    @pytest.mark.asyncio
    async def test_index_nonexistent_directory(self, rag_manager):
        """Test indexing non-existent directory."""
        files = await rag_manager.index_documents("/nonexistent/dir")
        
        assert files == []


class TestContextGeneration:
    """Tests for context generation."""
    
    @pytest.mark.asyncio
    async def test_get_context_includes_profile(self, rag_manager):
        """Test context includes profile info."""
        await rag_manager.load_profile()
        rag_manager.profile.name = "Test User"
        
        context = await rag_manager.get_context("test query")
        
        assert "Test User" in context
    
    @pytest.mark.asyncio
    async def test_get_context_empty_without_profile(self, rag_manager):
        """Test context generation without profile."""
        context = await rag_manager.get_context("test query")
        
        # Should not raise, returns empty or minimal context
        assert isinstance(context, str)


class TestHistory:
    """Tests for conversation history."""
    
    @pytest.mark.asyncio
    async def test_save_and_get_history(self, rag_manager):
        """Test saving and retrieving history."""
        await rag_manager.save_history("user", "Hello")
        await rag_manager.save_history("assistant", "Hi there!")
        
        history = await rag_manager.get_history()
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_clear_history(self, rag_manager):
        """Test clearing history."""
        await rag_manager.save_history("user", "Hello")
        await rag_manager.clear_history()
        
        history = await rag_manager.get_history()
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_history_limit(self, rag_manager):
        """Test history retrieval limit."""
        for i in range(20):
            await rag_manager.save_history("user", f"Message {i}")
        
        history = await rag_manager.get_history(limit=5)
        
        assert len(history) == 5


class TestPreferences:
    """Tests for preference accessors."""
    
    @pytest.mark.asyncio
    async def test_get_user_preference(self, rag_manager):
        """Test getting user preference."""
        await rag_manager.load_profile()
        
        editor = rag_manager.get_user_preference("editor")
        
        assert editor is not None
    
    @pytest.mark.asyncio
    async def test_get_missing_preference(self, rag_manager):
        """Test getting missing preference."""
        await rag_manager.load_profile()
        
        result = rag_manager.get_user_preference("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_directory(self, rag_manager):
        """Test getting configured directory."""
        await rag_manager.load_profile()
        
        config_dir = rag_manager.get_directory("config")
        
        assert config_dir is not None
        assert "config" in config_dir.lower()


class TestUserProfile:
    """Tests for UserProfile dataclass."""
    
    def test_default_profile(self):
        """Test default profile values."""
        profile = UserProfile()
        
        assert profile.name == "User"
        assert isinstance(profile.preferences, dict)
        assert isinstance(profile.directories, dict)
        assert isinstance(profile.knowledge, list)
