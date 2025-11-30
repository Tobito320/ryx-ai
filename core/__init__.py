"""
Ryx AI - Core Module

JARVIS-grade personal assistant core components.
"""

from .ai_engine_v2 import AIEngineV2, LatencyMetrics, QueryOptions, ResponseFormatter
from .model_orchestrator import ModelOrchestrator, QueryResult
from .model_router import ModelRouter, ModelTier, ModelConfig
from .intent_classifier import IntentClassifier, IntentType, ClassifiedIntent
from .permissions import PermissionManager, CommandExecutor, PermissionLevel
from .tool_registry import ToolRegistry, get_tool_registry
from .rag_system import RAGSystem, FileFinder
from .meta_learner import MetaLearner
from .health_monitor import HealthMonitor, HealthStatus
from .paths import get_project_root, get_data_dir, get_config_dir
from .performance_profiler import get_profiler, profile, Timer

__all__ = [
    # AI Engine
    'AIEngineV2',
    'LatencyMetrics',
    'QueryOptions',
    'ResponseFormatter',
    
    # Model Management
    'ModelOrchestrator',
    'QueryResult',
    'ModelRouter',
    'ModelTier',
    'ModelConfig',
    
    # Intent Classification
    'IntentClassifier',
    'IntentType',
    'ClassifiedIntent',
    
    # Permissions
    'PermissionManager',
    'CommandExecutor',
    'PermissionLevel',
    
    # Tools
    'ToolRegistry',
    'get_tool_registry',
    
    # RAG
    'RAGSystem',
    'FileFinder',
    
    # Learning
    'MetaLearner',
    
    # Health
    'HealthMonitor',
    'HealthStatus',
    
    # Paths
    'get_project_root',
    'get_data_dir',
    'get_config_dir',
    
    # Profiling
    'get_profiler',
    'profile',
    'Timer',
]
