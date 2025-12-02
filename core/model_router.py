"""
Ryx AI - Model Router

Intelligent model selection based on task type.
Each model has a specific purpose - no guessing.

FIXED MODELS (do not change without reason):
- qwen2.5:1.5b      → FAST: Intent detection, quick responses
- gemma2:2b         → CHAT: Simple conversations, German
- qwen2.5-coder:14b → CODE: Writing/modifying code  
- deepseek-r1:14b   → REASON: Complex logic, verification
- nomic-embed-text  → EMBED: Semantic search, RAG
- gpt-oss:20b       → FALLBACK: When others fail
- llama2-uncensored → UNCENSORED: No restrictions
"""

import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelRole(Enum):
    """What role does the model play in Ryx?"""
    FAST = "fast"           # Intent detection, quick tasks
    CHAT = "chat"           # Simple conversations
    CODE = "code"           # Code generation/editing
    REASON = "reason"       # Complex reasoning, verification
    EMBED = "embed"         # Vector embeddings
    FALLBACK = "fallback"   # When primary fails
    UNCENSORED = "uncensored"  # No restrictions


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str
    role: ModelRole
    vram_mb: int
    max_tokens: int
    timeout_seconds: int
    description: str
    
    def __str__(self):
        return f"{self.name} ({self.role.value})"


# ═══════════════════════════════════════════════════════════════
# FIXED MODEL CONFIGURATION - These are THE models Ryx uses
# ═══════════════════════════════════════════════════════════════

MODELS: Dict[ModelRole, ModelConfig] = {
    ModelRole.FAST: ModelConfig(
        name="qwen2.5:1.5b",
        role=ModelRole.FAST,
        vram_mb=1500,
        max_tokens=1024,
        timeout_seconds=10,
        description="Blitzschnell für Intent-Erkennung und einfache Aufgaben"
    ),
    
    ModelRole.CHAT: ModelConfig(
        name="gemma2:2b",
        role=ModelRole.CHAT,
        vram_mb=2000,
        max_tokens=2048,
        timeout_seconds=15,
        description="Schneller Chat, gutes Deutsch, einfache Fragen"
    ),
    
    ModelRole.CODE: ModelConfig(
        name="qwen2.5-coder:14b",
        role=ModelRole.CODE,
        vram_mb=10000,
        max_tokens=8192,
        timeout_seconds=90,
        description="Code schreiben, PLAN/APPLY Phasen, 88% HumanEval"
    ),
    
    ModelRole.REASON: ModelConfig(
        name="deepseek-r1:14b",
        role=ModelRole.REASON,
        vram_mb=10000,
        max_tokens=8192,
        timeout_seconds=120,
        description="Chain-of-Thought Reasoning, VERIFY Phase, komplexe Logik"
    ),
    
    ModelRole.EMBED: ModelConfig(
        name="nomic-embed-text:latest",
        role=ModelRole.EMBED,
        vram_mb=500,
        max_tokens=8192,
        timeout_seconds=30,
        description="Vektor-Embeddings für semantische Suche"
    ),
    
    ModelRole.FALLBACK: ModelConfig(
        name="gpt-oss:20b",
        role=ModelRole.FALLBACK,
        vram_mb=13000,
        max_tokens=8192,
        timeout_seconds=120,
        description="Backup wenn andere Modelle versagen"
    ),
    
    ModelRole.UNCENSORED: ModelConfig(
        name="llama2-uncensored:7b",
        role=ModelRole.UNCENSORED,
        vram_mb=4500,
        max_tokens=4096,
        timeout_seconds=60,
        description="Keine Einschränkungen, unzensiert"
    ),
}


# ═══════════════════════════════════════════════════════════════
# TASK → MODEL ROUTING (fixed mapping)
# ═══════════════════════════════════════════════════════════════

