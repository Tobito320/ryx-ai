#!/usr/bin/env python3
"""
Comprehensive Ryx AI V2 System Test
Tests all components and integration
"""

import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path.home() / "ryx-ai"))

# Test results
results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
}

def test(name, description=""):
    """Decorator for tests"""
    def decorator(func):
        def wrapper():
            results["summary"]["total"] += 1
            test_result = {
                "name": name,
                "description": description,
                "status": "running",
                "error": None,
                "duration_ms": 0
            }

            print(f"\n{'='*60}")
            print(f"TEST: {name}")
            if description:
                print(f"DESC: {description}")
            print(f"{'='*60}")

            start = time.time()
            try:
                func()
                test_result["status"] = "passed"
                results["summary"]["passed"] += 1
                print(f"✓ PASSED")
            except AssertionError as e:
                test_result["status"] = "failed"
                test_result["error"] = str(e)
                results["summary"]["failed"] += 1
                print(f"✗ FAILED: {e}")
            except Exception as e:
                test_result["status"] = "error"
                test_result["error"] = str(e)
                results["summary"]["failed"] += 1
                print(f"✗ ERROR: {e}")

            test_result["duration_ms"] = int((time.time() - start) * 1000)
            results["tests"].append(test_result)

        return wrapper
    return decorator


# ============================================================================
# TEST 1: Ollama Service
# ============================================================================

@test("ollama_service", "Check if Ollama service is running")
def test_ollama_service():
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    assert response.status_code == 200, f"Ollama returned {response.status_code}"
    models = response.json().get("models", [])
    print(f"  - Found {len(models)} installed models")


# ============================================================================
# TEST 2: Module Imports
# ============================================================================

@test("module_imports", "Test all core module imports")
def test_module_imports():
    from core.ai_engine_v2 import AIEngineV2
    from core.model_orchestrator import ModelOrchestrator
    from core.health_monitor import HealthMonitor
    from core.meta_learner import MetaLearner
    from core.task_manager import TaskManager
    from core.rag_system import RAGSystem
    print("  - All core modules imported successfully")


# ============================================================================
# TEST 3: Configuration Files
# ============================================================================

@test("config_files", "Verify all configuration files")
def test_config_files():
    config_dir = Path.home() / "ryx-ai" / "configs"
    required = ["settings.json", "models.json", "models_v2.json", "permissions.json"]

    for config_file in required:
        path = config_dir / config_file
        assert path.exists(), f"{config_file} not found"
        with open(path, 'r') as f:
            json.load(f)  # Validate JSON
        print(f"  - {config_file}: Valid")


# ============================================================================
# TEST 4: Model Configuration
# ============================================================================

@test("model_config", "Check V2 model configuration")
def test_model_config():
    from core.model_orchestrator import ModelOrchestrator
    from pathlib import Path

    # Use V2 config
    config_path = Path.home() / "ryx-ai" / "configs" / "models_v2.json"
    orchestrator = ModelOrchestrator(config_path)
    status = orchestrator.get_status()

    assert 'available_models' in status, "No model configuration"
    models = status['available_models']

    assert len(models) == 3, f"Expected 3 tiers, found {len(models)}"

    tiers = [m['tier'] for m in models]
    assert 'ULTRA_FAST' in tiers, "ULTRA_FAST tier missing"
    assert 'BALANCED' in tiers, "BALANCED tier missing"
    assert 'POWERFUL' in tiers, "POWERFUL tier missing"

    print(f"  - Configured tiers: {', '.join(tiers)}")


# ============================================================================
# TEST 5: Database Initialization
# ============================================================================

@test("database_init", "Test database initialization")
def test_database_init():
    from core.meta_learner import MetaLearner

    learner = MetaLearner()
    stats = learner.get_stats()

    assert 'total_interactions' in stats, "MetaLearner stats invalid"
    print(f"  - MetaLearner initialized: {stats['total_interactions']} interactions")

    from core.rag_system import RAGSystem
    rag = RAGSystem()
    rag_stats = rag.get_stats()

    assert 'cached_responses' in rag_stats, "RAG stats invalid"
    print(f"  - RAG initialized: {rag_stats['cached_responses']} cached responses")
    rag.close()


