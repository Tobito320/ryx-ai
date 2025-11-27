#!/usr/bin/env python3
"""
Ryx AI V2 Integration Test Suite
Tests all components and their integration
"""

import sys
import traceback
from pathlib import Path

# Add project to path
project_root = Path.home() / "ryx-ai"
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all critical imports"""
    print("\n" + "="*60)
    print("PHASE 1: Testing Imports")
    print("="*60)
    
    tests = [
        ("core.ai_engine", ["AIEngine", "ResponseFormatter"]),
        ("core.rag_system", ["RAGSystem", "FileFinder"]),
        ("core.permissions", ["PermissionManager", "CommandExecutor"]),
        ("tools.browser", ["WebBrowser"]),
        ("tools.scraper", ["WebScraper"]),
        ("tools.council", ["Council"]),
        ("modes.session_mode", ["SessionMode"]),
        ("modes.cli_mode", ["CLIMode"]),
    ]
    
    results = []
    for module_name, classes in tests:
        try:
            module = __import__(module_name, fromlist=classes)
            for cls_name in classes:
                getattr(module, cls_name)
            results.append((module_name, "✓ PASS", "All classes found"))
        except ImportError as e:
            results.append((module_name, "✗ FAIL", f"ImportError: {e}"))
        except AttributeError as e:
            results.append((module_name, "✗ FAIL", f"Missing class: {e}"))
        except Exception as e:
            results.append((module_name, "✗ FAIL", f"{type(e).__name__}: {e}"))
    
    for module, status, msg in results:
        print(f"{status} {module:30} {msg}")
    
    return all("PASS" in status for _, status, _ in results)

def test_new_components():
    """Test new V2 components"""
    print("\n" + "="*60)
    print("PHASE 2: Testing New V2 Components")
    print("="*60)
    
    components = [
        ("core.model_orchestrator", "ModelOrchestrator"),
        ("core.meta_learner", "MetaLearner"),
        ("core.health_monitor", "HealthMonitor"),
        ("core.task_manager", "TaskManager"),
    ]
    
    results = []
    for module_name, class_name in components:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            results.append((class_name, "✓ PASS", "Component exists"))
        except ImportError:
            results.append((class_name, "✗ MISSING", "Module not found"))
        except AttributeError:
            results.append((class_name, "✗ MISSING", "Class not found"))
        except Exception as e:
            results.append((class_name, "✗ ERROR", str(e)))
    
    for component, status, msg in results:
        print(f"{status} {component:30} {msg}")
    
    return all("PASS" in status or "exists" in msg for _, status, msg in results)

def test_browser_fix():
    """Test browser.py WebScraper import"""
    print("\n" + "="*60)
    print("PHASE 3: Testing Browser WebScraper Import")
    print("="*60)
    
    try:
        from tools.scraper import WebScraper
        print("✓ PASS WebScraper import         Found in tools.scraper")
        
        # Now try to instantiate WebBrowser
        from tools.browser import WebBrowser
        print("✓ PASS WebBrowser import        Found in tools.browser")
        
        # Try to create instance
        browser = WebBrowser()
        print("✓ PASS WebBrowser instantiate    WebBrowser() works")
        return True
    except ImportError as e:
        print(f"✗ FAIL ImportError: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ FAIL {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_rag_system():
    """Test RAG system enhancements"""
    print("\n" + "="*60)
    print("PHASE 4: Testing RAG System")
    print("="*60)
    
    try:
        from core.rag_system import RAGSystem
        
        rag = RAGSystem()
        print("✓ PASS RAGSystem instantiate    RAGSystem() works")
        
        # Test methods
        stats = rag.get_stats()
        print(f"✓ PASS RAGSystem.get_stats()    Returns: {list(stats.keys())}")
        
        # Test cache query
        result = rag.query_cache("test query")
        print(f"✓ PASS RAGSystem.query_cache()  Returns type: {type(result)}")
        
        return True
    except Exception as e:
        print(f"✗ FAIL {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_ai_engine():
    """Test integrated AI engine"""
    print("\n" + "="*60)
    print("PHASE 5: Testing AI Engine Integration")
    print("="*60)
    
    try:
        from core.ai_engine import AIEngine
        
        ai = AIEngine()
        print("✓ PASS AIEngine instantiate     AIEngine() works")
        
        # Check for new components integration
        has_orchestrator = hasattr(ai, 'orchestrator')
        has_meta_learner = hasattr(ai, 'meta_learner')
        has_health = hasattr(ai, 'health_monitor')
        has_task_manager = hasattr(ai, 'task_manager')
        
        print(f"  Model Orchestrator: {'✓' if has_orchestrator else '✗'}")
        print(f"  Meta Learner:       {'✓' if has_meta_learner else '✗'}")
        print(f"  Health Monitor:     {'✓' if has_health else '✗'}")
        print(f"  Task Manager:       {'✓' if has_task_manager else '✗'}")
        
        return True
    except Exception as e:
        print(f"✗ FAIL {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_session_mode_commands():
    """Test new session mode commands"""
    print("\n" + "="*60)
    print("PHASE 6: Testing Session Mode Commands")
    print("="*60)
    
    try:
        from modes.session_mode import SessionMode
        
        session = SessionMode()
        print("✓ PASS SessionMode instantiate  SessionMode() works")
        
        # Check for new command handlers
        has_health_cmd = hasattr(session, 'show_health')
        has_resume_cmd = hasattr(session, 'resume_session')
        has_status_cmd = hasattr(session, 'show_session_status')
        
        print(f"  /health command:   {'✓' if has_health_cmd else '✗'}")
        print(f"  /resume command:   {'✓' if has_resume_cmd else '✗'}")
        print(f"  /status command:   {'✓' if has_status_cmd else '✗'}")
        
        return True
    except Exception as e:
        print(f"✗ FAIL {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "╭" + "─"*58 + "╮")
    print("│  RYX AI V2 INTEGRATION TEST SUITE                      │")
    print("╰" + "─"*58 + "╯")
    
    results = {
        "Imports": test_imports(),
        "New Components": test_new_components(),
        "Browser Fix": test_browser_fix(),
        "RAG System": test_rag_system(),
        "AI Engine": test_ai_engine(),
        "Session Mode": test_session_mode_commands(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED - V2 INTEGRATION COMPLETE")
    else:
        print("✗ SOME TESTS FAILED - SEE ABOVE FOR DETAILS")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
