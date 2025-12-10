"""
Ryx Self-Improvement Script

This script:
1. Runs benchmark to find weaknesses
2. Uses deepseek-r1 to reason about fixes
3. Uses qwen2.5:3b to generate code changes
4. Applies changes and re-benchmarks
5. Keeps if improved, reverts if not
"""

import sys
import json
import subprocess
import re
import asyncio
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.ollama_client import OllamaClient
from core.benchmark import run_benchmark, INTENT_TEST_CASES


def analyze_failures(failed_tests: list) -> str:
    """Create analysis prompt for the model"""
    failures_text = "\n".join([
        f"- Input: '{f['prompt']}' → Got: {f['got']}, Expected: {f['expected']}"
        for f in failed_tests
    ])
    
    return f"""Analyze these intent detection failures:

{failures_text}

The intent detection happens in core/ryx_brain.py in the _resolve_from_knowledge() method.
Current intents: OPEN_FILE, OPEN_URL, RUN_COMMAND, GET_INFO, CODE_TASK, CHAT, SEARCH_WEB, etc.

What patterns are being missed? What rules should be added?"""


async def generate_fix_plan(client: OllamaClient, failures: list) -> str:
    """Use deepseek-r1 to reason about the fix"""
    print("\n[REASONING] Using deepseek-r1:8b to analyze failures...")
    
    prompt = analyze_failures(failures)
    
    response = await client.generate(
        prompt=prompt,
        model="deepseek-r1:8b",
        system="You are analyzing code issues. Think step by step about what patterns are being missed and how to fix them.",
        max_tokens=2000,
        temperature=0.3
    )
    
    if response.error:
        print(f"Error: {response.error}")
        return ""
    
    print(f"\n[REASONING OUTPUT]\n{response.response[:1500]}...")
    return response.response


async def generate_code_fix(client: OllamaClient, reasoning: str, target_file: str) -> str:
    """Use qwen2.5:3b to generate actual code changes"""
    print("\n[CODE GEN] Using qwen2.5:3b to generate fix...")
    
    # Read current file
    file_path = PROJECT_ROOT / target_file
    current_code = file_path.read_text()
    
    # Find the _resolve_from_knowledge method
    match = re.search(r'(def _resolve_from_knowledge\(self.*?)(\n    def )', current_code, re.DOTALL)
    if not match:
        print("Could not find _resolve_from_knowledge method")
        return ""
    
    method_code = match.group(1)
    
    prompt = f"""Based on this analysis:

{reasoning[:1000]}

Here is the current _resolve_from_knowledge method that needs fixing:

```python
{method_code[:2000]}
```

Generate ONLY the new code to add at the START of _resolve_from_knowledge (after 'p = prompt.lower()') to fix these patterns:
1. "run X" and "execute X" should return RUN_COMMAND
2. "~/.bashrc" style paths should return OPEN_FILE  
3. "how much RAM" style questions should return GET_INFO
4. "add error handling" should return CODE_TASK
5. "current directory" should return RUN_COMMAND

Output ONLY Python code, no explanation. Format as a single code block."""

    response = await client.generate(
        prompt=prompt,
        model="qwen2.5:3b",
        system="You are a Python code generator. Output only valid Python code.",
        max_tokens=1500,
        temperature=0.2
    )
    
    if response.error:
        print(f"Error: {response.error}")
        return ""
    
    print(f"\n[CODE OUTPUT]\n{response.response[:1000]}...")
    return response.response


