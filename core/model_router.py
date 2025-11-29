"""
Ryx AI - Model Router
Production-grade model routing with tier-based configuration and Ollama/Docker support
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Generator
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers for intelligent routing"""
    FAST = "fast"  # Quick responses, simple tasks
    BALANCED = "balanced"  # Default coding model
    POWERFUL = "powerful"  # Complex coding tasks
    ULTRA = "ultra"  # Heavy reasoning, architecture
    UNCENSORED = "uncensored"  # Personal/uncensored conversations


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str  # Model name in Ollama
    tier: ModelTier
    description: str
    vram_mb: int  # Expected VRAM usage
    typical_latency_ms: int  # Typical response latency
    specialties: List[str]  # What this model is good at
    max_tokens: int = 4096
    timeout_seconds: int = 60


@dataclass
class RouterConfig:
    """Configuration for the model router"""
    ollama_base_url: str = "http://localhost:11434"
    default_tier: ModelTier = ModelTier.BALANCED
    auto_fallback: bool = True
    stream_responses: bool = True
    models: Dict[ModelTier, ModelConfig] = field(default_factory=dict)


class ModelRouter:
    """
    Intelligent model router with tier-based selection

    Features:
    - Tier-based model selection (fast, balanced, powerful, ultra, uncensored)
    - Configurable Ollama base URL (Docker support)
    - Streaming support
    - Auto-fallback on model unavailability
    - User tier overrides
    """

    # Default model configurations
    DEFAULT_MODELS = {
        ModelTier.FAST: ModelConfig(
            name="mistral:7b",
            tier=ModelTier.FAST,
            description="Fast general model for quick tasks",
            vram_mb=4500,
            typical_latency_ms=200,
            specialties=["quick_tasks", "simple_queries", "chat"],
            max_tokens=2048,
            timeout_seconds=30
        ),
        ModelTier.BALANCED: ModelConfig(
            name="qwen2.5-coder:14b",
            tier=ModelTier.BALANCED,
            description="Main coding model (default)",
            vram_mb=9000,
            typical_latency_ms=500,
            specialties=["coding", "scripts", "configs", "debugging"],
            max_tokens=4096,
            timeout_seconds=60
        ),
        ModelTier.POWERFUL: ModelConfig(
            name="deepseek-coder-v2:16b",
            tier=ModelTier.POWERFUL,
            description="Strong coder alternative",
            vram_mb=10000,
            typical_latency_ms=1000,
            specialties=["complex_code", "refactoring", "analysis"],
            max_tokens=8192,
            timeout_seconds=90
        ),
        ModelTier.ULTRA: ModelConfig(
            name="SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL",
            tier=ModelTier.ULTRA,
            description="Heavy reasoning, architecture",
            vram_mb=16000,
            typical_latency_ms=3000,
            specialties=["architecture", "complex_reasoning", "large_refactors"],
            max_tokens=16384,
            timeout_seconds=180
        ),
        ModelTier.UNCENSORED: ModelConfig(
            name="huihui_ai/gpt-oss-abliterated:20b",
            tier=ModelTier.UNCENSORED,
            description="Uncensored personal reflection",
            vram_mb=12000,
            typical_latency_ms=1500,
            specialties=["personal_chat", "uncensored", "creative"],
            max_tokens=8192,
            timeout_seconds=120
        ),
    }

    # Fallback chain when primary model unavailable
    FALLBACK_CHAIN = {
        ModelTier.ULTRA: [ModelTier.POWERFUL, ModelTier.BALANCED, ModelTier.FAST],
        ModelTier.POWERFUL: [ModelTier.BALANCED, ModelTier.FAST],
        ModelTier.BALANCED: [ModelTier.FAST],
        ModelTier.FAST: [],
        ModelTier.UNCENSORED: [ModelTier.POWERFUL, ModelTier.BALANCED],
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize model router

        Args:
            config_path: Optional path to configuration file
        """
        self.config = self._load_config(config_path)
        self._available_models: Optional[List[str]] = None

    def _load_config(self, config_path: Optional[Path] = None) -> RouterConfig:
        """Load router configuration"""
        # Check environment variable for Ollama URL
        ollama_url = os.environ.get(
            'OLLAMA_BASE_URL',
            os.environ.get('RYX_OLLAMA_URL', 'http://localhost:11434')
        )

        config = RouterConfig(
            ollama_base_url=ollama_url,
            models=self.DEFAULT_MODELS.copy()
        )

        # Load from config file if provided
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)

                # Update Ollama URL
                if 'ollama_base_url' in file_config:
                    config.ollama_base_url = file_config['ollama_base_url']

                # Update default tier
                if 'default_tier' in file_config:
                    config.default_tier = ModelTier(file_config['default_tier'])

                # Update models
                if 'models' in file_config:
                    for tier_name, model_config in file_config['models'].items():
                        tier = ModelTier(tier_name)
                        config.models[tier] = ModelConfig(
                            name=model_config['name'],
                            tier=tier,
                            description=model_config.get('description', ''),
                            vram_mb=model_config.get('vram_mb', 4000),
                            typical_latency_ms=model_config.get('typical_latency_ms', 500),
                            specialties=model_config.get('specialties', []),
                            max_tokens=model_config.get('max_tokens', 4096),
                            timeout_seconds=model_config.get('timeout_seconds', 60)
                        )

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        return config

    def get_model(self, tier: Optional[ModelTier] = None, intent_type: Optional[str] = None) -> ModelConfig:
        """
        Get model configuration for a tier

        Args:
            tier: Model tier (or None for default)
            intent_type: Intent type for automatic tier selection

        Returns:
            ModelConfig for the appropriate model
        """
        if tier is None:
            tier = self._select_tier_for_intent(intent_type)

        # Check if model is available, with fallback
        model = self.config.models.get(tier, self.config.models[ModelTier.BALANCED])

        if self.config.auto_fallback and not self._is_model_available(model.name):
            model = self._get_fallback_model(tier)

        return model

    def _select_tier_for_intent(self, intent_type: Optional[str]) -> ModelTier:
        """Select tier based on intent type"""
        if intent_type is None:
            return self.config.default_tier

        intent_tier_map = {
            'chat': ModelTier.FAST,
            'code_edit': ModelTier.BALANCED,
            'config_edit': ModelTier.BALANCED,
            'file_ops': ModelTier.FAST,
            'web_research': ModelTier.BALANCED,
            'system_task': ModelTier.FAST,
            'knowledge_rag': ModelTier.FAST,
            'personal_chat': ModelTier.UNCENSORED,
        }

        return intent_tier_map.get(intent_type, self.config.default_tier)

    def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        if self._available_models is None:
            self._refresh_available_models()

        return model_name in (self._available_models or [])

    def _refresh_available_models(self):
        """Refresh list of available models from Ollama"""
        import requests

        try:
            response = requests.get(
                f"{self.config.ollama_base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self._available_models = [m['name'] for m in data.get('models', [])]
            else:
                self._available_models = []
        except Exception as e:
            logger.warning(f"Failed to refresh available models: {e}")
            self._available_models = []

    def _get_fallback_model(self, original_tier: ModelTier) -> ModelConfig:
        """Get fallback model when original is unavailable"""
        fallback_tiers = self.FALLBACK_CHAIN.get(original_tier, [])

        for fallback_tier in fallback_tiers:
            model = self.config.models.get(fallback_tier)
            if model and self._is_model_available(model.name):
                logger.info(f"Using fallback model {model.name} for tier {original_tier}")
                return model

        # Last resort: return first available model
        for tier, model in self.config.models.items():
            if self._is_model_available(model.name):
                return model

        # Return default even if unavailable
        return self.config.models[self.config.default_tier]

    def get_ollama_url(self) -> str:
        """Get Ollama base URL"""
        return self.config.ollama_base_url

    def list_models(self) -> Dict[str, ModelConfig]:
        """List all configured models with availability"""
        self._refresh_available_models()

        result = {}
        for tier, model in self.config.models.items():
            result[tier.value] = {
                'config': model,
                'available': self._is_model_available(model.name)
            }

        return result

    def get_tier_by_name(self, name: str) -> Optional[ModelTier]:
        """Get tier by name string"""
        name_lower = name.lower()

        # Direct tier name match
        for tier in ModelTier:
            if tier.value == name_lower:
                return tier

        # Alias matching
        aliases = {
            'quick': ModelTier.FAST,
            'small': ModelTier.FAST,
            'default': ModelTier.BALANCED,
            'strong': ModelTier.POWERFUL,
            'big': ModelTier.POWERFUL,
            'heavy': ModelTier.ULTRA,
            '30b': ModelTier.ULTRA,
            'qwen3': ModelTier.ULTRA,
            'abliterated': ModelTier.UNCENSORED,
            'gpt-oss': ModelTier.UNCENSORED,
            'personal': ModelTier.UNCENSORED,
        }

        return aliases.get(name_lower)

    def save_config(self, config_path: Path):
        """Save current configuration to file"""
        config_data = {
            'ollama_base_url': self.config.ollama_base_url,
            'default_tier': self.config.default_tier.value,
            'auto_fallback': self.config.auto_fallback,
            'stream_responses': self.config.stream_responses,
            'models': {}
        }

        for tier, model in self.config.models.items():
            config_data['models'][tier.value] = {
                'name': model.name,
                'description': model.description,
                'vram_mb': model.vram_mb,
                'typical_latency_ms': model.typical_latency_ms,
                'specialties': model.specialties,
                'max_tokens': model.max_tokens,
                'timeout_seconds': model.timeout_seconds
            }

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
