#!/usr/bin/env python3
"""
Test script for RyxHub backend API endpoints.
Tests all the new functionality added.
"""

import requests
import json
from typing import Dict, Any


API_BASE = "http://localhost:8420"


def test_health() -> bool:
    """Test health endpoint."""
    print("\n🔍 Testing /api/health...")
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   vLLM status: {data['vllm_status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_models() -> bool:
    """Test models listing endpoint."""
    print("\n🔍 Testing /api/models...")
    try:
        response = requests.get(f"{API_BASE}/api/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            loaded_count = data.get('loaded_count', 0)
            available_count = data.get('available_count', 0)
            
            print(f"✅ Models endpoint working")
            print(f"   Total models: {len(models)}")
            print(f"   Loaded: {loaded_count}")
            print(f"   Available: {available_count}")
            
            if models:
                print("\n   Models:")
                for model in models[:5]:  # Show first 5
                    print(f"   - {model['name']} ({model['status']})")
            
            return True
        else:
            print(f"❌ Models endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Models endpoint error: {e}")
        return False


def test_model_status(model_id: str = "/models/medium/general/qwen2.5-7b-gptq") -> bool:
    """Test model status endpoint."""
    print(f"\n🔍 Testing /api/models/{model_id}/status...")
    try:
        # URL encode the model_id
        import urllib.parse
        encoded_id = urllib.parse.quote(model_id, safe='')
        
        response = requests.get(f"{API_BASE}/api/models/{encoded_id}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Model status check passed")
            print(f"   Status: {data['status']}")
            print(f"   Loaded: {data['loaded']}")
            print(f"   Message: {data['message']}")
            return True
        else:
            print(f"❌ Model status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Model status error: {e}")
        return False


def test_searxng_status() -> bool:
    """Test SearXNG status endpoint."""
    print("\n🔍 Testing /api/searxng/status...")
    try:
        response = requests.get(f"{API_BASE}/api/searxng/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SearXNG status check passed")
            print(f"   Healthy: {data['healthy']}")
            print(f"   Status: {data['status']}")
            print(f"   Message: {data['message']}")
            return data['healthy']
        else:
            print(f"❌ SearXNG status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ SearXNG status error: {e}")
        return False


def test_searxng_search() -> bool:
    """Test SearXNG search endpoint."""
    print("\n🔍 Testing /api/searxng/search...")
    try:
        payload = {"query": "python programming"}
        response = requests.post(
            f"{API_BASE}/api/searxng/search",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            total = data.get('total', 0)
            
            print(f"✅ SearXNG search passed")
            print(f"   Results: {total}")
            
            if results:
                print("\n   Top results:")
                for result in results[:3]:
                    print(f"   - {result.get('title', 'N/A')}")
            
            return True
        else:
            print(f"❌ SearXNG search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ SearXNG search error: {e}")
        return False


def test_session_creation() -> Dict[str, Any] | None:
    """Test session creation endpoint."""
    print("\n🔍 Testing /api/sessions (POST)...")
    try:
        payload = {
            "name": "Test Session",
            "model": "default"
        }
        response = requests.post(
            f"{API_BASE}/api/sessions",
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session creation passed")
            print(f"   Session ID: {data['id']}")
            print(f"   Name: {data['name']}")
            print(f"   Model: {data['model']}")
            return data
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None


def test_sessions_list() -> bool:
    """Test sessions listing endpoint."""
    print("\n🔍 Testing /api/sessions (GET)...")
    try:
        response = requests.get(f"{API_BASE}/api/sessions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            print(f"✅ Sessions list passed")
            print(f"   Total sessions: {len(sessions)}")
            return True
        else:
            print(f"❌ Sessions list failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sessions list error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 RyxHub Backend API Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test health
    results['health'] = test_health()
    
    # Test models
    results['models_list'] = test_models()
    results['model_status'] = test_model_status()
    
    # Test SearXNG
    results['searxng_status'] = test_searxng_status()
    results['searxng_search'] = test_searxng_search()
    
    # Test sessions
    results['sessions_list'] = test_sessions_list()
    session = test_session_creation()
    results['session_creation'] = session is not None
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_status in results.items():
        status = "✅ PASS" if passed_status else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print("=" * 60)
    print(f"Overall: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