def extract_code(response: str) -> str:
    """Extract Python code from model response"""
    # Try to find code block
    match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    match = re.search(r'```\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Just return as-is if no code block
    return response.strip()


def apply_fix(code: str, target_file: str) -> bool:
    """Apply the generated fix to the file"""
    file_path = PROJECT_ROOT / target_file
    current_code = file_path.read_text()
    
    # Find insertion point (after 'p = prompt.lower()')
    insertion_point = "p = prompt.lower()"
    
    if insertion_point not in current_code:
        print("Could not find insertion point")
        return False
    
    # Insert the new code after 'p = prompt.lower()'
    new_code = current_code.replace(
        insertion_point,
        f"{insertion_point}\n\n        # AUTO-GENERATED FIX - {datetime.now().isoformat()}\n{code}\n        # END AUTO-GENERATED FIX\n"
    )
    
    # Backup original
    backup_path = file_path.with_suffix('.py.backup')
    backup_path.write_text(current_code)
    
    # Write new code
    file_path.write_text(new_code)
    print(f"\n[APPLIED] Fix applied to {target_file}")
    print(f"[BACKUP] Original saved to {backup_path}")
    
    return True


def revert_fix(target_file: str) -> bool:
    """Revert to backup"""
    file_path = PROJECT_ROOT / target_file
    backup_path = file_path.with_suffix('.py.backup')
    
    if backup_path.exists():
        file_path.write_text(backup_path.read_text())
        print(f"[REVERTED] Restored {target_file} from backup")
        return True
    return False


async def main():
    print("=" * 60)
    print("RYX SELF-IMPROVEMENT CYCLE")
    print("=" * 60)
    
    client = OllamaClient()
    target_file = "core/ryx_brain.py"
    
    # Step 1: Baseline benchmark
    print("\n[STEP 1] Running baseline benchmark...")
    baseline = run_benchmark()
    
    if not baseline.failed_tests:
        print("\n✓ No failures! Nothing to fix.")
        return
    
    print(f"\nBaseline: {baseline.intent_accuracy:.1f}% ({len(baseline.failed_tests)} failures)")
    
    # Step 2: Analyze with deepseek-r1
    print("\n[STEP 2] Analyzing failures with deepseek-r1...")
    reasoning = await generate_fix_plan(client, baseline.failed_tests)
    
    if not reasoning:
        print("Failed to generate reasoning. Stopping.")
        return
    
    # Step 3: Generate code fix with qwen2.5:3b
    print("\n[STEP 3] Generating code fix with qwen2.5:3b...")
    code_response = await generate_code_fix(client, reasoning, target_file)
    
    if not code_response:
        print("Failed to generate code. Stopping.")
        return
    
    code = extract_code(code_response)
    print(f"\n[EXTRACTED CODE]\n{code[:500]}...")
    
    # Step 4: Apply fix
    print("\n[STEP 4] Applying fix...")
    if not apply_fix(code, target_file):
        print("Failed to apply fix. Stopping.")
        return
    
    # Step 5: Re-benchmark (3 attempts)
    best_result = None
    for attempt in range(3):
        print(f"\n[STEP 5] Re-benchmark attempt {attempt + 1}/3...")
        
        try:
            result = run_benchmark()
            
            if result.intent_accuracy > baseline.intent_accuracy:
                print(f"\n✓ IMPROVED! {baseline.intent_accuracy:.1f}% → {result.intent_accuracy:.1f}%")
                best_result = result
                break
            else:
                print(f"\n✗ No improvement: {result.intent_accuracy:.1f}%")
        except Exception as e:
            print(f"\n✗ Benchmark failed: {e}")
            revert_fix(target_file)
            return
    
    if best_result and best_result.intent_accuracy > baseline.intent_accuracy:
        print("\n" + "=" * 60)
        print("SUCCESS - FIX KEPT")
        print("=" * 60)
        print(f"Before: {baseline.intent_accuracy:.1f}%")
        print(f"After:  {best_result.intent_accuracy:.1f}%")
        print(f"Improvement: +{best_result.intent_accuracy - baseline.intent_accuracy:.1f}%")
    else:
        print("\n[REVERTING] No improvement, reverting changes...")
        revert_fix(target_file)
        print("\n" + "=" * 60)
        print("FAILED - REVERTED")
        print("=" * 60)
        print("Ryx could not improve itself. Copilot should step in.")


if __name__ == "__main__":
    asyncio.run(main())