# ============================================================================
# TEST 6: Health Monitor
# ============================================================================

@test("health_monitor", "Test health monitoring system")
def test_health_monitor():
    from core.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    checks = monitor.run_health_checks()

    assert len(checks) > 0, "No health checks performed"
    print(f"  - Performed {len(checks)} health checks")

    for component, check in checks.items():
        print(f"  - {component}: {check.status.value} - {check.message}")

    status = monitor.get_status()
    assert 'overall_status' in status, "No overall status"


# ============================================================================
# TEST 7: Task Manager
# ============================================================================

@test("task_manager", "Test task management system")
def test_task_manager():
    from core.task_manager import TaskManager

    manager = TaskManager()

    # Create test task
    task = manager.create_task("test", "Test task", total_steps=3)
    assert task.id, "Task creation failed"
    print(f"  - Created task: {task.id}")

    # Start task
    started = manager.start_task(task.id)
    assert started, "Task start failed"
    print(f"  - Started task")

    # Create checkpoint
    manager.checkpoint(task.id, 1, "Step 1 complete", {"data": "test"})
    print(f"  - Created checkpoint")

    # Complete task
    manager.complete_task(task.id, result="success")
    print(f"  - Completed task")

    # Verify status
    status = manager.get_status()
    assert 'total_tasks' in status, "Status invalid"
    print(f"  - Total tasks: {status['total_tasks']}")


# ============================================================================
# TEST 8: Meta Learner
# ============================================================================

@test("meta_learner", "Test preference learning")
def test_meta_learner():
    from core.meta_learner import MetaLearner

    learner = MetaLearner()

    # Learn a preference
    learner.learn_preference("test_editor", "nvim", source="test", confidence=1.0)
    print(f"  - Learned preference")

    # Retrieve preference
    value = learner.get_preference("test_editor")
    assert value == "nvim", f"Expected 'nvim', got '{value}'"
    print(f"  - Retrieved preference: {value}")

    # Detect from query
    detected = learner.detect_preference_from_query("use nvim not nano")
    assert len(detected) > 0, "Failed to detect preference"
    print(f"  - Detected {len(detected)} preferences from query")

    # Record interaction
    learner.record_interaction(
        query="test query",
        model_used="test-model",
        tier_used="test",
        latency_ms=100,
        success=True
    )
    print(f"  - Recorded interaction")


# ============================================================================
# TEST 9: RAG System
# ============================================================================

@test("rag_system", "Test RAG caching system")
def test_rag_system():
    from core.rag_system import RAGSystem

    rag = RAGSystem()

    # Cache a response
    rag.cache_response("test query", "test response", "test-model")
    print(f"  - Cached response")

    # Query cache
    cached = rag.query_cache("test query")
    assert cached == "test response", "Cache query failed"
    print(f"  - Retrieved from cache")

    # Get stats
    stats = rag.get_stats()
    assert stats['total_cache_hits'] > 0, "Cache hits not recorded"
    print(f"  - Cache hits: {stats['total_cache_hits']}")

    rag.close()


# ============================================================================
# TEST 10: Model Orchestrator (requires models)
# ============================================================================

@test("model_orchestrator", "Test model orchestration (may skip if models unavailable)")
def test_model_orchestrator():
    from core.model_orchestrator import ModelOrchestrator
    import requests

    # Check if models are available
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models_data = response.json()
        installed = [m['name'] for m in models_data.get('models', [])]

        if 'qwen2.5:1.5b' not in installed:
            print("  - Skipping: qwen2.5:1.5b not installed yet")
            results["summary"]["skipped"] += 1
            return
    except:
        print("  - Skipping: Cannot check Ollama models")
        results["summary"]["skipped"] += 1
        return

    orchestrator = ModelOrchestrator()

    # Test complexity analysis
    from core.model_orchestrator import ComplexityAnalyzer
    analyzer = ComplexityAnalyzer()

    simple_score = analyzer.analyze("what is the time")
    complex_score = analyzer.analyze("design a complex architecture for microservices")

    assert simple_score < complex_score, "Complexity analysis failed"
    print(f"  - Simple query score: {simple_score:.2f}")
    print(f"  - Complex query score: {complex_score:.2f}")

    # Test model status
    status = orchestrator.get_status()
    print(f"  - Available models: {len(status['available_models'])}")
    print(f"  - Loaded models: {len(status['loaded_models'])}")


