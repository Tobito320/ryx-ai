"""
RYX Core - Intelligent Model Router

Provides intelligent model selection based on:
- Task complexity
- Required capabilities
- Available resources
- Performance history
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import logging

from .interfaces import BaseModel, ModelCapability, ModelResponse

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers for routing"""
    FAST = "fast"          # Quick tasks, simple queries
    BALANCED = "balanced"  # Default for most tasks
    POWERFUL = "powerful"  # Complex reasoning
    ULTRA = "ultra"        # Heavy computation
    SPECIALIZED = "specialized"  # Domain-specific


@dataclass
class RouteDecision:
    """Decision made by the router"""
    selected_model: str
    tier: ModelTier
    reason: str
    confidence: float  # 0.0 - 1.0
    fallback_models: List[str] = field(default_factory=list)
    estimated_latency_ms: int = 0
    estimated_tokens: int = 0


@dataclass
class ModelProfile:
    """Profile of a model for routing decisions"""
    name: str
    tier: ModelTier
    capabilities: List[ModelCapability]
    avg_latency_ms: float = 500.0
    success_rate: float = 1.0
    vram_mb: int = 4000
    max_tokens: int = 4096
    specialties: List[str] = field(default_factory=list)
    is_available: bool = True


@dataclass
class TaskAnalysis:
    """Analysis of a task for routing"""
    complexity: float  # 0.0 (simple) - 1.0 (complex)
    required_capabilities: List[ModelCapability]
    estimated_tokens: int
    requires_reasoning: bool = False
    requires_code: bool = False
    is_conversational: bool = False


