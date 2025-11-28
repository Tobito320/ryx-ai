"""
Ryx AI V2 - Integrated AI Engine
Orchestrates all components: Model Orchestrator, Meta Learner, Health Monitor, Task Manager, RAG
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Import all V2 components
from core.model_orchestrator import ModelOrchestrator, QueryResult, ModelTier
from core.meta_learner import MetaLearner
from core.health_monitor import HealthMonitor, HealthStatus
from core.task_manager import TaskManager, InterruptionHandler, TaskStatus
from core.rag_system import RAGSystem, FileFinder

# Import original components for backward compatibility
from core.ai_engine import ResponseFormatter
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

logger = logging.getLogger(__name__)


@dataclass
class IntegratedResponse:
    """Response from integrated AI engine"""
    response: str
    model_used: str
    tier_used: str
    latency_ms: int
    cached: bool
    from_cache: bool
    complexity_score: float
    health_status: str
    preferences_applied: List[str]
    error: bool = False
    error_message: Optional[str] = None


class AIEngineV2:
    """
    V2 Integrated AI Engine - The integration hub for all components

    Brings together:
    - Model Orchestrator: Smart lazy-loaded model routing
    - Meta Learner: Preference learning and application
    - Health Monitor: Self-healing capabilities
    - Task Manager: State persistence and graceful interruption
    - RAG System: Intelligent caching

    Features:
    - Starts with ONLY 1.5B model loaded
    - Auto-escalates to bigger models based on complexity
    - Auto-unloads idle models after 5 minutes
    - Learns and applies user preferences
    - Auto-fixes Ollama issues
    - Graceful Ctrl+C with state save
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize V2 integrated AI engine with all components"""
        self.project_root = project_root or get_project_root()

        logger.info("Initializing Ryx AI V2 Integrated Engine...")

        # Initialize all components
        try:
            # Import metrics collector
            from core.metrics_collector import MetricsCollector

            # Initialize metrics collector first
            self.metrics = MetricsCollector()

            # Core components - Use V2 model configuration
            model_config = self.project_root / "configs" / "models_v2.json"
            if not model_config.exists():
                model_config = self.project_root / "configs" / "models.json"

            # Initialize orchestrator with metrics integration
            self.orchestrator = ModelOrchestrator(model_config, metrics_collector=self.metrics)

            self.meta_learner = MetaLearner()  # Uses default path from get_project_root()
            self.health_monitor = HealthMonitor()  # Uses default path from get_project_root()
            self.task_manager = TaskManager()  # Uses default path from get_project_root()
            self.rag = RAGSystem()
            self.file_finder = FileFinder(self.rag)

            # Utilities
            self.formatter = ResponseFormatter()

            # Start health monitoring in background
            self.health_monitor.start_monitoring()

            logger.info("Ryx AI V2 initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AI Engine V2: {e}")
            raise

    def query(self,
              prompt: str,
              context: Optional[str] = None,
              use_cache: bool = True,
              learn_preferences: bool = True) -> IntegratedResponse:
        """
        Execute query with full integration of all V2 components

        Args:
            prompt: User query
            context: Additional context
            use_cache: Whether to use RAG caching
            learn_preferences: Whether to learn from this interaction

        Returns:
            IntegratedResponse with complete information
        """
        start_time = time.time()
        preferences_applied = []

        try:
            # Check system health first
            health_status = self.health_monitor.overall_status

            if health_status == HealthStatus.CRITICAL:
                logger.warning("System health is critical, attempting auto-repair...")
                self.health_monitor.run_health_checks()

            # Check cache first (ultra-fast path)
            if use_cache:
                cached = self.rag.query_cache(prompt)
                if cached:
                    # Apply learned preferences to cached response
                    if learn_preferences:
                        cached = self.meta_learner.apply_preferences_to_response(cached)
                        preferences_applied = self._detect_applied_preferences(cached)

                    latency_ms = int((time.time() - start_time) * 1000)

                    # Record cache hit metrics
                    self.metrics.record_query(
                        query_type='cache_hit',
                        latency_ms=latency_ms,
                        success=True,
                        model_used='cache'
                    )

                    return IntegratedResponse(
                        response=cached,
                        model_used="cache",
                        tier_used="cached",
                        latency_ms=latency_ms,
                        cached=True,
                        from_cache=True,
                        complexity_score=0.0,
                        health_status=health_status.value,
                        preferences_applied=preferences_applied,
                        error=False
                    )

            # Build enriched context
            enriched_context = self._build_enriched_context(prompt, context)

            # Query with model orchestrator (smart routing)
            result: QueryResult = self.orchestrator.query(prompt, enriched_context)

            # Apply learned preferences
            response_text = result.response
            if learn_preferences:
                response_text = self.meta_learner.apply_preferences_to_response(response_text)
                preferences_applied = self._detect_applied_preferences(response_text)

                # Detect and learn new preferences from query
                detected = self.meta_learner.detect_preference_from_query(prompt, response_text)
                if detected:
                    logger.info(f"Detected new preferences: {detected}")

            # Record interaction for learning
            self.meta_learner.record_interaction(
                query=prompt,
                response=response_text,
                model_used=result.model_used,
                latency_ms=result.latency_ms,
                complexity=result.complexity_score,
                preferences_applied=preferences_applied if preferences_applied else None
            )

            # Cache response for future use
            if use_cache:
                self.rag.cache_response(prompt, response_text, result.model_used)

            return IntegratedResponse(
                response=response_text,
                model_used=result.model_used,
                tier_used=result.tier_used.name,
                latency_ms=result.latency_ms,
                cached=False,
                from_cache=False,
                complexity_score=result.complexity_score,
                health_status=health_status.value,
                preferences_applied=preferences_applied,
                error=False
            )

        except Exception as e:
            logger.error(f"Query failed: {e}")

            # Check if it's an Ollama error and try to auto-fix
            error_str = str(e).lower()
            if "404" in error_str or "connection" in error_str or "ollama" in error_str:
                logger.info("Detected Ollama error, attempting auto-fix...")

                # Try to fix Ollama
                fix_result = self.health_monitor.check_and_fix_ollama()

                if fix_result['fixed']:
                    logger.info("Ollama fixed successfully, retrying query...")

                    # Retry the query once
                    try:
                        enriched_context = self._build_enriched_context(prompt, context)
                        result = self.orchestrator.query(prompt, enriched_context)

                        response_text = result.response
                        if learn_preferences:
                            response_text = self.meta_learner.apply_preferences_to_response(response_text)

                        self.meta_learner.record_interaction(
                            query=prompt,
                            response=response_text,
                            model_used=result.model_used,
                            latency_ms=result.latency_ms,
                            complexity=result.complexity_score,
                            preferences_applied=None
                        )

                        if use_cache:
                            self.rag.cache_response(prompt, response_text, result.model_used)

                        return IntegratedResponse(
                            response=response_text,
                            model_used=result.model_used,
                            tier_used=result.tier_used.name,
                            latency_ms=result.latency_ms,
                            cached=False,
                            from_cache=False,
                            complexity_score=result.complexity_score,
                            health_status=self.health_monitor.overall_status.value,
                            preferences_applied=[],
                            error=False
                        )
                    except Exception as retry_error:
                        logger.error(f"Retry after fix failed: {retry_error}")

            # Record failure
            self.meta_learner.record_interaction(
                query=prompt,
                response=str(e),
                model_used="error",
                latency_ms=int((time.time() - start_time) * 1000),
                complexity=0.0,
                preferences_applied=None
            )

            return IntegratedResponse(
                response=str(e),
                model_used="error",
                tier_used="error",
                latency_ms=int((time.time() - start_time) * 1000),
                cached=False,
                from_cache=False,
                complexity_score=0.0,
                health_status="error",
                preferences_applied=[],
                error=True,
                error_message=str(e)
            )

    def _build_enriched_context(self, prompt: str, context: Optional[str] = None) -> Dict:
        """Build enriched context with RAG knowledge and preferences"""
        enriched = {}

        # Add user preferences
        preferences = {}
        for key in ['editor', 'shell', 'theme', 'file_manager']:
            value = self.meta_learner.get_preference(key)
            if value:
                preferences[key] = value

        if preferences:
            enriched['preferences'] = preferences

        # Add RAG context
        rag_context = self.rag.get_context(prompt)
        if rag_context:
            enriched['rag'] = rag_context

        # Add custom context
        if context:
            enriched['custom'] = context

        return enriched

    def _detect_applied_preferences(self, response: str) -> List[str]:
        """Detect which preferences were applied to response"""
        applied = []

        # Check for editor preference
        if 'nvim' in response.lower():
            applied.append('editor=nvim')
        elif 'vim' in response.lower():
            applied.append('editor=vim')

        # Add more detection logic as needed

        return applied

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'orchestrator': self.orchestrator.get_status(),
            'health': self.health_monitor.get_status(),
            'tasks': self.task_manager.get_status(),
            'meta_learning': self.meta_learner.get_stats(),
            'cache': self.rag.get_stats()
        }

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get learned user preference"""
        return self.meta_learner.get_preference(key, default)

    def set_preference(self, key: str, value: Any, confidence: float = 1.0):
        """Explicitly set a user preference"""
        self.meta_learner.learn_preference(key, value, source="explicit", confidence=confidence)

    def install_interrupt_handler(self):
        """Install Ctrl+C handler for graceful interruption"""
        handler = InterruptionHandler(self.task_manager)
        handler.install_handler()
        logger.info("Interrupt handler installed (Ctrl+C will save state)")

    def get_resumable_tasks(self):
        """Get tasks that can be resumed"""
        return self.task_manager.get_resumable_tasks()

    def resume_task(self, task_id: str):
        """Resume a paused/interrupted task"""
        return self.task_manager.resume_task(task_id)

    def shutdown(self):
        """Graceful shutdown of all components"""
        logger.info("Shutting down Ryx AI V2...")

        try:
            # Stop health monitoring
            self.health_monitor.stop_monitoring()

            # Save any pending state
            if self.task_manager.current_task:
                self.task_manager.interrupt_current_task("shutdown")

            # Close RAG connection
            self.rag.close()

            logger.info("Shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Backward compatibility: Export old AIEngine interface
class AIEngine(AIEngineV2):
    """
    Backward compatible AIEngine that uses V2 under the hood

    This allows existing code to continue working while gaining V2 benefits
    """

    def __init__(self) -> None:
        """Initialize backward compatible AI engine"""
        super().__init__()

    def query(self, prompt: str, system_context: str = "", model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Query with old interface (backward compatible)

        Returns old-style dict for compatibility
        """
        result = super().query(prompt, context=system_context, use_cache=True)

        # Convert to old format
        return {
            "response": result.response,
            "model": result.model_used,
            "latency_ms": result.latency_ms,
            "cached": result.from_cache,
            "error": result.error
        }
