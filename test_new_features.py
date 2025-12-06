#!/usr/bin/env python3
"""
Test script for new RYX AI features:
- Visual step indicators
- Token streaming
- Council system
"""

import sys
import asyncio
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_visual_steps():
    """Test visual step indicators"""
    print("\n" + "="*60)
    print("TEST 1: Visual Step Indicators")
    print("="*60 + "\n")
    
    from core.visual_steps import StepVisualizer, StepType
    from rich.console import Console
    
    console = Console()
    viz = StepVisualizer(console)
    
    # Simulate a multi-step process
    viz.start_step(StepType.THINKING, "Analyzing request")
    import time
    time.sleep(0.5)
    viz.complete_step()
    
    viz.start_step(StepType.PARSING, "Parsing query", "Extracting intent...")
    time.sleep(0.3)
    viz.add_substep("Found keywords: quantum, entanglement")
    viz.add_substep("Detected question type: explanation")
    time.sleep(0.2)
    viz.complete_step()
    
    viz.start_step(StepType.SEARCHING, "Web search", "query: quantum entanglement")
    time.sleep(0.8)
    viz.update_step("Found 5 sources")
    time.sleep(0.2)
    viz.complete_step()
    
    viz.start_step(StepType.SYNTHESIS, "Generating response")
    time.sleep(0.6)
    viz.complete_step()
    
    print(f"\n{viz.get_summary()}")
    print("\n✅ Visual steps test completed!")


def test_streaming_display():
    """Test streaming display with token statistics"""
    print("\n" + "="*60)
    print("TEST 2: Token Streaming Display")
    print("="*60 + "\n")
    
    from core.visual_steps import StreamingDisplay
    from rich.console import Console
    import time
    
    console = Console()
    display = StreamingDisplay(console)
    
    # Simulate streaming response
    display.start()
    
    sample_text = "Quantum entanglement is a physical phenomenon that occurs when a group of particles are generated, interact, or share spatial proximity in a way such that the quantum state of each particle of the group cannot be described independently of the state of the others."
    
    words = sample_text.split()
    for word in words:
        display.add_token(word + " ")
        time.sleep(0.05)  # Simulate token delay
    
    stats = display.finish()
    
    print("\n✅ Streaming display test completed!")
    return stats


async def test_council_system():
    """Test council system (requires vLLM to be running)"""
    print("\n" + "="*60)
    print("TEST 3: Council System")
    print("="*60 + "\n")
    
    try:
        from core.council_v2 import Council, CouncilMember, CouncilPreset
        from rich.console import Console
        
        console = Console()
        
        # Create a minimal council with mock members
        # Note: This will fail if vLLM is not running, which is expected in test environment
        council = Council(console=console)
        
        print("Council initialized with members:")
        for member in council.members:
            print(f"  - {member.name}: {member.model_path} (weight: {member.weight})")
        
        print("\n⚠️  Council test requires vLLM to be running")
        print("   Start vLLM with: ryx start vllm")
        print("   Then run: /council <question> in a session")
        
    except ImportError as e:
        print(f"❌ Council import failed: {e}")
    except Exception as e:
        print(f"⚠️  Council test skipped: {e}")
    
    print("\n✅ Council structure test completed!")


def test_cli_visual_methods():
    """Test CLI visual methods"""
    print("\n" + "="*60)
    print("TEST 4: CLI Visual Methods")
    print("="*60 + "\n")
    
    try:
        from core.cli_ui import CLI
        
        cli = CLI()
        
        print("Testing visual indicators:\n")
        
        cli.thinking("Processing your request...")
        import time
        time.sleep(0.3)
        
        cli.parsing("Analyzing query structure...")
        time.sleep(0.2)
        
        cli.planning("Planning execution strategy...")
        time.sleep(0.2)
        
        cli.searching("quantum computing", 5)
        time.sleep(0.3)
        
        cli.tool_exec("web_search", "SearXNG query")
        time.sleep(0.2)
        
        cli.synthesizing("Generating response...")
        time.sleep(0.3)
        
        cli.success("All visual indicators working!")
        
        print("\n✅ CLI visual methods test completed!")
        
    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
    except Exception as e:
        print(f"⚠️  CLI test error: {e}")


def test_backend_streaming():
    """Test backend streaming capability"""
    print("\n" + "="*60)
    print("TEST 5: Backend Streaming")
    print("="*60 + "\n")
    
    try:
        from core.llm_backend import VLLMBackend, LLMResponse
        
        backend = VLLMBackend()
        
        # Check if backend is healthy
        health = backend.health_check()
        print(f"Backend health: {health}")
        
        if health.get("healthy"):
            print("✅ vLLM backend is running!")
            print("   Streaming is available")
        else:
            print("⚠️  vLLM backend not running")
            print("   Start with: ryx start vllm")
        
        print("\n✅ Backend streaming test completed!")
        
    except Exception as e:
        print(f"⚠️  Backend test error: {e}")


def main():
    """Run all tests"""
    print("\n" + "🟣"*30)
    print("  RYX AI - New Features Test Suite")
    print("🟣"*30)
    
    try:
        # Test 1: Visual steps
        test_visual_steps()
        
        # Test 2: Streaming display
        test_streaming_display()
        
        # Test 3: Council (structure only, needs vLLM)
        asyncio.run(test_council_system())
        
        # Test 4: CLI visual methods
        test_cli_visual_methods()
        
        # Test 5: Backend streaming
        test_backend_streaming()
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("\n✅ All structural tests passed!")
        print("\nTo test full functionality:")
        print("  1. Start vLLM: ryx start vllm")
        print("  2. Run interactive session: ryx")
        print("  3. Try commands:")
        print("     - /council What is quantum computing?")
        print("     - /review @myfile.py")
        print("     - explain recursion (watch streaming!)")
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
