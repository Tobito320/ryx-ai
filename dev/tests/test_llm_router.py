"""
Tests for LLM Router module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from core.model_router import ModelRouter, ModelRole

# Note: LLMRouter was renamed to ModelRouter in the actual implementation

@pytest.fixture
def router():
    """Create a router instance for testing."""
    return ModelRouter()


class TestIntentDetection:
    """Tests for intent detection."""
    
    def test_detect_search_intent(self, router):
        """Test detecting search intent."""
        intent, _ = router._detect_intent("find files in my config")
        assert intent == Intent.SEARCH
    
    def test_detect_code_intent(self, router):
        """Test detecting code intent."""
        intent, _ = router._detect_intent("debug this python function")
        assert intent == Intent.CODE
    
    def test_detect_chat_intent(self, router):
        """Test detecting chat intent."""
        intent, _ = router._detect_intent("explain how this works")
        assert intent == Intent.CHAT
    
    def test_detect_shell_intent(self, router):
        """Test detecting shell intent."""
        intent, _ = router._detect_intent("run docker container")
        assert intent == Intent.SHELL
    
    def test_unknown_intent(self, router):
        """Test unknown intent fallback."""
        intent, _ = router._detect_intent("hello there")
        assert intent == Intent.UNKNOWN
    
    def test_confidence_score(self, router):
        """Test that confidence is between 0 and 1."""
        _, confidence = router._detect_intent("find and search files")
        assert 0.0 <= confidence <= 1.0


class TestRouting:
    """Tests for query routing."""
    
    @pytest.mark.asyncio
    async def test_route_to_search_model(self, router):
        """Test routing search queries to correct model."""
        with patch.object(router, 'check_availability', return_value=True):
            result = await router.route("find my config files")
            assert result.model == "qwen2.5:3b"
            assert result.intent == Intent.SEARCH
    
    @pytest.mark.asyncio
    async def test_fallback_when_unavailable(self, router):
        """Test fallback when primary model unavailable."""
        availability = {
            "qwen2.5:3b": False,
            "qwen2.5-coder:14b": True,
        }
        
        async def mock_availability(model):
            return availability.get(model, False)
        
        with patch.object(router, 'check_availability', side_effect=mock_availability):
            result = await router.route("find files")
            assert result.fallback_used is True
    
    @pytest.mark.asyncio
    async def test_routing_result_structure(self, router):
        """Test that routing result has expected structure."""
        with patch.object(router, 'check_availability', return_value=True):
            result = await router.route("test query")
            
            assert isinstance(result, RoutingResult)
            assert isinstance(result.intent, Intent)
            assert isinstance(result.model, str)
            assert isinstance(result.confidence, float)
            assert isinstance(result.fallback_used, bool)


class TestAvailability:
    """Tests for model availability checking."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, router):
        """Test that cache is used for availability checks."""
        # Pre-populate cache
        router._availability_cache["test-model"] = (True, datetime.now())
        
        result = await router.check_availability("test-model")
        assert result is True
    
    def test_clear_cache(self, router):
        """Test cache clearing."""
        router._availability_cache["test"] = (True, datetime.now())
        router._latency_cache["test"] = (100.0, datetime.now())
        
        router.clear_cache()
        
        assert len(router._availability_cache) == 0
        assert len(router._latency_cache) == 0


class TestIntentModels:
    """Tests for intent to model mapping."""
    
    def test_all_intents_have_models(self, router):
        """Test that all intents map to models."""
        for intent in Intent:
            assert intent in router.INTENT_MODELS
    
    def test_fallback_chain_not_empty(self, router):
        """Test that fallback chain has models."""
        assert len(router.FALLBACK_CHAIN) > 0