class IntelligentRouter:
    """
    Intelligent model router with capability-based selection
    
    Features:
    - Task complexity analysis
    - Capability matching
    - Performance-based selection
    - Automatic fallback
    - Learning from outcomes
    """
    
    # Default model profiles
    DEFAULT_PROFILES = {
        "fast": ModelProfile(
            name="mistral:7b",
            tier=ModelTier.FAST,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.FAST_INFERENCE,
            ],
            avg_latency_ms=200,
            vram_mb=4500,
            max_tokens=2048,
            specialties=["chat", "quick_tasks"],
        ),
        "balanced": ModelProfile(
            name="qwen2.5-coder:14b",
            tier=ModelTier.BALANCED,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.CODE_ANALYSIS,
            ],
            avg_latency_ms=500,
            vram_mb=9000,
            max_tokens=4096,
            specialties=["coding", "scripts", "debugging"],
        ),
        "powerful": ModelProfile(
            name="deepseek-coder-v2:16b",
            tier=ModelTier.POWERFUL,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.CODE_ANALYSIS,
                ModelCapability.REASONING,
            ],
            avg_latency_ms=1000,
            vram_mb=10000,
            max_tokens=8192,
            specialties=["complex_code", "refactoring"],
        ),
        "ultra": ModelProfile(
            name="qwen3-coder:30b",
            tier=ModelTier.ULTRA,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.CODE_ANALYSIS,
                ModelCapability.REASONING,
                ModelCapability.PLANNING,
                ModelCapability.LONG_CONTEXT,
            ],
            avg_latency_ms=3000,
            vram_mb=16000,
            max_tokens=16384,
            specialties=["architecture", "complex_reasoning"],
        ),
    }
    
    # Fallback chains
    FALLBACK_CHAINS = {
        ModelTier.ULTRA: [ModelTier.POWERFUL, ModelTier.BALANCED, ModelTier.FAST],
        ModelTier.POWERFUL: [ModelTier.BALANCED, ModelTier.FAST],
        ModelTier.BALANCED: [ModelTier.FAST],
        ModelTier.FAST: [],
    }
    
    def __init__(
        self,
        profiles: Optional[Dict[str, ModelProfile]] = None,
        default_tier: ModelTier = ModelTier.BALANCED,
    ):
        """
        Initialize the router
        
        Args:
            profiles: Custom model profiles (uses defaults if not provided)
            default_tier: Default tier when task analysis is inconclusive
        """
        self.profiles = profiles or self.DEFAULT_PROFILES.copy()
        self.default_tier = default_tier
        self._performance_history: List[Dict[str, Any]] = []
    
    def analyze_task(self, prompt: str, context: Optional[str] = None) -> TaskAnalysis:
        """
        Analyze a task to determine routing requirements
        
        Args:
            prompt: User prompt
            context: Optional context (previous messages, etc.)
            
        Returns:
            TaskAnalysis with complexity and requirements
        """
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())
        
        # Analyze complexity
        complexity = 0.0
        required_caps = [ModelCapability.TEXT_GENERATION]
        
        # Check for code-related tasks
        code_keywords = [
            "code", "function", "class", "refactor", "debug", "implement",
            "script", "fix bug", "optimize", "test", "unit test",
        ]
        requires_code = any(kw in prompt_lower for kw in code_keywords)
        if requires_code:
            complexity += 0.3
            required_caps.append(ModelCapability.CODE_GENERATION)
        
        # Check for reasoning tasks
        reasoning_keywords = [
            "explain", "why", "analyze", "compare", "design", "architect",
            "plan", "strategy", "evaluate", "assess",
        ]
        requires_reasoning = any(kw in prompt_lower for kw in reasoning_keywords)
        if requires_reasoning:
            complexity += 0.2
            required_caps.append(ModelCapability.REASONING)
        
        # Check for planning tasks
        planning_keywords = ["plan", "steps", "roadmap", "workflow", "strategy"]
        if any(kw in prompt_lower for kw in planning_keywords):
            complexity += 0.2
            required_caps.append(ModelCapability.PLANNING)
        
        # Adjust for prompt length
        if word_count > 200:
            complexity += 0.1
            required_caps.append(ModelCapability.LONG_CONTEXT)
        
        # Check for simple conversational prompts
        conversational_patterns = [
            "hello", "hi", "hey", "thanks", "thank you",
            "how are you", "what is", "who is",
        ]
        is_conversational = any(p in prompt_lower for p in conversational_patterns)
        if is_conversational:
            complexity = max(0.0, complexity - 0.3)
        
        # Estimate tokens (rough approximation)
        estimated_tokens = word_count * 2  # Input
        if requires_code:
            estimated_tokens += 500  # Expected code output
        elif requires_reasoning:
            estimated_tokens += 300  # Expected reasoning output
        else:
            estimated_tokens += 100  # Simple response
        
        return TaskAnalysis(
            complexity=min(1.0, complexity),
            required_capabilities=list(set(required_caps)),
            estimated_tokens=estimated_tokens,
            requires_reasoning=requires_reasoning,
            requires_code=requires_code,
            is_conversational=is_conversational,
        )
    
    def route(
        self,
        prompt: str,
        context: Optional[str] = None,
        tier_override: Optional[ModelTier] = None,
        required_capabilities: Optional[List[ModelCapability]] = None,
    ) -> RouteDecision:
        """
        Route a request to the appropriate model
        
        Args:
            prompt: User prompt
            context: Optional context
            tier_override: Force a specific tier
            required_capabilities: Force specific capabilities
            
        Returns:
            RouteDecision with selected model and reasoning
        """
        # Analyze the task
        analysis = self.analyze_task(prompt, context)
        
        # Override capabilities if specified
        if required_capabilities:
            analysis.required_capabilities = required_capabilities
        
        # Determine target tier
        if tier_override:
            target_tier = tier_override
            reason = f"Tier override: {tier_override.value}"
        else:
            target_tier, reason = self._select_tier(analysis)
        
        # Find best matching model
        selected = self._find_model(target_tier, analysis.required_capabilities)
        
        # Build fallback list
        fallbacks = []
        for fallback_tier in self.FALLBACK_CHAINS.get(target_tier, []):
            fallback_model = self._find_model(fallback_tier, [])
            if fallback_model:
                fallbacks.append(fallback_model.name)
        
        profile = self.profiles.get(selected.name if selected else "balanced")
        
        return RouteDecision(
            selected_model=selected.name if selected else "qwen2.5-coder:14b",
            tier=target_tier,
            reason=reason,
            confidence=1.0 - analysis.complexity * 0.5,  # Less confident for complex tasks
            fallback_models=fallbacks,
            estimated_latency_ms=profile.avg_latency_ms if profile else 500,
            estimated_tokens=analysis.estimated_tokens,
        )
    
    def _select_tier(self, analysis: TaskAnalysis) -> tuple[ModelTier, str]:
        """Select tier based on task analysis"""
        if analysis.is_conversational and not analysis.requires_code:
            return ModelTier.FAST, "Simple conversational task"
        
        if analysis.complexity < 0.2:
            return ModelTier.FAST, "Low complexity task"
        
        if analysis.complexity < 0.5:
            if analysis.requires_code:
                return ModelTier.BALANCED, "Standard coding task"
            return ModelTier.BALANCED, "Moderate complexity task"
        
        if analysis.complexity < 0.8:
            if analysis.requires_reasoning or ModelCapability.PLANNING in analysis.required_capabilities:
                return ModelTier.POWERFUL, "Complex reasoning/planning task"
            return ModelTier.POWERFUL, "High complexity task"
        
        return ModelTier.ULTRA, "Very high complexity task requiring deep reasoning"
    
    def _find_model(
        self,
        tier: ModelTier,
        required_capabilities: List[ModelCapability],
    ) -> Optional[ModelProfile]:
        """Find the best model for a tier and capability set"""
        # First try exact tier match
        for name, profile in self.profiles.items():
            if profile.tier == tier and profile.is_available:
                # Check capabilities
                has_caps = all(
                    cap in profile.capabilities
                    for cap in required_capabilities
                )
                if has_caps or not required_capabilities:
                    return profile
        
        # Fallback to any available model in tier
        for name, profile in self.profiles.items():
            if profile.tier == tier and profile.is_available:
                return profile
        
        return None
    
    def record_outcome(
        self,
        model: str,
        prompt: str,
        success: bool,
        latency_ms: float,
        tokens_used: int,
    ) -> None:
        """
        Record the outcome of a model call for learning
        
        Args:
            model: Model that was used
            prompt: Original prompt
            success: Whether the call was successful
            latency_ms: Actual latency
            tokens_used: Tokens used
        """
        self._performance_history.append({
            "model": model,
            "prompt_length": len(prompt),
            "success": success,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "timestamp": time.time(),
        })
        
        # Update model profile with running averages
        if model in self.profiles:
            profile = self.profiles[model]
            # Exponential moving average for latency
            alpha = 0.1
            profile.avg_latency_ms = (
                alpha * latency_ms + (1 - alpha) * profile.avg_latency_ms
            )
            # Update success rate
            recent = [
                h for h in self._performance_history[-100:]
                if h["model"] == model
            ]
            if recent:
                profile.success_rate = sum(h["success"] for h in recent) / len(recent)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        if not self._performance_history:
            return {"total_calls": 0}
        
        total = len(self._performance_history)
        successful = sum(1 for h in self._performance_history if h["success"])
        avg_latency = sum(h["latency_ms"] for h in self._performance_history) / total
        
        by_model: Dict[str, int] = {}
        for h in self._performance_history:
            by_model[h["model"]] = by_model.get(h["model"], 0) + 1
        
        return {
            "total_calls": total,
            "success_rate": successful / total,
            "avg_latency_ms": avg_latency,
            "calls_by_model": by_model,
        }
