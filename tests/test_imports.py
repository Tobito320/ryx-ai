#!/usr/bin/env python3
"""
Test all Python module imports
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.home() / "ryx-ai"))

def test_imports():
    results = []

    # Test core modules
    try:
        from core.ai_engine import AIEngine, ResponseFormatter
        results.append(("core.ai_engine", "PASS", "AIEngine, ResponseFormatter imported"))
    except Exception as e:
        results.append(("core.ai_engine", "FAIL", str(e)))

    try:
        from core.rag_system import RAGSystem, FileFinder
        results.append(("core.rag_system", "PASS", "RAGSystem, FileFinder imported"))
    except Exception as e:
        results.append(("core.rag_system", "FAIL", str(e)))

    try:
        from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm
        results.append(("core.permissions", "PASS", "PermissionManager, CommandExecutor, InteractiveConfirm imported"))
    except Exception as e:
        results.append(("core.permissions", "FAIL", str(e)))

    try:
        from core.self_improve import SelfImprover
        results.append(("core.self_improve", "PASS", "SelfImprover imported"))
    except Exception as e:
        results.append(("core.self_improve", "FAIL", str(e)))

    # Test modes
    try:
        from modes.cli_mode import CLIMode
        results.append(("modes.cli_mode", "PASS", "CLIMode imported"))
    except Exception as e:
        results.append(("modes.cli_mode", "FAIL", str(e)))

    try:
        from modes.session_mode import SessionMode
        results.append(("modes.session_mode", "PASS", "SessionMode imported"))
    except Exception as e:
        results.append(("modes.session_mode", "FAIL", str(e)))

    # Test tools
    try:
        from tools.scraper import WebScraper
        results.append(("tools.scraper", "PASS", "WebScraper imported"))
    except Exception as e:
        results.append(("tools.scraper", "FAIL", str(e)))

    try:
        from tools.browser import WebBrowser
        results.append(("tools.browser", "PASS", "WebBrowser imported"))
    except Exception as e:
        results.append(("tools.browser", "FAIL", str(e)))

    try:
        from tools.council import Council
        results.append(("tools.council", "PASS", "Council imported"))
    except Exception as e:
        results.append(("tools.council", "FAIL", str(e)))

    return results

if __name__ == "__main__":
    print("Testing Python module imports...\n")
    results = test_imports()

    pass_count = sum(1 for r in results if r[1] == "PASS")
    fail_count = sum(1 for r in results if r[1] == "FAIL")

    for module, status, message in results:
        print(f"[{status}] {module}: {message}")

    print(f"\nSummary: {pass_count} PASS, {fail_count} FAIL")
    sys.exit(0 if fail_count == 0 else 1)
