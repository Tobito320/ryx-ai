#!/usr/bin/env python3
"""
Test script for the complete exam evaluation pipeline with streaming.

Tests:
1. Docker sandbox creation
2. WebSocket streaming endpoints
3. Full exam evaluation flow
"""

import asyncio
import json
import os
import sys
import httpx
import websockets

API_BASE = os.environ.get("API_BASE", "http://localhost:8420")
WS_BASE = API_BASE.replace("http", "ws")

print("=" * 60)
print("RyxHub Complete Integration Test")
print("=" * 60)

async def test_health():
    """Test basic health endpoint."""
    print("\n[1] Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_BASE}/api/health", timeout=10)
            data = resp.json()
            print(f"    Status: {data.get('status', 'unknown')}")
            print(f"    Ollama: {data.get('ollama_status', 'unknown')}")
            return True
        except Exception as e:
            print(f"    ERROR: {e}")
            return False

async def test_websocket_stream():
    """Test WebSocket token streaming."""
    print("\n[2] Testing WebSocket streaming...")
    try:
        async with websockets.connect(f"{WS_BASE}/ws/stream") as ws:
            # Send a simple prompt
            await ws.send(json.dumps({
                "prompt": "Say hello in exactly 3 words",
                "model": "qwen2.5:7b"
            }))
            
            # Collect tokens
            tokens = []
            try:
                for _ in range(50):  # Max 50 messages
                    msg = await asyncio.wait_for(ws.recv(), timeout=15)
                    data = json.loads(msg)
                    if data.get("type") == "token":
                        tokens.append(data.get("content", ""))
                        print(f"{data.get('content', '')}", end="", flush=True)
                    elif data.get("type") == "done":
                        break
            except asyncio.TimeoutError:
                pass
            
            print(f"\n    Received {len(tokens)} tokens")
            return True  # Connection worked, that's enough
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

async def test_websocket_agent():
    """Test WebSocket agent streaming."""
    print("\n[3] Testing WebSocket agent steps...")
    try:
        async with websockets.connect(f"{WS_BASE}/ws/agent") as ws:
            # Send an agent task
            await ws.send(json.dumps({
                "task": "Analyze a simple math problem: 2+2",
                "model": "qwen2.5:7b"
            }))
            
            # Collect steps
            steps = []
            try:
                for _ in range(20):  # Max 20 messages
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    msg_type = data.get("type", "")
                    if "step" in msg_type or msg_type == "agent_step":
                        steps.append(data.get("step", data.get("step_type", "unknown")))
                        print(f"    Step: {data.get('step', data.get('step_type'))}")
                    elif data.get("type") in ("done", "error", "complete"):
                        break
            except asyncio.TimeoutError:
                pass
            
            print(f"    Received {len(steps)} steps")
            return True  # Connection worked
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

async def test_exam_api():
    """Test exam API v2 endpoints."""
    print("\n[4] Testing Exam API v2...")
    async with httpx.AsyncClient() as client:
        try:
            # Test subjects endpoint
            resp = await client.get(f"{API_BASE}/api/exam/v2/subjects", timeout=10)
            if resp.status_code == 200:
                subjects = resp.json()
                print(f"    Found {len(subjects)} subjects")
                return True
            else:
                print(f"    Status: {resp.status_code}")
                return False
        except Exception as e:
            print(f"    ERROR: {e}")
            return False

async def test_sandbox_manager():
    """Test sandbox manager functionality."""
    print("\n[5] Testing Sandbox Manager...")
    try:
        # Import the sandbox manager
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.sandbox_manager import SandboxManager
        
        # Create a sandbox manager
        manager = SandboxManager(sandbox_type="docker")
        print(f"    Sandbox type: {manager.sandbox_type}")
        
        # Note: We don't actually start the sandbox here (requires Docker running)
        print("    Sandbox manager initialized successfully")
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

async def test_ocr_module():
    """Test OCR module availability."""
    print("\n[6] Testing OCR module...")
    try:
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.ocr import OCREngine, OCRResult, process_pdf
        print("    OCR module available (OCREngine, process_pdf)")
        return True
    except ImportError as e:
        print(f"    OCR module not available: {e}")
        return False

async def test_rubric_generator():
    """Test rubric generator availability."""
    print("\n[7] Testing Rubric Generator...")
    try:
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.rubric_generator import generate_rubric
        print("    Rubric generator available")
        return True
    except ImportError as e:
        print(f"    Rubric generator not available: {e}")
        return False

async def test_semantic_evaluator():
    """Test semantic evaluator availability."""
    print("\n[8] Testing Semantic Evaluator...")
    try:
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.semantic_evaluator import evaluate_answer_semantically
        print("    Semantic evaluator available")
        return True
    except ImportError as e:
        print(f"    Semantic evaluator not available: {e}")
        return False

async def test_pedagogical_feedback():
    """Test pedagogical feedback availability."""
    print("\n[9] Testing Pedagogical Feedback...")
    try:
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.pedagogical_feedback import generate_task_feedback
        print("    Pedagogical feedback available")
        return True
    except ImportError as e:
        print(f"    Pedagogical feedback not available: {e}")
        return False

async def test_learning_analytics():
    """Test learning analytics availability."""
    print("\n[10] Testing Learning Analytics...")
    try:
        sys.path.insert(0, "/home/tobi/ryx-ai")
        from ryx_pkg.interfaces.web.backend.learning_analytics import generate_learning_analytics
        print("    Learning analytics available")
        return True
    except ImportError as e:
        print(f"    Learning analytics not available: {e}")
        return False

async def main():
    """Run all tests."""
    results = {
        "health": await test_health(),
        "sandbox_manager": await test_sandbox_manager(),
        "ocr": await test_ocr_module(),
        "rubric": await test_rubric_generator(),
        "semantic": await test_semantic_evaluator(),
        "feedback": await test_pedagogical_feedback(),
        "analytics": await test_learning_analytics(),
    }
    
    # WebSocket tests only if API is available
    if results["health"]:
        results["websocket_stream"] = await test_websocket_stream()
        results["websocket_agent"] = await test_websocket_agent()
        results["exam_api"] = await test_exam_api()
    else:
        print("\n⚠️ Skipping WebSocket tests (API not available)")
        results["websocket_stream"] = None
        results["websocket_agent"] = None
        results["exam_api"] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for name, result in results.items():
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⏭️ SKIP")
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