TASK_ROUTING: Dict[str, ModelRole] = {
    # Intent Detection & Quick Tasks
    "intent_detection": ModelRole.FAST,
    "typo_correction": ModelRole.FAST,
    "json_parsing": ModelRole.FAST,
    "quick_answer": ModelRole.FAST,
    "file_search": ModelRole.FAST,
    "app_launch": ModelRole.FAST,
    
    # Simple Chat
    "simple_chat": ModelRole.CHAT,
    "small_talk": ModelRole.CHAT,
    "definition": ModelRole.CHAT,
    "translation": ModelRole.CHAT,
    "greeting": ModelRole.CHAT,
    
    # Code Tasks (EXPLORE/PLAN/APPLY phases)
    "code_explore": ModelRole.CODE,
    "code_plan": ModelRole.CODE,
    "code_apply": ModelRole.CODE,
    "code_generation": ModelRole.CODE,
    "refactoring": ModelRole.CODE,
    "debugging": ModelRole.CODE,
    "script_writing": ModelRole.CODE,
    "config_edit": ModelRole.CODE,
    
    # Complex Reasoning (VERIFY phase)
    "code_verify": ModelRole.REASON,
    "complex_analysis": ModelRole.REASON,
    "architecture_review": ModelRole.REASON,
    "problem_solving": ModelRole.REASON,
    "step_by_step": ModelRole.REASON,
    "verification": ModelRole.REASON,
    
    # Embeddings
    "semantic_search": ModelRole.EMBED,
    "file_relevance": ModelRole.EMBED,
    "rag_embedding": ModelRole.EMBED,
    "codebase_search": ModelRole.EMBED,
    
    # Uncensored
    "uncensored_chat": ModelRole.UNCENSORED,
    "personal_reflection": ModelRole.UNCENSORED,
    "no_filter": ModelRole.UNCENSORED,
}


# ═══════════════════════════════════════════════════════════════
# PHASE → MODEL MAPPING (for the agent system)
# ═══════════════════════════════════════════════════════════════

PHASE_MODELS: Dict[str, ModelRole] = {
    "explore": ModelRole.CODE,      # Understanding code needs coding model
    "plan": ModelRole.CODE,         # Planning needs coding knowledge
    "apply": ModelRole.CODE,        # Writing code
    "verify": ModelRole.REASON,     # Verification needs reasoning
}


# ═══════════════════════════════════════════════════════════════
# FALLBACK CHAINS
# ═══════════════════════════════════════════════════════════════

FALLBACK_CHAIN: Dict[ModelRole, List[ModelRole]] = {
    ModelRole.FAST: [ModelRole.CHAT, ModelRole.FALLBACK],
    ModelRole.CHAT: [ModelRole.FAST, ModelRole.FALLBACK],
    ModelRole.CODE: [ModelRole.REASON, ModelRole.FALLBACK],
    ModelRole.REASON: [ModelRole.CODE, ModelRole.FALLBACK],
    ModelRole.EMBED: [],  # No fallback for embeddings
    ModelRole.FALLBACK: [ModelRole.CODE, ModelRole.UNCENSORED],
    ModelRole.UNCENSORED: [ModelRole.FALLBACK],
}


