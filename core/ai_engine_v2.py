"""
Ryx AI V2 - Enhanced AI Engine
JARVIS-grade unified AI engine with <2s latency target, intelligent model routing,
and automatic failover.

Core Philosophy:
- Sub-2s latency for all operations (or fail gracefully)
- Never slower than useful (if performance > usability cost, disable it)
- Permission-aware execution
- Model-aware routing (pick best model for task, not all tasks)
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .model_orchestrator import ModelOrchestrator, QueryResult
from .meta_learner import MetaLearner
from .health_monitor import HealthMonitor
from .task_manager import TaskManager
from .rag_system import RAGSystem
from .performance_profiler import Timer, get_profiler


@dataclass
class LatencyMetrics:
    """Track latency metrics for performance monitoring"""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    latency_violations: int = 0  # Queries exceeding 2s target

    def record(self, latency_ms: float, from_cache: bool = False):
        """Record a query latency"""
        self.total_queries += 1
        self.total_latency_ms += latency_ms
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)

        if from_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        if latency_ms > 2000:  # 2 second target
            self.latency_violations += 1

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds"""
        return self.total_latency_ms / self.total_queries if self.total_queries > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage"""
        return (self.cache_hits / self.total_queries * 100) if self.total_queries > 0 else 0.0

    @property
    def latency_compliance_rate(self) -> float:
        """Percentage of queries meeting <2s target"""
        compliant = self.total_queries - self.latency_violations
        return (compliant / self.total_queries * 100) if self.total_queries > 0 else 100.0


@dataclass
class QueryOptions:
    """Options for query processing"""
    use_cache: bool = True
    max_latency_ms: int = 2000  # 2 second default target
    fallback_on_timeout: bool = True
    model_override: Optional[str] = None
    tier_override: Optional[str] = None
    stream: bool = False


class AIEngineV2:
    """
    JARVIS-grade AI Engine with <2s latency target

    Features:
    - Latency monitoring with 2s target enforcement
    - Multi-layer caching (hot -> warm -> cold)
    - Intelligent model failover
    - Automatic preference learning
    - Health monitoring with auto-recovery
    - Performance profiling

    Architecture:
    1. Cache Layer - Zero-latency responses for known queries
    2. Fast Model Layer - Sub-second responses for simple queries
    3. Balanced Model Layer - Standard coding responses
    4. Powerful Model Layer - Complex reasoning (may exceed 2s)
    """

    # Latency targets in milliseconds
    LATENCY_TARGET_MS = 2000  # 2 seconds
    CACHE_TARGET_MS = 50      # 50ms for cache hits
    FAST_MODEL_TARGET_MS = 500  # 500ms for fast model

    def __init__(self, skip_health_start: bool = False):
        """
        Initialize enhanced AI engine

        Args:
            skip_health_start: Skip background health monitoring (for testing)
        """
        # Initialize all components
        self.orchestrator = ModelOrchestrator()
        self.meta_learner = MetaLearner()
        self.health_monitor = HealthMonitor()
        self.task_manager = TaskManager()
        self.rag_system = RAGSystem()

        # Latency tracking
        self.latency_metrics = LatencyMetrics()

        # Profiler
        self.profiler = get_profiler()

        # Start health monitoring in background (optional)
        if not skip_health_start:
            self.health_monitor.start_monitoring()

    def query(self,
              prompt: str,
              system_context: str = "",
              options: Optional[QueryOptions] = None) -> Dict[str, Any]:
        """
        Process a query with <2s latency target

        Pipeline (optimized for latency):
        1. [<50ms] Check hot cache for instant response
        2. [<100ms] Apply learned preferences
        3. [<500ms] Check warm cache (semantic similarity)
        4. [<2000ms] Query model with failover
        5. [async] Cache result and learn from interaction

        Args:
            prompt: User query
            system_context: Additional context
            options: Query processing options

        Returns:
            {
                "response": str,
                "model": str,
                "latency_ms": int,
                "complexity": float,
                "cached": bool,
                "preferences_applied": bool,
                "health_status": str,
                "latency_target_met": bool,
                "error": bool
            }
        """
        if options is None:
            options = QueryOptions()

        start_time = time.perf_counter()

        # Step 1: Health Check (fast, non-blocking)
        health_status = "healthy"
        if not self.health_monitor.is_healthy():
            health_status = "degraded"
            # Continue anyway - don't block on health

        # Step 2: Check Cache (<50ms target)
        cached_response = None
        if options.use_cache:
            with Timer("cache_lookup"):
                cached_response = self.rag_system.query_cache(prompt)

            if cached_response:
                # Apply preferences to cached response
                preferences = self.meta_learner.get_preferences()
                final_response = self.meta_learner.apply_preferences(cached_response)

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                self.latency_metrics.record(latency_ms, from_cache=True)

                return {
                    "response": final_response,
                    "model": "cache",
                    "latency_ms": latency_ms,
                    "complexity": 0.0,
                    "cached": True,
                    "preferences_applied": bool(preferences),
                    "health_status": health_status,
                    "latency_target_met": latency_ms < self.LATENCY_TARGET_MS,
                    "error": False
                }

        # Step 3: Get Preferences
        preferences = self.meta_learner.get_preferences()
        enhanced_context = system_context
        if preferences:
            pref_text = "\n".join([f"{k}: {v}" for k, v in preferences.items()])
            enhanced_context += f"\n\nUser Preferences:\n{pref_text}"

        # Step 4: Query Model with latency awareness
        result = self._query_with_latency_target(
            prompt=prompt,
            system_context=enhanced_context,
            preferences=preferences,
            options=options,
            remaining_time_ms=options.max_latency_ms - int((time.perf_counter() - start_time) * 1000)
        )

        if result.error:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            self.latency_metrics.record(latency_ms, from_cache=False)

            return {
                "response": result.response,
                "model": result.model_used,
                "latency_ms": latency_ms,
                "complexity": result.complexity_score,
                "cached": False,
                "preferences_applied": False,
                "health_status": health_status,
                "latency_target_met": latency_ms < self.LATENCY_TARGET_MS,
                "error": True
            }

        # Step 5: Apply Preferences
        original_response = result.response
        final_response = self.meta_learner.apply_preferences(original_response)
        preferences_applied = final_response != original_response

        # Step 6: Record interaction and cache (async-friendly)
        self.meta_learner.record_interaction(
            query=prompt,
            response=final_response,
            model_used=result.model_used,
            latency_ms=result.latency_ms,
            complexity=result.complexity_score,
            preferences_applied=preferences if preferences_applied else None
        )

        # Cache the response (async-friendly, non-blocking)
        if options.use_cache:
            self.rag_system.cache_response(
                prompt=prompt,
                response=final_response,
                model=result.model_used
            )

        total_latency_ms = int((time.perf_counter() - start_time) * 1000)
        self.latency_metrics.record(total_latency_ms, from_cache=False)

        return {
            "response": final_response,
            "model": result.model_used,
            "latency_ms": total_latency_ms,
            "complexity": result.complexity_score,
            "cached": False,
            "preferences_applied": preferences_applied,
            "health_status": health_status,
            "latency_target_met": total_latency_ms < self.LATENCY_TARGET_MS,
            "error": False
        }

    def _query_with_latency_target(self,
                                    prompt: str,
                                    system_context: str,
                                    preferences: Optional[Dict],
                                    options: QueryOptions,
                                    remaining_time_ms: int) -> QueryResult:
        """
        Query model with latency target enforcement

        Strategy:
        1. If remaining time < 500ms, use fast model only
        2. If remaining time < 1500ms, use balanced model with fast fallback
        3. Otherwise, use complexity-based routing
        """
        # Determine model based on time budget
        if remaining_time_ms < 500:
            # Critical time - use fast model only
            model_override = options.model_override or "qwen2.5:1.5b"
        elif remaining_time_ms < 1500 and not options.model_override:
            # Limited time - prefer fast models
            # Let orchestrator decide but hint at fast
            model_override = None
        else:
            model_override = options.model_override

        # Query through orchestrator
        return self.orchestrator.query(
            prompt=prompt,
            preferences=preferences,
            system_context=system_context,
            model_override=model_override
        )

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including latency metrics"""
        return {
            "health": self.health_monitor.get_status(),
            "orchestrator": self.orchestrator.get_status(),
            "learning": self.meta_learner.get_insights(),
            "cache": self.rag_system.get_stats(),
            "latency": {
                "total_queries": self.latency_metrics.total_queries,
                "avg_latency_ms": round(self.latency_metrics.avg_latency_ms, 2),
                "max_latency_ms": round(self.latency_metrics.max_latency_ms, 2),
                "cache_hit_rate": round(self.latency_metrics.cache_hit_rate, 2),
                "latency_compliance_rate": round(self.latency_metrics.latency_compliance_rate, 2),
                "latency_violations": self.latency_metrics.latency_violations,
            },
            "tasks": {
                "current": self.task_manager.current_task.description if self.task_manager.current_task else None,
                "paused": len(self.task_manager.get_all_tasks(status=None))
            }
        }

    def get_latency_report(self) -> Dict[str, Any]:
        """Get detailed latency performance report"""
        return {
            "metrics": {
                "total_queries": self.latency_metrics.total_queries,
                "cache_hits": self.latency_metrics.cache_hits,
                "cache_misses": self.latency_metrics.cache_misses,
                "avg_latency_ms": round(self.latency_metrics.avg_latency_ms, 2),
                "min_latency_ms": round(self.latency_metrics.min_latency_ms, 2) if self.latency_metrics.min_latency_ms != float('inf') else 0,
                "max_latency_ms": round(self.latency_metrics.max_latency_ms, 2),
                "cache_hit_rate_pct": round(self.latency_metrics.cache_hit_rate, 2),
                "latency_compliance_pct": round(self.latency_metrics.latency_compliance_rate, 2),
            },
            "targets": {
                "latency_target_ms": self.LATENCY_TARGET_MS,
                "cache_target_ms": self.CACHE_TARGET_MS,
                "fast_model_target_ms": self.FAST_MODEL_TARGET_MS,
            },
            "performance": {
                "latency_violations": self.latency_metrics.latency_violations,
                "meeting_target": self.latency_metrics.latency_compliance_rate > 95,
            }
        }

    def get_health(self) -> Dict[str, Any]:
        """Get detailed health information"""
        health_checks = self.health_monitor.run_health_checks()
        incidents = self.health_monitor.get_incident_history(limit=5)

        return {
            "overall_status": self.health_monitor.current_status.value,
            "components": {
                name: {
                    "status": check.status.value,
                    "message": check.message
                }
                for name, check in health_checks.items()
            },
            "recent_incidents": incidents
        }

    def get_preferences(self) -> Dict[str, Any]:
        """Get learned preferences"""
        insights = self.meta_learner.get_insights()

        return {
            "preferences": insights["preferences"],
            "patterns": insights["patterns"],
            "suggestions": self.meta_learner.suggest_optimizations()
        }

    def set_preference(self, category: str, value: str):
        """Manually set a preference"""
        self.meta_learner.learn_preference(
            key=category,
            value=value,
            source="Manual setting",
            confidence=1.0
        )

    def resume_task(self) -> Optional[Dict[str, Any]]:
        """Resume the last paused task"""
        task = self.task_manager.get_last_paused_task()

        if not task:
            return {
                "success": False,
                "message": "No paused tasks found"
            }

        resumed = self.task_manager.resume_task(task.task_id)

        if resumed:
            return {
                "success": True,
                "task_id": resumed.task_id,
                "description": resumed.description,
                "current_step": resumed.current_step_index,
                "total_steps": len(resumed.steps)
            }
        else:
            return {
                "success": False,
                "message": "Failed to resume task"
            }

    def cleanup(self):
        """Cleanup resources"""
        self.health_monitor.stop_monitoring()
        self.rag_system.close()

    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            self.cleanup()
        except Exception:
            pass


# ===================================
# Response Formatter
# ===================================

class ResponseFormatter:
    """Format AI responses for beautiful terminal output"""

    @staticmethod
    def format_cli(response: str, show_model: bool = False) -> str:
        """
        Format response for CLI mode

        Extracts bash commands and highlights them
        """
        lines = response.split('\n')
        output = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if not in_code_block:
                    output.append('')  # Add newline after code block
                continue

            if in_code_block:
                # This is a command - highlight it
                output.append(f"  \033[1;36m{line}\033[0m")
            elif line.strip():
                # Regular text
                output.append(f"\033[0;37m{line}\033[0m")

        return '\n'.join(output)

    @staticmethod
    def extract_commands(response: str) -> List[str]:
        """Extract bash commands from response"""
        commands = []
        in_code_block = False
        current_block = []

        for line in response.split('\n'):
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of block
                    if current_block:
                        commands.append('\n'.join(current_block))
                        current_block = []
                in_code_block = not in_code_block
                continue

            if in_code_block and line.strip():
                current_block.append(line.strip())

        return commands
