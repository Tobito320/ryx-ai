#!/usr/bin/env python3
"""
Manual test script to validate identified bugs
Run with: python3 test_bugs_manual.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.intent_parser import IntentParser

def test_bug(name, test_func):
    """Test wrapper with nice output"""
    try:
        result = test_func()
        status = "\033[1;32m✓ PASS\033[0m" if result else "\033[1;31m✗ FAIL\033[0m"
        print(f"{status} {name}")
        return result
    except AssertionError as e:
        print(f"\033[1;31m✗ FAIL\033[0m {name}")
        print(f"  AssertionError: {e}")
        return False
    except Exception as e:
        print(f"\033[1;33m⚠ ERROR\033[0m {name}")
        print(f"  {type(e).__name__}: {e}")
        return False

def main():
    print()
    print("\033[1;36m╭─────────────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  Intent Parser - Bug Validation Tests      │\033[0m")
    print("\033[1;36m╰─────────────────────────────────────────────╯\033[0m")
    print()

    parser = IntentParser()
    passed = 0
    failed = 0

    print("\033[1;33m1. Model Switch False Positives\033[0m")

    def test1():
        intent = parser.parse("use nvim to edit file")
        print(f"  Input: 'use nvim to edit file'")
        print(f"  Detected model_switch: {intent.model_switch}")
        print(f"  Expected: None (should not trigger)")
        return intent.model_switch is None

    if test_bug("  BUG #1: 'use nvim' triggers false positive", test1):
        passed += 1
    else:
        failed += 1

    def test2():
        intent = parser.parse("use the terminal for this")
        print(f"  Input: 'use the terminal for this'")
        print(f"  Detected model_switch: {intent.model_switch}")
        return intent.model_switch is None

    if test_bug("  'use terminal' should not trigger", test2):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;33m2. Implicit Locate Over-Triggering\033[0m")

    def test3():
        intent = parser.parse("I need config help")
        print(f"  Input: 'I need config help'")
        print(f"  Detected action: {intent.action}")
        print(f"  Expected: 'chat' (not 'locate')")
        return intent.action == 'chat'

    if test_bug("  BUG #2: 'I need config help' triggers locate", test3):
        passed += 1
    else:
        failed += 1

    def test4():
        intent = parser.parse("how do I change config")
        print(f"  Input: 'how do I change config'")
        print(f"  Detected action: {intent.action}")
        return intent.action == 'chat'

    if test_bug("  'how do I change config' should be chat", test4):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;33m3. Legitimate Cases (Should Work)\033[0m")

    def test5():
        intent = parser.parse("hyprland config")
        print(f"  Input: 'hyprland config'")
        print(f"  Detected action: {intent.action}")
        print(f"  Expected: 'locate'")
        return intent.action == 'locate'

    if test_bug("  ✓ 'hyprland config' should locate", test5):
        passed += 1
    else:
        failed += 1

    def test6():
        intent = parser.parse("open hyprland config")
        print(f"  Input: 'open hyprland config'")
        print(f"  Detected action: {intent.action}")
        print(f"  Expected: 'execute'")
        return intent.action == 'execute'

    if test_bug("  ✓ 'open config' should execute", test6):
        passed += 1
    else:
        failed += 1

    def test7():
        intent = parser.parse("switch to deepseek")
        print(f"  Input: 'switch to deepseek'")
        print(f"  Detected model_switch: {intent.model_switch}")
        print(f"  Expected: 'deepseek-coder:6.7b'")
        return intent.model_switch == "deepseek-coder:6.7b"

    if test_bug("  ✓ 'switch to deepseek' should work", test7):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;33m4. Conflicting Keywords\033[0m")

    def test8():
        intent = parser.parse("open look up hyprland")
        print(f"  Input: 'open look up hyprland'")
        print(f"  Detected action: {intent.action}")
        print(f"  Note: Has both 'open' (execute) and 'look up' (browse)")
        # First match wins (execute)
        return intent.action == 'execute'

    if test_bug("  'open look up' → execute (first match wins)", test8):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;33m5. Target Extraction\033[0m")

    def test9():
        intent = parser.parse("open my hyprland config")
        print(f"  Input: 'open my hyprland config'")
        print(f"  Extracted target: '{intent.target}'")
        has_hyprland = 'hyprland' in intent.target.lower() if intent.target else False
        has_config = 'config' in intent.target.lower() if intent.target else False
        return has_hyprland and has_config

    if test_bug("  'my hyprland config' → extracts correctly", test9):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;33m6. Edge Cases\033[0m")

    def test10():
        intent = parser.parse("hello")
        print(f"  Input: 'hello'")
        print(f"  Detected action: {intent.action}")
        # Should be chat, but ideally handled before AI query
        return intent.action == 'chat'

    if test_bug("  'hello' → chat (but not instant)", test10):
        passed += 1
    else:
        failed += 1

    def test11():
        intent = parser.parse("")
        print(f"  Input: '' (empty)")
        print(f"  Detected action: {intent.action}")
        return intent.action == 'chat'

    if test_bug("  Empty prompt → chat", test11):
        passed += 1
    else:
        failed += 1

    print()
    print("\033[1;36m" + "─" * 45 + "\033[0m")
    print(f"\033[1;37mResults:\033[0m {passed} passed, {failed} failed out of {passed + failed} tests")
    print()

    # Summary of bugs
    print("\033[1;33mConfirmed Bugs:\033[0m")
    print("  1. Model switch false positives on 'use <program>'")
    print("  2. Implicit locate over-triggers on conversational prompts")
    print("  3. Greetings query AI instead of instant response")
    print("  4. Conflicting keywords use first-match (no disambiguation)")
    print()

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
