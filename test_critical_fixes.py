#!/usr/bin/env python3
"""
Test script for critical Ryx AI fixes

Tests:
1. RAG Database Schema (knowledge table)
2. SearXNG environment variable support
3. Model validation at startup
4. Web search with retry logic
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_rag_database_schema():
    """Test that knowledge table exists and works"""
    print("\n🧪 Test 1: RAG Database Schema")
    print("─" * 50)

    try:
        from core.rag_system import RAGSystem

        rag = RAGSystem()

        # Test learn_file_location
        test_query = "test hyprland config"
        test_path = "~/.config/hypr/hyprland.conf"
        rag.learn_file_location(test_query, "config", test_path, confidence=1.0)
        print("✅ learn_file_location() works")

        # Test recall_file_location
        result = rag.recall_file_location(test_query)
        if result and result['file_path'] == test_path:
            print("✅ recall_file_location() works")
            print(f"   Retrieved: {result['file_path']}")
        else:
            print("❌ recall_file_location() failed")
            return False

        # Verify knowledge table exists
        rag.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge'")
        if rag.cursor.fetchone():
            print("✅ knowledge table exists")
        else:
            print("❌ knowledge table missing")
            return False

        print("✅ Test 1 PASSED\n")
        return True

    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_searxng_env_vars():
    """Test that SearXNG uses environment variables"""
    print("\n🧪 Test 2: SearXNG Environment Variables")
    print("─" * 50)

    try:
        # Test tools.py WebSearchTool
        from core.tools import WebSearchTool

        # Test default
        search_default = WebSearchTool()
        if search_default.searxng_url == "http://localhost:8888":
            print("✅ Default SearXNG URL: http://localhost:8888")
        else:
            print(f"❌ Unexpected default URL: {search_default.searxng_url}")
            return False

        # Test with environment variable
        os.environ["SEARXNG_URL"] = "http://custom:9999"
        search_custom = WebSearchTool()
        if search_custom.searxng_url == "http://custom:9999":
            print("✅ Custom SearXNG URL from env: http://custom:9999")
        else:
            print(f"❌ Env variable not working: {search_custom.searxng_url}")
            return False

        # Clean up
        del os.environ["SEARXNG_URL"]

        # Test search_agents.py
        from core.search_agents import SearchAgent

        os.environ["SEARXNG_URL"] = "http://agent-test:8080"
        agent = SearchAgent(agent_id="test", vllm_url="http://localhost:8001")
        if agent.searxng_url == "http://agent-test:8080":
            print("✅ SearchAgent uses SEARXNG_URL env")
        else:
            print(f"❌ SearchAgent not using env: {agent.searxng_url}")
            return False

        # Clean up
        del os.environ["SEARXNG_URL"]

        # Test council/searxng.py
        from core.council.searxng import SearXNGClient

        os.environ["SEARXNG_URL"] = "http://council-test:7777"
        client = SearXNGClient()
        if client.base_url == "http://council-test:7777":
            print("✅ SearXNGClient uses SEARXNG_URL env")
        else:
            print(f"❌ SearXNGClient not using env: {client.base_url}")
            return False

        # Clean up
        del os.environ["SEARXNG_URL"]

        print("✅ Test 2 PASSED\n")
        return True

    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_model_validation():
    """Test that model validation works at startup"""
    print("\n🧪 Test 3: Model Validation")
    print("─" * 50)

    try:
        from core.model_router import ModelRouter

        # Create router with validation
        router = ModelRouter(validate=True)

        # Check if validation warnings were collected
        warnings = router.get_validation_warnings()

        print(f"📊 Validation found {len(warnings)} warnings")

        if warnings:
            print("\n⚠️  Missing Models:")
            for warning in warnings[:5]:  # Show first 5
                print(f"   {warning}")

        # Check that validation method exists
        if hasattr(router, '_validate_configured_models'):
            print("✅ Model validation method exists")
        else:
            print("❌ Model validation method missing")
            return False

        # Check that suggestion method exists
        if hasattr(router, '_suggest_alternative'):
            print("✅ Alternative suggestion method exists")
        else:
            print("❌ Alternative suggestion method missing")
            return False

        print("✅ Test 3 PASSED\n")
        return True

    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_search_retry():
    """Test that search has retry logic"""
    print("\n🧪 Test 4: Web Search Retry Logic")
    print("─" * 50)

    try:
        from core.tools import WebSearchTool
        import inspect

        search = WebSearchTool()

        # Check that search method has retry parameter
        sig = inspect.signature(search.search)
        if 'retry' in sig.parameters:
            print("✅ search() method has retry parameter")
            default_retry = sig.parameters['retry'].default
            print(f"   Default retry count: {default_retry}")
        else:
            print("❌ search() method missing retry parameter")
            return False

        # Check for auto-start method
        if hasattr(search, '_ensure_searxng_running'):
            print("✅ Auto-start method exists")
        else:
            print("❌ Auto-start method missing")
            return False

        print("✅ Test 4 PASSED\n")
        return True

    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("  RYX AI - CRITICAL FIXES TEST SUITE")
    print("=" * 60)

    results = {
        "RAG Database": test_rag_database_schema(),
        "SearXNG Env Vars": test_searxng_env_vars(),
        "Model Validation": test_model_validation(),
        "Search Retry": test_search_retry(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} {status}")

    print("\n" + "─" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
