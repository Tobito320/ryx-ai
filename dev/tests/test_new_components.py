"""
Tests for the new Ryx AI production-grade components
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifier:
    """Test the new LLM-based intent classifier"""

    def test_import(self):
        """Test import"""
        from core.intent_classifier import IntentClassifier, IntentType
        assert IntentClassifier is not None
        assert IntentType is not None

    def test_classify_file_ops(self):
        """Test file operation detection"""
        from core.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        # Clear file operations
        intent = classifier.classify("open hyprland config")
        assert intent.intent_type == IntentType.FILE_OPS

        intent = classifier.classify("find waybar config")
        assert intent.intent_type == IntentType.FILE_OPS

        intent = classifier.classify("locate my nvim settings")
        assert intent.intent_type == IntentType.FILE_OPS

    def test_classify_chat(self):
        """Test chat detection"""
        from core.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        # Simple greetings
        intent = classifier.classify("hello")
        assert intent.intent_type == IntentType.CHAT

        intent = classifier.classify("hi there")
        assert intent.intent_type == IntentType.CHAT

        # Short conversational
        intent = classifier.classify("how are you")
        assert intent.intent_type == IntentType.CHAT

    def test_classify_code_edit(self):
        """Test code edit detection"""
        from core.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("refactor the intent parser")
        assert intent.intent_type == IntentType.CODE_EDIT

        intent = classifier.classify("debug this function")
        assert intent.intent_type == IntentType.CODE_EDIT

    def test_classify_web_research(self):
        """Test web research detection"""
        from core.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("search for AI coding tools")
        assert intent.intent_type == IntentType.WEB_RESEARCH

        intent = classifier.classify("google python best practices")
        assert intent.intent_type == IntentType.WEB_RESEARCH

    def test_slash_commands(self):
        """Test slash command handling"""
        from core.intent_classifier import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("/help")
        assert intent.intent_type == IntentType.SYSTEM_TASK
        assert intent.target == "show_help"

        intent = classifier.classify("/status")
        assert intent.intent_type == IntentType.SYSTEM_TASK
        assert intent.target == "show_status"

        intent = classifier.classify("/quit")
        assert intent.intent_type == IntentType.SYSTEM_TASK
        assert intent.target == "quit"

    def test_tier_override(self):
        """Test tier override detection"""
        from core.intent_classifier import IntentClassifier

        classifier = IntentClassifier()

        intent = classifier.classify("use fast model")
        assert intent.tier_override == "fast"

        intent = classifier.classify("switch to powerful")
        assert intent.tier_override == "powerful"


class TestModelRouter:
    """Test the model router"""

    def test_import(self):
        """Test import"""
        from core.model_router import ModelRouter, ModelTier
        assert ModelRouter is not None
        assert ModelTier is not None

    def test_get_model(self):
        """Test getting model by tier"""
        from core.model_router import ModelRouter, ModelTier

        router = ModelRouter()
        # Disable auto-fallback for testing
        router.config.auto_fallback = False

        # Get balanced model (default)
        model = router.get_model(ModelTier.BALANCED)
        assert model.name == "qwen2.5-coder:14b"

        # Get fast model
        model = router.get_model(ModelTier.FAST)
        assert model.name == "mistral:7b"

        # Get powerful model
        model = router.get_model(ModelTier.POWERFUL)
        assert model.name == "deepseek-coder-v2:16b"

    def test_tier_by_name(self):
        """Test getting tier by name"""
        from core.model_router import ModelRouter, ModelTier

        router = ModelRouter()

        assert router.get_tier_by_name("fast") == ModelTier.FAST
        assert router.get_tier_by_name("balanced") == ModelTier.BALANCED
        assert router.get_tier_by_name("powerful") == ModelTier.POWERFUL
        assert router.get_tier_by_name("ultra") == ModelTier.ULTRA
        assert router.get_tier_by_name("uncensored") == ModelTier.UNCENSORED

        # Aliases
        assert router.get_tier_by_name("quick") == ModelTier.FAST
        assert router.get_tier_by_name("strong") == ModelTier.POWERFUL

    def test_list_models(self):
        """Test listing models"""
        from core.model_router import ModelRouter

        router = ModelRouter()
        models = router.list_models()

        assert "fast" in models
        assert "balanced" in models
        assert "powerful" in models
        assert "ultra" in models
        assert "uncensored" in models


class TestOllamaClient:
    """Test the Ollama client"""

    def test_import(self):
        """Test import"""
        from core.ollama_client import OllamaClient, GenerateResponse
        assert OllamaClient is not None
        assert GenerateResponse is not None

    def test_initialization(self):
        """Test client initialization"""
        from core.ollama_client import OllamaClient

        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"

        client = OllamaClient(base_url="http://custom:1234")
        assert client.base_url == "http://custom:1234"

    def test_health_check_structure(self):
        """Test health check returns proper structure"""
        from core.ollama_client import OllamaClient

        client = OllamaClient()
        health = client.health_check()

        assert "status" in health
        assert "base_url" in health


class TestToolRegistry:
    """Test the tool registry"""

    def test_import(self):
        """Test import"""
        from core.tool_registry import ToolRegistry, ToolCategory, SafetyLevel
        assert ToolRegistry is not None
        assert ToolCategory is not None
        assert SafetyLevel is not None

    def test_builtin_tools(self):
        """Test builtin tools are registered"""
        from core.tool_registry import ToolRegistry

        tools = ToolRegistry()

        # Filesystem tools
        assert "read_file" in tools.tools
        assert "write_file" in tools.tools
        assert "search_files" in tools.tools

        # Shell tools
        assert "run_command" in tools.tools

        # Web tools
        assert "web_search" in tools.tools
        assert "scrape_page" in tools.tools

        # RAG tools
        assert "save_note" in tools.tools
        assert "search_notes" in tools.tools

    def test_execute_read_file(self):
        """Test reading a file"""
        from core.tool_registry import ToolRegistry
        import tempfile
        import os

        tools = ToolRegistry()

        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            test_path = f.name

        try:
            result = tools.execute_tool("read_file", {"path": test_path})
            assert result.success
            assert result.output == "test content"
        finally:
            os.unlink(test_path)

    def test_save_note_path_traversal(self):
        """Test that save_note prevents path traversal attacks"""
        from core.tool_registry import ToolRegistry

        tools = ToolRegistry()

        # Try to save a note with path traversal in the title
        result = tools.execute_tool("save_note", {
            "title": "../../../etc/passwd",
            "content": "malicious content",
            "tags": []
        })

        # The note should be saved but with sanitized filename
        # or rejected entirely
        if result.success:
            # If saved, verify the path doesn't escape notes directory
            from core.paths import get_data_dir
            notes_dir = str(get_data_dir() / "notes")
            assert notes_dir in result.metadata.get('path', ''), "Path traversal should be prevented"

    def test_dangerous_command_blocking(self):
        """Test that dangerous commands are blocked"""
        from core.tool_registry import ToolRegistry

        tools = ToolRegistry()

        # Test various dangerous commands
        dangerous_commands = [
            "rm -rf /",
            "rm -rf ~",
            "dd if=/dev/zero of=/dev/sda",
            ":(){:|:&};:",
            "> /dev/sda",
        ]

        for cmd in dangerous_commands:
            result = tools.execute_tool("run_command", {"command": cmd})
            assert not result.success, f"Command '{cmd}' should be blocked"
            assert "blocked" in result.error.lower(), f"Command '{cmd}' should show blocked message"

    def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool"""
        from core.tool_registry import ToolRegistry

        tools = ToolRegistry()
        result = tools.execute_tool("nonexistent_tool", {})

        assert not result.success
        assert "Unknown tool" in result.error

    def test_tool_descriptions(self):
        """Test getting tool descriptions for LLM"""
        from core.tool_registry import ToolRegistry

        tools = ToolRegistry()
        descriptions = tools.get_tool_descriptions()

        assert "read_file" in descriptions
        assert "write_file" in descriptions
        assert "web_search" in descriptions


class TestUI:
    """Test the UI module"""

    def test_import(self):
        """Test import"""
        from core.ui import RyxUI, Color, Emoji
        assert RyxUI is not None
        assert Color is not None
        assert Emoji is not None

    def test_ui_initialization(self):
        """Test UI initialization"""
        from core.ui import RyxUI

        ui = RyxUI()
        assert ui.show_emoji == True

        ui = RyxUI(show_emoji=False)
        assert ui.show_emoji == False


class TestSessionLoop:
    """Test the session loop"""

    def test_import(self):
        """Test import"""
        from core.session_loop import SessionLoop
        assert SessionLoop is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
