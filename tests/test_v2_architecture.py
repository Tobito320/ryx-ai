"""
Tests for Ryx V2 New Architecture Components
"""

import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifier:
    """Test the new LLM-based intent classifier"""
    
    def test_import(self):
        """Test import of intent classifier"""
        from core.intent_classifier import IntentClassifier, IntentType, ClassifiedIntent
        assert IntentClassifier is not None
        assert IntentType is not None
    
    def test_greeting_detection(self):
        """Test greeting detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        greetings = ['hello', 'hi', 'hey', 'howdy', 'sup']
        for greeting in greetings:
            result = classifier.classify(greeting)
            assert result.intent_type == IntentType.CHAT
            assert result.flags.get('is_greeting', False)
    
    def test_code_edit_intent(self):
        """Test CODE_EDIT intent detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        code_prompts = [
            'refactor the parser module',
            'implement a new feature',
            'fix bug in the handler',
        ]
        
        for prompt in code_prompts:
            result = classifier.classify(prompt)
            assert result.intent_type == IntentType.CODE_EDIT, f"Failed for: {prompt}"
    
    def test_config_edit_intent(self):
        """Test CONFIG_EDIT intent detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        config_prompts = [
            'edit my hyprland config',
            'update waybar settings',
            'change kitty configuration',
        ]
        
        for prompt in config_prompts:
            result = classifier.classify(prompt)
            assert result.intent_type == IntentType.CONFIG_EDIT, f"Failed for: {prompt}"
    
    def test_file_ops_intent(self):
        """Test FILE_OPS intent detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        file_prompts = [
            'find file config.py',
            'open my bashrc',
            'create file test.txt',
        ]
        
        for prompt in file_prompts:
            result = classifier.classify(prompt)
            assert result.intent_type == IntentType.FILE_OPS, f"Failed for: {prompt}"
    
    def test_web_research_intent(self):
        """Test WEB_RESEARCH intent detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        web_prompts = [
            'search web for python tips',
            'look up vim plugins',
            'google best arch linux themes',
        ]
        
        for prompt in web_prompts:
            result = classifier.classify(prompt)
            assert result.intent_type == IntentType.WEB_RESEARCH, f"Failed for: {prompt}"
            assert result.needs_web == True
    
    def test_system_task_intent(self):
        """Test SYSTEM_TASK intent detection"""
        from core.intent_classifier import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        system_prompts = [
            'run tests',
            'build the project',
            'diagnose network issues',
        ]
        
        for prompt in system_prompts:
            result = classifier.classify(prompt)
            assert result.intent_type == IntentType.SYSTEM_TASK, f"Failed for: {prompt}"
    
    def test_tier_override_detection(self):
        """Test tier override detection"""
        from core.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        
        tier_prompts = {
            'use fast model': 'fast',
            'tier powerful': 'powerful',
            'uncensored model please': 'uncensored',
        }
        
        for prompt, expected_tier in tier_prompts.items():
            result = classifier.classify(prompt)
            assert result.tier_override == expected_tier, f"Failed for: {prompt}"


class TestModelRouter:
    """Test the new model router"""
    
    def test_import(self):
        """Test import of model router"""
        from core.model_router_v2 import ModelRouter, ModelTier, ModelResponse
        assert ModelRouter is not None
    
    def test_initialization(self):
        """Test router initialization"""
        from core.model_router_v2 import ModelRouter
        
        router = ModelRouter()
        assert router.current_tier == 'balanced'  # Default tier
        assert len(router.tiers) > 0
    
    def test_tier_selection(self):
        """Test tier selection"""
        from core.model_router_v2 import ModelRouter
        
        router = ModelRouter()
        
        # Test setting tier
        assert router.set_tier('fast') == True
        assert router.current_tier == 'fast'
        
        # Test invalid tier
        assert router.set_tier('nonexistent') == False
    
    def test_intent_to_tier_mapping(self):
        """Test intent to tier mapping"""
        from core.model_router_v2 import ModelRouter
        
        router = ModelRouter()
        
        # CHAT should map to fast
        tier = router.get_tier_for_intent('CHAT')
        assert tier in ['fast', 'balanced']  # Depends on config
        
        # CODE_EDIT should map to balanced
        tier = router.get_tier_for_intent('CODE_EDIT')
        assert tier in ['balanced', 'powerful']
    
    def test_status(self):
        """Test status reporting"""
        from core.model_router_v2 import ModelRouter
        
        router = ModelRouter()
        status = router.get_status()
        
        assert 'current_tier' in status
        assert 'tiers' in status
        assert 'available_models' in status


class TestToolRegistry:
    """Test the tool registry"""
    
    def test_import(self):
        """Test import of tool registry"""
        from core.tool_registry import ToolRegistry, get_tool_registry
        assert ToolRegistry is not None
        assert get_tool_registry is not None
    
    def test_default_tools(self):
        """Test default tools are registered"""
        from core.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        expected_tools = [
            'file_search', 'file_read', 'file_write', 'file_patch',
            'list_directory', 'shell_command', 'web_fetch', 'web_search'
        ]
        
        for tool in expected_tools:
            assert tool in tools, f"Missing tool: {tool}"
    
    def test_tool_execution(self):
        """Test tool execution"""
        from core.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        
        # Test list_directory tool
        result = registry.execute_tool('list_directory', {'path': '.'})
        assert result.success == True
        assert 'files' in result.output or 'directories' in result.output
    
    def test_file_search_tool(self):
        """Test file search tool"""
        from core.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        
        # Search for Python files in current directory
        result = registry.execute_tool('file_search', {'pattern': '*.py', 'path': '.', 'max_depth': 2})
        assert result.success == True
        assert isinstance(result.output, list)
    
    def test_shell_command_safety(self):
        """Test shell command safety"""
        from core.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        
        # Blocked command should fail
        result = registry.execute_tool('shell_command', {'command': 'rm -rf /'})
        assert result.success == False
        assert 'blocked' in result.error.lower()
        
        # Safe command should work
        result = registry.execute_tool('shell_command', {'command': 'echo hello'})
        assert result.success == True
        assert 'hello' in result.output
    
    def test_tool_descriptions(self):
        """Test tool descriptions for LLM"""
        from core.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        descriptions = registry.get_tool_descriptions()
        
        assert len(descriptions) > 0
        for desc in descriptions:
            assert 'name' in desc
            assert 'description' in desc
            assert 'parameters' in desc


class TestUI:
    """Test the UI module"""
    
    def test_import(self):
        """Test import of UI module"""
        from core.ui import RyxUI, get_ui, Colors, Icons
        assert RyxUI is not None
        assert get_ui is not None
    
    def test_colors(self):
        """Test color constants"""
        from core.ui import Colors
        
        assert Colors.PURPLE is not None
        assert Colors.RESET is not None
        assert '\033[' in Colors.PURPLE  # ANSI escape code
    
    def test_icons(self):
        """Test icon constants"""
        from core.ui import Icons
        
        assert Icons.SUCCESS is not None
        assert Icons.ERROR is not None
        assert Icons.DONE is not None
    
    def test_format_response(self):
        """Test response formatting"""
        from core.ui import get_ui
        
        ui = get_ui()
        
        # Test code block formatting
        response = "Here is code:\n```bash\necho hello\n```"
        formatted = ui.format_response(response)
        assert '```' in formatted  # Should preserve structure
    
    def test_singleton(self):
        """Test UI singleton pattern"""
        from core.ui import get_ui
        
        ui1 = get_ui()
        ui2 = get_ui()
        
        assert ui1 is ui2


class TestSessionLoop:
    """Test the session loop"""
    
    def test_import(self):
        """Test import of session loop"""
        from core.session_loop import SessionLoop
        assert SessionLoop is not None
    
    def test_initialization(self):
        """Test session initialization"""
        from core.session_loop import SessionLoop
        
        # Just test that it initializes without error
        # (Can't fully test without terminal)
        session = SessionLoop()
        assert session.running == True
        assert session.current_tier == 'balanced'


class TestWorkflowOrchestrator:
    """Test the workflow orchestrator"""
    
    def test_import(self):
        """Test import of workflow orchestrator"""
        from core.workflow_orchestrator import WorkflowOrchestrator, Workflow, WorkflowStep
        assert WorkflowOrchestrator is not None
    
    def test_initialization(self):
        """Test orchestrator initialization"""
        from core.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        assert orchestrator.router is not None
        assert orchestrator.tools is not None
        assert orchestrator.classifier is not None
    
    def test_status(self):
        """Test status reporting"""
        from core.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        status = orchestrator.get_current_status()
        
        assert 'router_status' in status
        assert 'tools_available' in status


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
