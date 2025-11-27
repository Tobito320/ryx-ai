"""
Ryx AI V2 - Component Tests
Tests for all new V2 components
"""

import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.home() / "ryx-ai"))


class TestModelOrchestrator:
    """Test Model Orchestrator"""

    def test_import(self):
        """Test that model orchestrator can be imported"""
        from core.model_orchestrator import ModelOrchestrator
        assert ModelOrchestrator is not None

    def test_complexity_analysis(self):
        """Test query complexity analysis"""
        from core.model_orchestrator import ModelOrchestrator

        orchestrator = ModelOrchestrator()

        # Simple query should have low complexity
        simple = "open config"
        complexity = orchestrator.analyze_complexity(simple)
        assert complexity < 0.3, f"Simple query has too high complexity: {complexity}"

        # Complex query should have high complexity
        complex_query = "refactor this architecture to use design patterns and optimize performance"
        complexity = orchestrator.analyze_complexity(complex_query)
        assert complexity > 0.6, f"Complex query has too low complexity: {complexity}"

    def test_model_selection(self):
        """Test model selection based on complexity"""
        from core.model_orchestrator import ModelOrchestrator

        orchestrator = ModelOrchestrator()

        # Low complexity -> ultra-fast model
        model = orchestrator.select_model(0.2)
        assert "1.5b" in model or model == orchestrator.model_tiers["ultra-fast"].name

        # High complexity -> powerful model
        model = orchestrator.select_model(0.8)
        assert "14b" in model or model == orchestrator.model_tiers["powerful"].name


class TestMetaLearner:
    """Test Meta Learner"""

    def test_import(self):
        """Test that meta learner can be imported"""
        from core.meta_learner import MetaLearner
        assert MetaLearner is not None

    def test_preference_detection(self):
        """Test preference detection from queries"""
        from core.meta_learner import MetaLearner

        learner = MetaLearner()

        # Test editor preference detection
        query = "use nvim not nano"
        detected = learner.detect_preferences_from_query(query)

        assert len(detected) > 0, "Should detect preference"
        assert detected[0].category == "editor", "Should detect editor preference"
        assert detected[0].value == "nvim", f"Should detect nvim, got {detected[0].value}"

    def test_preference_application(self):
        """Test preference application to responses"""
        from core.meta_learner import MetaLearner, Preference
        from datetime import datetime

        learner = MetaLearner()

        # Set preference
        pref = Preference(
            category="editor",
            value="nvim",
            confidence=1.0,
            learned_from="test",
            learned_at=datetime.now()
        )
        learner._save_preference(pref)

        # Apply to response
        response = "nano config.txt"
        modified = learner.apply_preferences(response)

        assert "nvim" in modified, "Should replace nano with nvim"
        assert "nano" not in modified, "Should not contain nano anymore"

    def test_similarity(self):
        """Test text similarity computation"""
        from core.rag_system import RAGSystem

        rag = RAGSystem()

        # Identical texts
        similarity = rag.compute_similarity("open config", "open config")
        assert similarity == 1.0, "Identical texts should have similarity 1.0"

        # Similar texts
        similarity = rag.compute_similarity("open hyprland config", "show hypr conf")
        assert similarity > 0.3, "Similar texts should have some similarity"

        # Different texts
        similarity = rag.compute_similarity("open config", "delete files")
        assert similarity < 0.3, "Different texts should have low similarity"


class TestHealthMonitor:
    """Test Health Monitor"""

    def test_import(self):
        """Test that health monitor can be imported"""
        from core.health_monitor import HealthMonitor
        assert HealthMonitor is not None

    def test_initialization(self):
        """Test health monitor initialization"""
        from core.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        assert monitor is not None
        assert monitor.ollama_url == "http://localhost:11434"

    def test_health_checks(self):
        """Test running health checks"""
        from core.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        checks = monitor.run_health_checks()

        assert "ollama" in checks, "Should check Ollama"
        assert "database" in checks, "Should check database"
        assert "disk" in checks, "Should check disk"
        assert "memory" in checks, "Should check memory"

        # Each check should have status
        for component, check in checks.items():
            assert hasattr(check, "status"), f"{component} check should have status"
            assert hasattr(check, "message"), f"{component} check should have message"


class TestTaskManager:
    """Test Task Manager"""

    def test_import(self):
        """Test that task manager can be imported"""
        from core.task_manager import TaskManager
        assert TaskManager is not None

    def test_task_creation(self):
        """Test creating a task"""
        from core.task_manager import TaskManager, TaskStatus

        manager = TaskManager()

        task = manager.create_task(
            description="Test task",
            steps=["Step 1", "Step 2", "Step 3"]
        )

        assert task is not None
        assert task.description == "Test task"
        assert len(task.steps) == 3
        assert task.status == TaskStatus.PENDING

    def test_task_persistence(self):
        """Test task state persistence"""
        from core.task_manager import TaskManager

        manager = TaskManager()

        # Create task
        task = manager.create_task("Persistent task")
        task_id = task.task_id

        # Start task
        manager.start_task(task)

        # Pause task
        manager.pause_task(task)

        # Load task in new manager instance
        manager2 = TaskManager()
        loaded_task = manager2._load_task(task_id)

        assert loaded_task is not None
        assert loaded_task.task_id == task_id
        assert loaded_task.description == "Persistent task"


class TestAIEngine:
    """Test AI Engine Integration"""

    def test_import(self):
        """Test that AI engine can be imported"""
        from core.ai_engine import AIEngine
        assert AIEngine is not None

    def test_initialization(self):
        """Test AI engine initialization"""
        from core.ai_engine import AIEngine

        engine = AIEngine()

        assert engine.orchestrator is not None
        assert engine.meta_learner is not None
        assert engine.health_monitor is not None
        assert engine.task_manager is not None
        assert engine.rag_system is not None

        # Cleanup
        engine.cleanup()

    def test_status(self):
        """Test getting system status"""
        from core.ai_engine import AIEngine

        engine = AIEngine()

        status = engine.get_status()

        assert "health" in status
        assert "orchestrator" in status
        assert "learning" in status
        assert "cache" in status
        assert "tasks" in status

        # Cleanup
        engine.cleanup()


class TestRAGSystemV2:
    """Test RAG System V2 enhancements"""

    def test_stats_bug_fixed(self):
        """Test that stats bug is fixed"""
        from core.rag_system import RAGSystem

        rag = RAGSystem()
        stats = rag.get_stats()

        # Should return valid stats (not None or error)
        assert "cached_responses" in stats
        assert "known_files" in stats
        assert "total_cache_hits" in stats
        assert "hot_cache_size" in stats

        # Should be numbers
        assert isinstance(stats["cached_responses"], int)
        assert isinstance(stats["known_files"], int)
        assert isinstance(stats["total_cache_hits"], int)


def run_tests():
    """Run all tests"""
    print("🧪 Running Ryx AI V2 Component Tests")
    print("=" * 50)
    print()

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
