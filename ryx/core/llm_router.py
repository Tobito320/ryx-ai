"""
Ryx AI - LLM Router
Routes queries to appropriate LLM models based on intent detection.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class Intent(Enum):
    """User intent types."""

    SEARCH = "search"
    CODE = "code"
    CHAT = "chat"
    SHELL = "shell"
    UNKNOWN = "unknown"


@dataclass
class RoutingResult:
    """Result of query routing."""

    intent: Intent
    model: str
    confidence: float
    fallback_used: bool = False


class LatencyError(Exception):
    """Raised when model latency exceeds threshold."""

    pass


class ModelUnavailableError(Exception):
    """Raised when no models are available."""

    pass


class LLMRouter:
    """
    Routes queries to appropriate LLM models based on intent detection.

    Features:
        - Intent detection from query keywords
        - Model availability checking
        - Automatic fallback to available models
        - Latency caching for performance

    Example:
        router = LLMRouter()
        result = await router.route("find files in my config")
        # result.model == "qwen2.5:3b"
    """

    # Intent to model mapping
    INTENT_MODELS: Dict[Intent, str] = {
        Intent.SEARCH: "qwen2.5:3b",
        Intent.CODE: "qwen2.5-coder:14b",
        Intent.CHAT: "gpt-oss-abliterated:20b",
        Intent.SHELL: "mistral:7b",
        Intent.UNKNOWN: "mistral:7b",  # Default
    }

    # Fallback chain
    FALLBACK_CHAIN: List[str] = [
        "qwen2.5-coder:14b",
        "mistral:7b",
        "qwen2.5:3b",
    ]

    # Intent keywords
    INTENT_KEYWORDS: Dict[Intent, List[str]] = {
        Intent.SEARCH: ["find", "search", "locate", "where", "look for"],
        Intent.CODE: [
            "code",
            "debug",
            "fix",
            "refactor",
            "implement",
            "function",
            "class",
        ],
        Intent.CHAT: [
            "chat",
            "talk",
            "explain",
            "creative",
            "write",
            "help me understand",
        ],
        Intent.SHELL: [
            "shell",
            "command",
            "docker",
            "system",
            "run",
            "execute",
            "terminal",
        ],
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        cache_ttl_seconds: int = 300,
        latency_threshold_ms: float = 5000.0,
    ):
        """
        Initialize the LLM Router.

        Args:
            base_url: Ollama API base URL
            cache_ttl_seconds: Cache TTL for availability checks (default: 5 min)
            latency_threshold_ms: Maximum acceptable latency (default: 5000ms)
        """
        self.base_url = base_url
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.latency_threshold = latency_threshold_ms

        # Caches
        self._availability_cache: Dict[str, Tuple[bool, datetime]] = {}
        self._latency_cache: Dict[str, Tuple[float, datetime]] = {}

    async def route(self, query: str) -> RoutingResult:
        """
        Route a query to the appropriate model.

        Args:
            query: User's input query

        Returns:
            RoutingResult with intent, model, and confidence

        Raises:
            ModelUnavailableError: If no models are available
        """
        # Detect intent
        intent, confidence = self._detect_intent(query)

        # Get primary model for intent
        primary_model = self.INTENT_MODELS.get(
            intent, self.INTENT_MODELS[Intent.UNKNOWN]
        )

        # Check availability
        if await self.check_availability(primary_model):
            return RoutingResult(
                intent=intent,
                model=primary_model,
                confidence=confidence,
                fallback_used=False,
            )

        # Try fallback
        fallback = await self.get_fallback(primary_model)
        if fallback:
            return RoutingResult(
                intent=intent,
                model=fallback,
                confidence=confidence,
                fallback_used=True,
            )

        raise ModelUnavailableError("No models available")

    def _detect_intent(self, query: str) -> Tuple[Intent, float]:
        """
        Detect intent from query keywords.

        Args:
            query: User's input query

        Returns:
            Tuple of (Intent, confidence score 0.0-1.0)
        """
        query_lower = query.lower()

        scores: Dict[Intent, int] = {intent: 0 for intent in Intent}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[intent] += 1

        # Find best match
        best_intent = Intent.UNKNOWN
        best_score = 0

        for intent, score in scores.items():
            if score > best_score:
                best_score = score
                best_intent = intent

        # Calculate confidence
        confidence = min(best_score / 3.0, 1.0)  # Cap at 1.0

        return best_intent, confidence

    async def check_availability(self, model: str) -> bool:
        """
        Check if a model is available.

        Args:
            model: Model name to check

        Returns:
            True if model is available
        """
        # Check cache
        if model in self._availability_cache:
            available, cached_at = self._availability_cache[model]
            if datetime.now() - cached_at < self.cache_ttl:
                return available

        if not HTTPX_AVAILABLE:
            # If httpx not available, assume model is available (local stub)
            self._availability_cache[model] = (True, datetime.now())
            return True

        # Query Ollama
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0,
                )
                response.raise_for_status()
                data = response.json()

                models = [m["name"] for m in data.get("models", [])]
                available = model in models

                # Cache result
                self._availability_cache[model] = (available, datetime.now())

                return available

        except Exception:
            self._availability_cache[model] = (False, datetime.now())
            return False

    async def get_fallback(self, failed_model: str) -> Optional[str]:
        """
        Get fallback model when primary is unavailable.

        Args:
            failed_model: Model that failed availability check

        Returns:
            Available fallback model or None
        """
        for model in self.FALLBACK_CHAIN:
            if model != failed_model and await self.check_availability(model):
                return model
        return None

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._availability_cache.clear()
        self._latency_cache.clear()