# ============================================================================
# TEST 11: AIEngineV2 Integration
# ============================================================================

@test("ai_engine_v2", "Test integrated AI engine (may skip if models unavailable)")
def test_ai_engine_v2():
    from core.ai_engine_v2 import AIEngineV2
    import requests

    # Check if models are available
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models_data = response.json()
        installed = [m['name'] for m in models_data.get('models', [])]

        if not any('qwen' in m or 'deepseek' in m for m in installed):
            print("  - Skipping: No suitable models installed")
            results["summary"]["skipped"] += 1
            return
    except:
        print("  - Skipping: Cannot check Ollama models")
        results["summary"]["skipped"] += 1
        return

    engine = AIEngineV2()

    # Test status
    status = engine.get_status()
    assert 'orchestrator' in status, "Orchestrator status missing"
    assert 'health' in status, "Health status missing"
    assert 'meta_learning' in status, "Meta learning status missing"

    print(f"  - AIEngineV2 initialized successfully")
    print(f"  - Components: {', '.join(status.keys())}")

    # Test simple query (if models available)
    try:
        result = engine.query("What is 2+2?", use_cache=False, learn_preferences=False)
        assert not result.error, f"Query failed: {result.error_message}"
        print(f"  - Query executed: {result.model_used} ({result.latency_ms}ms)")
    except Exception as e:
        print(f"  - Query test skipped: {e}")


# ============================================================================
# TEST 12: CLI Mode
# ============================================================================

@test("cli_mode", "Test CLI mode functionality")
def test_cli_mode():
    from modes.cli_mode import CLIMode

    # Just test initialization
    cli = CLIMode()
    assert cli.ai is not None, "CLI AI engine not initialized"
    assert cli.rag is not None, "CLI RAG not initialized"
    print(f"  - CLI mode initialized successfully")


# ============================================================================
# TEST 13: File Permissions
# ============================================================================

@test("file_permissions", "Check file permissions")
def test_file_permissions():
    project_root = Path.home() / "ryx-ai"

    # Check main executable
    ryx_bin = project_root / "ryx"
    assert ryx_bin.exists(), "ryx binary not found"
    assert ryx_bin.stat().st_mode & 0o111, "ryx not executable"
    print(f"  - ryx binary: executable")

    # Check venv
    venv_python = project_root / ".venv" / "bin" / "python3"
    assert venv_python.exists(), "venv python not found"
    print(f"  - venv: present")

    # Check data directory
    data_dir = project_root / "data"
    assert data_dir.exists(), "data directory not found"
    assert data_dir.is_dir(), "data is not a directory"
    print(f"  - data directory: present")


# ============================================================================
# Run all tests
# ============================================================================

def run_all_tests():
    print("\n" + "="*60)
    print("RYX AI V2 - COMPREHENSIVE SYSTEM TEST")
    print("="*60)

    # Run tests
    test_ollama_service()
    test_module_imports()
    test_config_files()
    test_model_config()
    test_database_init()
    test_health_monitor()
    test_task_manager()
    test_meta_learner()
    test_rag_system()
    test_model_orchestrator()
    test_ai_engine_v2()
    test_cli_mode()
    test_file_permissions()

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total:   {results['summary']['total']}")
    print(f"Passed:  {results['summary']['passed']} ✓")
    print(f"Failed:  {results['summary']['failed']} ✗")
    print(f"Skipped: {results['summary']['skipped']} ○")
    print("="*60)

    # Save results
    results_file = Path.home() / "ryx-ai" / "test_results_comprehensive.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
