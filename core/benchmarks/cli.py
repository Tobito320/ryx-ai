#!/usr/bin/env python3
"""
Ryx AI - Benchmark CLI

Command-line interface for running benchmarks.

Usage:
    ryx ::benchmark list              # List available benchmarks
    ryx ::benchmark run [name]        # Run a benchmark
    ryx ::benchmark baseline [name]   # Set current as baseline
    ryx ::benchmark compare [id1] [id2]  # Compare two runs
    ryx ::benchmark history [name]    # Show run history
"""

import sys
import asyncio
import argparse
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.benchmarks import (
    BenchmarkRunner, BenchmarkRegistry, RunConfig
)


def create_dummy_executor():
    """Create a dummy executor for testing"""
    async def executor(problem, config):
        # This would normally call the LLM
        # For now, return a placeholder
        return f"# Placeholder for {problem.problem_id}\ndef placeholder(): pass"
    return executor


def create_ollama_executor(model: str = "qwen2.5-coder:14b", base_url: str = "http://localhost:11434"):
    """Create an LLM executor using Ollama"""
    
    async def executor(problem, config):
        """Execute a benchmark problem using Ollama"""
        prompt = f"""You are a coding assistant. Solve the following problem:

Problem: {problem.description}

{problem.context if hasattr(problem, 'context') and problem.context else ''}

Provide a complete, working solution in Python. Return ONLY the code, no explanations."""

        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Lower for more consistent code
                        "num_predict": 2000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                return f"# Error: HTTP {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "# Error: Cannot connect to Ollama at " + base_url
        except Exception as e:
            return f"# Error: {str(e)}"
    
    return executor


async def cmd_list(args):
    """List available benchmarks"""
    print("\n📊 Available Benchmarks:\n")
    
    for name in BenchmarkRegistry.list_all():
        benchmark = BenchmarkRegistry.create(name)
        if benchmark:
            print(f"  • {name}")
            print(f"    {benchmark.description}")
            print(f"    Problems: {len(benchmark.problems)}")
            print()


async def cmd_run(args):
    """Run a benchmark"""
    runner = BenchmarkRunner()
    
    # Use Ollama executor if available, otherwise fall back to dummy
    if args.dry_run:
        print("🔄 Dry run mode - using dummy executor")
        runner.set_executor(create_dummy_executor())
    else:
        model = getattr(args, 'model', 'qwen2.5-coder:14b')
        base_url = getattr(args, 'ollama_url', 'http://localhost:11434')
        print(f"🤖 Using Ollama executor (model: {model})")
        runner.set_executor(create_ollama_executor(model, base_url))
    
    config = RunConfig(
        verbose=args.verbose,
        timeout_seconds=args.timeout,
        save_results=not args.no_save,
    )
    
    benchmark_name = args.name or "coding_tasks"
    
    print(f"\n🚀 Running benchmark: {benchmark_name}\n")
    
    try:
        result = await runner.run(benchmark_name, config)
        print(result.summary())
        
        if not args.no_save:
            print(f"💾 Results saved: {result.run_id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


async def cmd_baseline(args):
    """Set baseline for a benchmark"""
    runner = BenchmarkRunner()
    
    if args.run_id:
        # Set specific run as baseline
        try:
            runner.set_baseline(args.run_id)
            print(f"✅ Baseline set: {args.run_id}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1
    else:
        # Show current baseline
        benchmark_name = args.name or "coding_tasks"
        baseline = runner.get_baseline(benchmark_name)
        
        if baseline:
            print(f"\n📊 Current baseline for {benchmark_name}:")
            print(f"   Run ID: {baseline.run_id}")
            print(f"   Score: {baseline.average_score:.2%}")
            print(f"   Passed: {baseline.passed_count}/{baseline.total_problems}")
        else:
            print(f"ℹ️  No baseline set for {benchmark_name}")


async def cmd_compare(args):
    """Compare two benchmark runs"""
    runner = BenchmarkRunner()
    
    try:
        diff = runner.compare(args.run1, args.run2)
        
        print(f"\n📊 Comparison: {args.run1} vs {args.run2}\n")
        print(f"Score: {diff['run1_score']:.2%} → {diff['run2_score']:.2%} ({diff['score_diff']:+.2%})")
        print(f"Improved: {diff['improved_count']} problems")
        print(f"Regressed: {diff['regressed_count']} problems")
        print(f"Unchanged: {len(diff['unchanged'])} problems")
        
        if diff['is_improvement']:
            print("\n✅ Run 2 is an improvement!")
        else:
            print("\n⚠️  Run 2 has regressions")
            
        if diff['regressed'] and args.verbose:
            print(f"\nRegressed problems: {', '.join(diff['regressed'])}")
            
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1


async def cmd_history(args):
    """Show benchmark run history"""
    runner = BenchmarkRunner()
    benchmark_name = args.name
    
    runs = runner.list_runs(benchmark_name)
    
    if not runs:
        print(f"ℹ️  No runs found" + (f" for {benchmark_name}" if benchmark_name else ""))
        return
    
    print(f"\n📜 Benchmark History" + (f" ({benchmark_name})" if benchmark_name else "") + ":\n")
    
    for run_id in runs[:args.limit]:
        run = runner.load_run(run_id)
        if run:
            print(f"  {run_id}")
            print(f"    Score: {run.average_score:.2%} | Passed: {run.passed_count}/{run.total_problems}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Ryx AI Benchmark System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list
    list_parser = subparsers.add_parser('list', help='List available benchmarks')
    
    # run
    run_parser = subparsers.add_parser('run', help='Run a benchmark')
    run_parser.add_argument('name', nargs='?', help='Benchmark name')
    run_parser.add_argument('-v', '--verbose', action='store_true')
    run_parser.add_argument('--timeout', type=int, default=120)
    run_parser.add_argument('--no-save', action='store_true')
    run_parser.add_argument('--dry-run', action='store_true', help='Use dummy executor')
    
    # baseline
    baseline_parser = subparsers.add_parser('baseline', help='Manage baselines')
    baseline_parser.add_argument('name', nargs='?', help='Benchmark name')
    baseline_parser.add_argument('--set', dest='run_id', help='Set run as baseline')
    
    # compare
    compare_parser = subparsers.add_parser('compare', help='Compare two runs')
    compare_parser.add_argument('run1', help='First run ID')
    compare_parser.add_argument('run2', help='Second run ID')
    compare_parser.add_argument('-v', '--verbose', action='store_true')
    
    # history
    history_parser = subparsers.add_parser('history', help='Show run history')
    history_parser.add_argument('name', nargs='?', help='Benchmark name filter')
    history_parser.add_argument('-n', '--limit', type=int, default=10)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run async command
    cmd_map = {
        'list': cmd_list,
        'run': cmd_run,
        'baseline': cmd_baseline,
        'compare': cmd_compare,
        'history': cmd_history,
    }
    
    cmd = cmd_map.get(args.command)
    if cmd:
        result = asyncio.run(cmd(args))
        sys.exit(result or 0)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
