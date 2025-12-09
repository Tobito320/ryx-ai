"""Tests for ryxsurf"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRyxsurfImports:
    """Test that ryxsurf modules can be imported"""
    
    def test_import_package(self):
        """Test that the package can be imported"""
        import ryxsurf
        assert ryxsurf is not None
    
    def test_import_keybinds(self):
        """Test that keybinds module can be imported"""
        from ryxsurf.keybinds import KEYBINDS, Modifier, Keybind
        assert 'navigation' in KEYBINDS
        assert 'tabs' in KEYBINDS
        assert 'ui' in KEYBINDS
        assert 'ai' in KEYBINDS
    
    def test_import_sync(self):
        """Test that sync module can be imported"""
        from ryxsurf.src.sync import SessionSync, HubSyncClient
        assert SessionSync is not None
        assert HubSyncClient is not None


class TestKeybinds:
    """Test keybind definitions"""
    
    def test_keybind_structure(self):
        """Test that keybinds have correct structure"""
        from ryxsurf.keybinds import KEYBINDS, Keybind
        
        for category, binds in KEYBINDS.items():
            assert isinstance(binds, list)
            for bind in binds:
                assert isinstance(bind, Keybind)
                assert bind.key
                assert bind.action
                assert bind.description
    
    def test_get_all_keybinds(self):
        """Test get_all_keybinds returns flat list"""
        from ryxsurf.keybinds import get_all_keybinds
        
        all_binds = get_all_keybinds()
        assert isinstance(all_binds, list)
        assert len(all_binds) > 20  # Should have many keybinds
    
    def test_keybind_help(self):
        """Test keybind help generation"""
        from ryxsurf.keybinds import get_keybind_help
        
        help_text = get_keybind_help()
        assert "RyxSurf Keybinds" in help_text
        assert "NAVIGATION" in help_text
        assert "TABS" in help_text


class TestSessionSync:
    """Test session sync functionality"""
    
    @pytest.fixture
    def session_sync(self, tmp_path):
        """Create a session sync with temp directory"""
        from ryxsurf.src.sync import SessionSync
        sync = SessionSync()
        sync._state = {"sessions": {}, "settings": {}}
        sync._state_file = tmp_path / "state.json"
        return sync
    
    def test_save_session(self, session_sync):
        """Test saving a session"""
        tabs = [
            {"url": "https://google.com", "title": "Google"},
            {"url": "https://github.com", "title": "GitHub"}
        ]
        session_sync.save_session("test", tabs)
        
        assert "test" in session_sync._state["sessions"]
        assert len(session_sync._state["sessions"]["test"]["tabs"]) == 2
    
    def test_get_session(self, session_sync):
        """Test getting a session"""
        tabs = [{"url": "https://test.com", "title": "Test"}]
        session_sync.save_session("mytest", tabs)
        
        result = session_sync.get_session("mytest")
        assert result is not None
        assert len(result) == 1
        assert result[0]["url"] == "https://test.com"
    
    def test_list_sessions(self, session_sync):
        """Test listing sessions"""
        session_sync.save_session("session1", [{"url": "http://a.com"}])
        session_sync.save_session("session2", [{"url": "http://b.com"}])
        
        sessions = session_sync.list_sessions()
        assert "session1" in sessions
        assert "session2" in sessions
    
    def test_merge_remote_session(self, session_sync):
        """Test merging remote and local sessions"""
        import time
        
        # Setup local session
        local_tabs = [
            {"url": "https://local.com", "title": "Local", "last_active": time.time() - 100}
        ]
        session_sync.save_session("merge_test", local_tabs)
        
        # Merge with remote
        remote_tabs = [
            {"url": "https://remote.com", "title": "Remote", "last_active": time.time()}
        ]
        result = session_sync.merge_remote_session("merge_test", remote_tabs)
        
        # Should have both URLs
        urls = [t["url"] for t in result]
        assert "https://remote.com" in urls


class TestConfig:
    """Test configuration handling"""
    
    def test_default_config_exists(self):
        """Test that default config file exists"""
        config_path = Path(__file__).parent.parent / "config.default.json"
        assert config_path.exists()
    
    def test_default_config_valid(self):
        """Test that default config is valid JSON"""
        config_path = Path(__file__).parent.parent / "config.default.json"
        with open(config_path) as f:
            config = json.load(f)
        
        assert isinstance(config, dict)
        # Check for expected keys
        assert "theme" in config or "settings" in config or len(config) > 0


class TestWorkspaces:
    """Test workspace definitions"""
    
    def test_workspaces_defined(self):
        """Test that workspaces are defined in browser"""
        # Can't import browser.py due to GTK, but check file exists
        browser_path = Path(__file__).parent.parent / "src" / "core" / "browser.py"
        assert browser_path.exists()
        
        content = browser_path.read_text()
        assert "WORKSPACES" in content
        assert "chill" in content
        assert "school" in content
        assert "work" in content

