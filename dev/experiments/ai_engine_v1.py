"""
Ryx AI V2 - Unified AI Engine
Orchestrates all components for intelligent, self-healing, personalized assistance
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any

from .model_orchestrator import ModelOrchestrator, QueryResult
from .meta_learner import MetaLearner
from .health_monitor import HealthMonitor
from .task_manager import TaskManager
from .rag_system import RAGSystem


class AIEngine:
    """
    Unified AI Engine that orchestrates all V2 components

    Components:
    1. Model Orchestrator - Intelligent model selection and loading
    2. Meta Learner - Preference learning and pattern recognition
    3. Health Monitor - System health and auto-healing
    4. Task Manager - State persistence and graceful interrupts
    5. RAG System - Zero-latency caching and knowledge base

    Features:
    - Automatic health checking before queries
    - Intelligent model routing based on complexity
    - Preference application from learned patterns
    - Smart caching with semantic similarity
    - Continuous learning from interactions
    """

    def __init__(self):
        """Initialize all components"""
        self.orchestrator = ModelOrchestrator()
        self.meta_learner = MetaLearner()
        self.health_monitor = HealthMonitor()
        self.task_manager = TaskManager()
        self.rag_system = RAGSystem()

        # Start health monitoring in background
        self.health_monitor.start_monitoring()

    def query(self,
              prompt: str,
              system_context: str = "",
              model_override: Optional[str] = None,
              use_cache: bool = True) -> Dict[str, Any]:
        """
        Process a query through the full V2 pipeline

        Pipeline:
        1. Check system health (auto-fix if needed)
        2. Check cache for instant response
        3. Apply learned preferences
        4. Route to appropriate model
        5. Learn from interaction
        6. Cache result

        Args:
            prompt: User query
            system_context: Additional context
            model_override: Force specific model
            use_cache: Whether to use caching

        Returns:
            {
                "response": str,
                "model": str,
                "latency_ms": int,
                "complexity": float,
                "cached": bool,
                "preferences_applied": bool,
                "health_status": str,
                "error": bool
            }
        """
        start_time = time.time()

        # Step 1: Health Check
        if not self.health_monitor.is_healthy():
            # Try auto-repair
            self.health_monitor.run_health_checks()

            # If still unhealthy, return degraded response
            if not self.health_monitor.is_healthy():
                return {
                    "response": "⚠️ System health degraded. Some features may not work correctly.\nRun 'ryx ::health' for details.",
                    "model": None,
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "complexity": 0.0,
                    "cached": False,
                    "preferences_applied": False,
                    "health_status": "unhealthy",
                    "error": True
                }

        # Step 2: Check Cache
        cached_response = None
        if use_cache:
            cached_response = self.rag_system.query_cache(prompt)

        if cached_response:
            # Cache hit! Apply preferences to cached response
            preferences = self.meta_learner.get_preferences()
            final_response = self.meta_learner.apply_preferences(cached_response)

            return {
                "response": final_response,
                "model": "cache",
                "latency_ms": int((time.time() - start_time) * 1000),
                "complexity": 0.0,
                "cached": True,
                "preferences_applied": bool(preferences),
                "health_status": "healthy",
                "error": False
            }

        # Step 3: Get Preferences
        preferences = self.meta_learner.get_preferences()

        # Build context with preferences
        enhanced_context = system_context
        if preferences:
            pref_text = "\n".join([f"{k}: {v}" for k, v in preferences.items()])
            enhanced_context += f"\n\nUser Preferences:\n{pref_text}"

        # Step 4: Query Model
        result: QueryResult = self.orchestrator.query(
            prompt=prompt,
            preferences=preferences,
            system_context=enhanced_context,
            model_override=model_override
        )

        if result.error:
            return {
                "response": result.response,
                "model": result.model_used,
                "latency_ms": result.latency_ms,
                "complexity": result.complexity_score,
                "cached": False,
                "preferences_applied": False,
                "health_status": self.health_monitor.current_status.value,
                "error": True
            }

        # Step 5: Apply Preferences
        original_response = result.response
        final_response = self.meta_learner.apply_preferences(original_response)
        preferences_applied = final_response != original_response

        # Step 6: Learn from Interaction
        self.meta_learner.record_interaction(
            query=prompt,
            response=final_response,
            model_used=result.model_used,
            latency_ms=result.latency_ms,
            complexity=result.complexity_score,
            preferences_applied=preferences if preferences_applied else None
        )

        # Step 7: Cache Result
        if use_cache:
            self.rag_system.cache_response(
                prompt=prompt,
                response=final_response,
                model=result.model_used
            )

        return {
            "response": final_response,
            "model": result.model_used,
            "latency_ms": int((time.time() - start_time) * 1000),
            "complexity": result.complexity_score,
            "cached": False,
            "preferences_applied": preferences_applied,
            "fallback_used": False,
            "health_status": self.health_monitor.current_status.value,
            "error": False
        }

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "health": self.health_monitor.get_status(),
            "orchestrator": self.orchestrator.get_status(),
            "learning": self.meta_learner.get_insights(),
            "cache": self.rag_system.get_stats(),
            "tasks": {
                "current": self.task_manager.current_task.description if self.task_manager.current_task else None,
                "paused": len(self.task_manager.get_all_tasks(status=None))
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
        from .meta_learner import Preference
        from datetime import datetime

        pref = Preference(
            category=category,
            value=value,
            confidence=1.0,  # High confidence for manual setting
            learned_from="Manual setting",
            learned_at=datetime.now()
        )

        self.meta_learner._save_preference(pref)

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
        except:
            pass


# ===================================
# Response Formatter (from V1)
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
    def extract_commands(response: str) -> list:
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
