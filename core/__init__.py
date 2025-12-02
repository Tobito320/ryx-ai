"""
Ryx AI - Core Module

JARVIS-grade personal assistant core components.
"""

# Lazy imports to avoid circular dependencies and speed up startup
__all__ = [
    # AI Engine
    'AIEngine',
    'RyxBrain',
    'RyxEngine',
    
    # Model Management
    'ModelOrchestrator',
    'ModelRouter',
    
    # Intent
    'IntentClassifier',
    'IntentParser',
    
    # Permissions
    'PermissionManager',
    
    # Tools
    'ToolRegistry',
    
    # RAG
    'RAGSystem',
    
    # Learning
    'MetaLearner',
    
    # Health
    'HealthMonitor',
    
    # Paths
    'get_project_root',
    'get_data_dir',
    'get_config_dir',
    
    # Session
    'RyxSession',
    'SessionLoop',
]

def __getattr__(name):
    """Lazy import for faster startup."""
    if name == 'AIEngine':
        from .ai_engine import AIEngine
        return AIEngine
    elif name == 'RyxBrain':
        from .ryx_brain import RyxBrain
        return RyxBrain
    elif name == 'RyxEngine':
        from .ryx_engine import RyxEngine
        return RyxEngine
    elif name == 'ModelOrchestrator':
        from .model_orchestrator import ModelOrchestrator
        return ModelOrchestrator
    elif name == 'ModelRouter':
        from .model_router import ModelRouter
        return ModelRouter
    elif name == 'IntentClassifier':
        from .intent_classifier import IntentClassifier
        return IntentClassifier
    elif name == 'IntentParser':
        from .intent_parser import IntentParser
        return IntentParser
    elif name == 'PermissionManager':
        from .permissions import PermissionManager
        return PermissionManager
    elif name == 'ToolRegistry':
        from .tool_registry import ToolRegistry
        return ToolRegistry
    elif name == 'RAGSystem':
        from .rag_system import RAGSystem
        return RAGSystem
    elif name == 'MetaLearner':
        from .meta_learner import MetaLearner
        return MetaLearner
    elif name == 'HealthMonitor':
        from .health_monitor import HealthMonitor
        return HealthMonitor
    elif name in ('get_project_root', 'get_data_dir', 'get_config_dir'):
        from . import paths
        return getattr(paths, name)
    elif name == 'RyxSession':
        from .ryx_session import RyxSession
        return RyxSession
    elif name == 'SessionLoop':
        from .session_loop import SessionLoop
        return SessionLoop
    raise AttributeError(f"module 'core' has no attribute '{name}'")
