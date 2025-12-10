"""
Ryx AI - Benchmark System

Measures Ryx's actual performance across key metrics.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.llm_backend import get_backend
from core.ryx_brain import get_brain, Intent

# Test cases: (prompt, expected_intent)
INTENT_TEST_CASES = [
    ("open youtube", Intent.OPEN_URL),
    ("open google", Intent.OPEN_URL),
    ("open github", Intent.OPEN_URL),
    ("open my hyprland config", Intent.OPEN_FILE),
    ("open ~/.bashrc", Intent.OPEN_FILE),
    ("open the neovim config", Intent.OPEN_FILE),
    ("what time is it", Intent.GET_INFO),
    ("what's the date", Intent.GET_INFO),
    ("how much RAM do I have", Intent.GET_INFO),
    ("hi", Intent.CHAT),
    ("hello", Intent.CHAT),
    ("how are you", Intent.CHAT),
    ("thanks", Intent.CHAT),
    ("create a python script that prints hello", Intent.CODE_TASK),
    ("write a function to calculate fibonacci", Intent.CODE_TASK),
    ("fix the bug in main.py", Intent.CODE_TASK),
    ("refactor this code", Intent.CODE_TASK),
    ("add error handling to the login function", Intent.CODE_TASK),
    ("search for python tutorials", Intent.SEARCH_WEB),
    ("google arch linux installation", Intent.SEARCH_WEB),
    ("find information about rust programming", Intent.SEARCH_WEB),
    ("run ls -la", Intent.RUN_COMMAND),
    ("execute git status", Intent.RUN_COMMAND),
    ("show me the current directory", Intent.RUN_COMMAND),
]


@dataclass
class BenchmarkResult:
    timestamp: str
    intent_accuracy: float
    intent_correct: int
    intent_total: int
    failed_tests: list
    overall_score: float


def run_benchmark() -> BenchmarkResult:
    """Run the benchmark and return results"""
    print("=" * 60)
    print("RUNNING RYX BENCHMARK")
    print("=" * 60)
    
    backend = get_backend()
    brain = get_brain(backend)
    
    print("\n[1/1] Testing Intent Detection...")
    correct = 0
    failed = []
    
    for prompt, expected in INTENT_TEST_CASES:
        plan = brain.understand(prompt)
        if plan.intent == expected:
            print(f"  ✓ '{prompt[:30]}' → {plan.intent.value}")
            correct += 1
        else:
            print(f"  ✗ '{prompt[:30]}' → {plan.intent.value} (expected: {expected.value})")
            failed.append({
                "prompt": prompt,
                "expected": expected.value,
                "got": plan.intent.value
            })
    
    total = len(INTENT_TEST_CASES)
    accuracy = correct / total * 100
    
    # Score: 70% intent accuracy weight
    score = accuracy * 0.7 + 30  # Base 30 for other factors
    
    result = BenchmarkResult(
        timestamp=datetime.now().isoformat(),
        intent_accuracy=accuracy,
        intent_correct=correct,
        intent_total=total,
        failed_tests=failed,
        overall_score=score
    )
    
    # Save result
    data_dir = PROJECT_ROOT / "data" / "benchmarks"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = data_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(asdict(result), f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"  Intent Accuracy:   {accuracy:.1f}% ({correct}/{total})")
    print(f"  OVERALL SCORE:     {score:.1f}/100")
    print("=" * 60)
    
    if failed:
        print("\nFailed tests:")
        for f in failed:
            print(f"  - '{f['prompt']}': got {f['got']}, expected {f['expected']}")
    
    return result


if __name__ == "__main__":
    print("Using Ollama backend")
    run_benchmark()