class ModelRouter:
    """
    Routes tasks to the appropriate model.
    No guessing - each task type has a fixed model.
    """
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = os.environ.get('OLLAMA_BASE_URL', ollama_base_url)
        self._available_models: Optional[List[str]] = None
    
    # ─────────────────────────────────────────────────────────────
    # Core API
    # ─────────────────────────────────────────────────────────────
    
    def get_model(self, task: str) -> ModelConfig:
        """Get the model for a specific task"""
        role = TASK_ROUTING.get(task, ModelRole.CHAT)
        return MODELS[role]
    
    def get_model_by_role(self, role: ModelRole) -> ModelConfig:
        """Get model by role directly"""
        return MODELS[role]
    
    def get_model_name(self, task: str) -> str:
        """Get just the model name for a task"""
        return self.get_model(task).name
    
    def get_phase_model(self, phase: str) -> ModelConfig:
        """Get the model for an agent phase"""
        role = PHASE_MODELS.get(phase.lower(), ModelRole.CODE)
        return MODELS[role]
    
    def select_for_query(self, query: str) -> ModelConfig:
        """
        Smart model selection based on query analysis.
        Quick heuristics - no LLM call needed.
        """
        q = query.lower()
        qlen = len(query)
        
        # Very short → FAST
        if qlen < 20:
            return MODELS[ModelRole.FAST]
        
        # Greetings → CHAT
        greetings = ['hi', 'hello', 'hallo', 'hey', 'moin', 'servus']
        if any(q.startswith(g) for g in greetings):
            return MODELS[ModelRole.CHAT]
        
        # Code indicators → CODE
        code_words = ['code', 'function', 'class', 'def ', 'import', 'error', 
                      'bug', 'fix', 'refactor', 'implement', 'create a', 'add a',
                      'funktion', 'fehler', 'erstelle', 'füge hinzu']
        if any(w in q for w in code_words):
            # Complex code → REASON for planning
            if qlen > 200 or 'refactor' in q or 'architect' in q or 'design' in q:
                return MODELS[ModelRole.REASON]
            return MODELS[ModelRole.CODE]
        
        # Reasoning indicators → REASON
        reason_words = ['why', 'warum', 'explain step', 'analyze', 'analysiere',
                        'think through', 'verify', 'check if', 'prüfe']
        if any(w in q for w in reason_words):
            return MODELS[ModelRole.REASON]
        
        # Uncensored indicators
        uncensored_words = ['uncensored', 'unzensiert', 'no filter', 'honest opinion']
        if any(w in q for w in uncensored_words):
            return MODELS[ModelRole.UNCENSORED]
        
        # Medium length general query → CHAT
        if qlen < 100:
            return MODELS[ModelRole.CHAT]
        
        # Default for longer queries → CODE (can handle most things)
        return MODELS[ModelRole.CODE]
    
    # ─────────────────────────────────────────────────────────────
    # Availability & Fallback
    # ─────────────────────────────────────────────────────────────
    
    @property
    def available_models(self) -> List[str]:
        """Get list of models installed in Ollama"""
        if self._available_models is None:
            self._available_models = self._fetch_available_models()
        return self._available_models
    
    def _fetch_available_models(self) -> List[str]:
        """Fetch available models from Ollama"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                return [line.split()[0] for line in lines if line]
        except Exception as e:
            logger.warning(f"Failed to fetch models: {e}")
        return []
    
    def refresh_available(self) -> List[str]:
        """Refresh the list of available models"""
        self._available_models = None
        return self.available_models
    
    def get_ollama_url(self) -> str:
        """Get Ollama base URL"""
        return self.ollama_base_url
    
    def is_available(self, role: ModelRole) -> bool:
        """Check if the model for a role is available"""
        model = MODELS[role]
        return model.name in self.available_models
    
    def get_fallback(self, role: ModelRole) -> Optional[ModelConfig]:
        """Get fallback model if primary isn't available"""
        for fallback_role in FALLBACK_CHAIN.get(role, []):
            if self.is_available(fallback_role):
                return MODELS[fallback_role]
        return None
    
    def get_best_available(self, task: str) -> ModelConfig:
        """Get best available model for a task (with fallback)"""
        primary = self.get_model(task)
        
        if primary.name in self.available_models:
            return primary
        
        # Try fallback
        role = TASK_ROUTING.get(task, ModelRole.CHAT)
        fallback = self.get_fallback(role)
        if fallback:
            logger.info(f"Using fallback {fallback.name} for task {task}")
            return fallback
        
        # Last resort: any available model
        for model in MODELS.values():
            if model.name in self.available_models:
                return model
        
        # Nothing available - return primary anyway (will fail gracefully)
        return primary
    
    # ─────────────────────────────────────────────────────────────
    # Status & Info
    # ─────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Dict]:
        """Get status of all models"""
        available = self.available_models
        status = {}
        
        for role, model in MODELS.items():
            status[role.value] = {
                "model": model.name,
                "available": model.name in available,
                "vram_mb": model.vram_mb,
                "description": model.description
            }
        
        return status
    
    def print_status(self):
        """Print status to console"""
        status = self.get_status()
        print("\n=== Ryx Model Status ===\n")
        
        for role, info in status.items():
            icon = "✓" if info["available"] else "✗"
            print(f"  {icon} {role.upper():12} → {info['model']}")
        
        print()
    
    def list_models(self) -> Dict[str, Any]:
        """List all configured models with availability"""
        self.refresh_available()
        
        result = {}
        for role, model in MODELS.items():
            result[role.value] = {
                'config': model,
                'available': model.name in self.available_models
            }
        
        return result


# ═══════════════════════════════════════════════════════════════
# Singleton & Helper Functions
# ═══════════════════════════════════════════════════════════════

_router: Optional[ModelRouter] = None

def get_router() -> ModelRouter:
    """Get or create the model router singleton"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def get_model_for_task(task: str) -> ModelConfig:
    """Convenience function to get model for a task"""
    return get_router().get_model(task)


def get_model_for_phase(phase: str) -> ModelConfig:
    """Convenience function to get model for a phase"""
    return get_router().get_phase_model(phase)


def select_model(query: str) -> ModelConfig:
    """Convenience function for smart model selection"""
    return get_router().select_for_query(query)
