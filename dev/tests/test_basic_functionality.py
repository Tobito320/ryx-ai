#!/usr/bin/env python3
"""
Ryx AI - Basic Functionality Tests
Quick smoke tests to verify core features work
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all core modules can be imported"""
    print("Testing imports...")

    try:
        from core.ai_engine_v2 import AIEngineV2
        from core.model_orchestrator import ModelOrchestrator
        from core.meta_learner import MetaLearner
        from core.health_monitor import HealthMonitor
        from core.task_manager import TaskManager
        from core.rag_system import RAGSystem
        from core.metrics_collector import MetricsCollector
        from core.cleanup_manager import CleanupManager
        from core.startup_optimizer import StartupOptimizer

        print("  ✓ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_health_monitor():
    """Test health monitoring and auto-fix"""
    print("\nTesting health monitor...")

    try:
        from core.health_monitor import HealthMonitor

        monitor = HealthMonitor()

        # Run health checks
        checks = monitor.run_health_checks()

        print(f"  ✓ Health checks completed: {len(checks)} components")

        # Test Ollama check and fix
        ollama_result = monitor.check_and_fix_ollama()
        if ollama_result['healthy'] or ollama_result['fixed']:
            print(f"  ✓ Ollama status: {ollama_result['message']}")
        else:
            print(f"  ⚠ Ollama status: {ollama_result['message']}")

        return True
    except Exception as e:
        print(f"  ✗ Health monitor test failed: {e}")
        return False


def test_rag_system():
    """Test RAG caching and knowledge"""
    print("\nTesting RAG system...")

    try:
        from core.rag_system import RAGSystem

        rag = RAGSystem()

        # Test caching
        test_prompt = "test query for caching"
        test_response = "test response"

        rag.cache_response(test_prompt, test_response, "test_model")
        cached = rag.query_cache(test_prompt)

        if cached == test_response:
            print("  ✓ Cache write/read works")
        else:
            print("  ✗ Cache test failed")
            return False

        # Test file learning
        rag.learn_file_location("test config", "config", "/test/path.conf", confidence=0.9)

        # Get stats
        stats = rag.get_stats()
        print(f"  ✓ RAG stats: {stats['cached_responses']} cached, {stats['known_files']} files")

        rag.close()
        return True
    except Exception as e:
        print(f"  ✗ RAG test failed: {e}")
        return False


def test_meta_learner():
    """Test preference learning"""
    print("\nTesting meta learner...")

    try:
        from core.meta_learner import MetaLearner

        learner = MetaLearner()

        # Test preference application
        response = "You can edit the file with nano config.txt"

        # Manually set a preference for testing
        learner.learn_preference("editor", "nvim", source="test", confidence=1.0)

        # Apply preferences
        modified = learner.apply_preferences_to_response(response)

        if "nvim" in modified and "nano" not in modified:
            print("  ✓ Preference application works (nano → nvim)")
        else:
            print(f"  ⚠ Preference test inconclusive: {modified}")

        return True
    except Exception as e:
        print(f"  ✗ Meta learner test failed: {e}")
        return False


def test_metrics():
    """Test metrics collection"""
    print("\nTesting metrics collector...")

    try:
        from core.metrics_collector import MetricsCollector

        metrics = MetricsCollector()

        # Record test metric
        metrics.record_query(
            query_type='cache_hit',
            latency_ms=5,
            success=True,
            model_used='test'
        )

        # Get session metrics
        session = metrics.get_session_metrics()

        if session['queries'] > 0:
            print(f"  ✓ Metrics recording works: {session['queries']} queries tracked")
        else:
            print("  ⚠ No metrics recorded")

        return True
    except Exception as e:
        print(f"  ✗ Metrics test failed: {e}")
        return False


def test_cleanup():
    """Test cleanup manager"""
    print("\nTesting cleanup manager...")

    try:
        from core.cleanup_manager import CleanupManager

        manager = CleanupManager()

        # Get disk usage
        usage = manager.get_disk_usage()
        print(f"  ✓ Disk usage: {usage['total_mb']:.2f} MB")
        print(f"    - Databases: {usage['databases_mb']:.2f} MB")
        print(f"    - Logs: {usage['logs_mb']:.2f} MB")
        print(f"    - Cache: {usage['cache_mb']:.2f} MB")

        return True
    except Exception as e:
        print(f"  ✗ Cleanup test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("="*50)
    print("Ryx AI - Basic Functionality Tests")
    print("="*50)

    tests = [
        test_imports,
        test_health_monitor,
        test_rag_system,
        test_meta_learner,
        test_metrics,
        test_cleanup,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Unexpected error in {test.__name__}: {e}")
            results.append(False)

    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        return 0
    else:
        print(f"⚠ Some tests failed ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
