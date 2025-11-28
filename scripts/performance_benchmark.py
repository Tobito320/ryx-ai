#!/usr/bin/env python3
"""
Ryx AI - Performance Benchmark
Comprehensive performance testing and benchmarking tool
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any

from core.rag_system import RAGSystem
from core.meta_learner import MetaLearner
from core.health_monitor import HealthMonitor
from core.startup_optimizer import StartupOptimizer, BenchmarkResult
from core.paths import get_project_root, get_data_dir


class PerformanceBenchmark:
    """Comprehensive performance benchmarking"""

    def __init__(self) -> None:
        """Initialize performance benchmark tool"""
        self.project_root = get_project_root()
        self.data_dir = get_data_dir()
        self.results = {}

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Performance Benchmark Suite\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        self.results['timestamp'] = datetime.now().isoformat()
        self.results['benchmarks'] = {}

        # 1. Cache Performance
        print("\033[1;33m1. Cache Performance\033[0m")
        cache_results = self._benchmark_cache_performance()
        self.results['benchmarks']['cache'] = cache_results
        self._print_cache_results(cache_results)

        # 2. Database Performance
        print("\n\033[1;33m2. Database Performance\033[0m")
        db_results = self._benchmark_database_performance()
        self.results['benchmarks']['database'] = db_results
        self._print_db_results(db_results)

        # 3. Preference Learning
        print("\n\033[1;33m3. Preference Learning\033[0m")
        pref_results = self._benchmark_preference_learning()
        self.results['benchmarks']['preferences'] = pref_results
        self._print_pref_results(pref_results)

        # 4. Startup Time
        print("\n\033[1;33m4. Startup Performance\033[0m")
        startup_results = self._benchmark_startup()
        self.results['benchmarks']['startup'] = startup_results
        self._print_startup_results(startup_results)

        # 5. Overall Summary
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mSummary\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m")
        self._print_summary()

        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return self.results

    def _benchmark_cache_performance(self) -> Dict[str, Any]:
        """Benchmark cache read/write performance"""
        rag = RAGSystem()
        results = {
            'write_times_ms': [],
            'hot_read_times_ms': [],
            'cold_read_times_ms': [],
            'cache_hits': 0,
            'cache_misses': 0
        }

        # Benchmark writes
        test_queries = [
            f"test query {i}" for i in range(100)
        ]

        for query in test_queries:
            start = time.perf_counter()
            rag.cache_response(query, f"response for {query}", "test_model")
            duration_ms = (time.perf_counter() - start) * 1000
            results['write_times_ms'].append(duration_ms)

        # Benchmark hot cache reads (in-memory)
        for query in test_queries[:10]:
            start = time.perf_counter()
            response = rag.query_cache(query)
            duration_ms = (time.perf_counter() - start) * 1000

            if response:
                results['cache_hits'] += 1
                results['hot_read_times_ms'].append(duration_ms)
            else:
                results['cache_misses'] += 1

        # Benchmark cold cache reads (after clearing hot cache)
        rag.hot_cache.clear()

        for query in test_queries[:10]:
            start = time.perf_counter()
            response = rag.query_cache(query)
            duration_ms = (time.perf_counter() - start) * 1000

            if response:
                results['cold_read_times_ms'].append(duration_ms)

        # Calculate statistics
        if results['write_times_ms']:
            results['write_avg_ms'] = statistics.mean(results['write_times_ms'])
            results['write_p50_ms'] = statistics.median(results['write_times_ms'])
            results['write_p95_ms'] = statistics.quantiles(results['write_times_ms'], n=20)[18]

        if results['hot_read_times_ms']:
            results['hot_read_avg_ms'] = statistics.mean(results['hot_read_times_ms'])
            results['hot_read_p50_ms'] = statistics.median(results['hot_read_times_ms'])

        if results['cold_read_times_ms']:
            results['cold_read_avg_ms'] = statistics.mean(results['cold_read_times_ms'])
            results['cold_read_p50_ms'] = statistics.median(results['cold_read_times_ms'])

        rag.close()

        return results

    def _benchmark_database_performance(self) -> Dict[str, Any]:
        """Benchmark database operations"""
        import sqlite3

        results = {
            'query_times_ms': [],
            'write_times_ms': [],
            'index_effectiveness': {}
        }

        # Test RAG database
        rag_db = self.data_dir / "rag_knowledge.db"
        if rag_db.exists():
            conn = sqlite3.connect(rag_db)
            cursor = conn.cursor()

            # Benchmark simple query
            for _ in range(10):
                start = time.perf_counter()
                cursor.execute("SELECT COUNT(*) FROM quick_responses")
                cursor.fetchone()
                duration_ms = (time.perf_counter() - start) * 1000
                results['query_times_ms'].append(duration_ms)

            # Test with index
            start = time.perf_counter()
            cursor.execute("SELECT * FROM quick_responses WHERE prompt_hash = 'test' LIMIT 1")
            cursor.fetchone()
            with_index_ms = (time.perf_counter() - start) * 1000

            # Test without using index (full scan)
            start = time.perf_counter()
            cursor.execute("SELECT * FROM quick_responses WHERE response LIKE '%test%' LIMIT 1")
            cursor.fetchone()
            without_index_ms = (time.perf_counter() - start) * 1000

            results['index_effectiveness'] = {
                'with_index_ms': with_index_ms,
                'without_index_ms': without_index_ms,
                'speedup': without_index_ms / with_index_ms if with_index_ms > 0 else 0
            }

            conn.close()

        if results['query_times_ms']:
            results['query_avg_ms'] = statistics.mean(results['query_times_ms'])
            results['query_p50_ms'] = statistics.median(results['query_times_ms'])

        return results

    def _benchmark_preference_learning(self) -> Dict[str, Any]:
        """Benchmark preference learning performance"""
        meta_learner = MetaLearner()

        results = {
            'detection_times_ms': [],
            'application_times_ms': [],
            'detected_count': 0
        }

        # Test preference detection
        test_queries = [
            ("open with nvim", "Opening in nvim editor"),
            ("use zsh", "Using zsh shell"),
            ("dark theme", "Applying dark theme"),
        ]

        for query, response in test_queries:
            start = time.perf_counter()
            detected = meta_learner.detect_preference_from_query(query, response)
            duration_ms = (time.perf_counter() - start) * 1000

            results['detection_times_ms'].append(duration_ms)
            if detected:
                results['detected_count'] += 1

        # Test preference application
        test_responses = [
            "You can use nano to edit the file",
            "Open it with vim editor",
            "Use the bash shell",
        ]

        for response in test_responses:
            start = time.perf_counter()
            modified = meta_learner.apply_preferences_to_response(response)
            duration_ms = (time.perf_counter() - start) * 1000
            results['application_times_ms'].append(duration_ms)

        if results['detection_times_ms']:
            results['detection_avg_ms'] = statistics.mean(results['detection_times_ms'])

        if results['application_times_ms']:
            results['application_avg_ms'] = statistics.mean(results['application_times_ms'])

        return results

    def _benchmark_startup(self) -> Dict[str, Any]:
        """Benchmark startup performance"""
        optimizer = StartupOptimizer()

        try:
            benchmark_results = optimizer.benchmark_startup()

            results = {
                'components': {},
                'total_time_ms': 0
            }

            for component, result in benchmark_results.items():
                if isinstance(result, BenchmarkResult):
                    results['components'][component] = {
                        'duration_ms': result.duration_ms,
                        'success': result.success,
                        'details': result.details
                    }
                    results['total_time_ms'] += result.duration_ms

            return results
        except Exception as e:
            return {'error': str(e)}

    def _print_cache_results(self, results: Dict[str, Any]) -> None:
        """Print cache benchmark results"""
        if 'write_avg_ms' in results:
            print(f"  Write Performance:")
            print(f"    Avg: {results['write_avg_ms']:.2f}ms")
            print(f"    P50: {results['write_p50_ms']:.2f}ms")
            print(f"    P95: {results['write_p95_ms']:.2f}ms")

        if 'hot_read_avg_ms' in results:
            print(f"  Hot Cache Read (in-memory):")
            print(f"    Avg: {results['hot_read_avg_ms']:.2f}ms")
            print(f"    P50: {results['hot_read_p50_ms']:.2f}ms")

            target_ms = 10
            if results['hot_read_avg_ms'] < target_ms:
                print(f"    \033[1;32m✓\033[0m Target <{target_ms}ms met")
            else:
                print(f"    \033[1;33m⚠\033[0m Target <{target_ms}ms not met")

        if 'cold_read_avg_ms' in results:
            print(f"  Cold Cache Read (SQLite):")
            print(f"    Avg: {results['cold_read_avg_ms']:.2f}ms")
            print(f"    P50: {results['cold_read_p50_ms']:.2f}ms")

    def _print_db_results(self, results: Dict[str, Any]) -> None:
        """Print database benchmark results"""
        if 'query_avg_ms' in results:
            print(f"  Query Performance:")
            print(f"    Avg: {results['query_avg_ms']:.2f}ms")
            print(f"    P50: {results['query_p50_ms']:.2f}ms")

        if 'index_effectiveness' in results:
            idx = results['index_effectiveness']
            if idx.get('speedup', 0) > 0:
                print(f"  Index Effectiveness:")
                print(f"    With index: {idx['with_index_ms']:.2f}ms")
                print(f"    Without index: {idx['without_index_ms']:.2f}ms")
                print(f"    Speedup: {idx['speedup']:.1f}x")

    def _print_pref_results(self, results: Dict[str, Any]) -> None:
        """Print preference learning results"""
        if 'detection_avg_ms' in results:
            print(f"  Preference Detection:")
            print(f"    Avg: {results['detection_avg_ms']:.2f}ms")
            print(f"    Detected: {results['detected_count']} preferences")

        if 'application_avg_ms' in results:
            print(f"  Preference Application:")
            print(f"    Avg: {results['application_avg_ms']:.2f}ms")

    def _print_startup_results(self, results: Dict[str, Any]) -> None:
        """Print startup benchmark results"""
        if 'error' in results:
            print(f"  \033[1;31m✗\033[0m Error: {results['error']}")
            return

        if 'total_time_ms' in results:
            print(f"  Total Startup Time: {results['total_time_ms']:.2f}ms")

            for component, data in results['components'].items():
                status = "\033[1;32m✓\033[0m" if data['success'] else "\033[1;31m✗\033[0m"
                print(f"    {status} {component}: {data['duration_ms']:.2f}ms")

    def _print_summary(self) -> None:
        """Print benchmark summary"""
        benchmarks = self.results['benchmarks']

        # Check targets
        targets_met = []
        targets_missed = []

        # Cache target: <10ms hot reads
        if 'cache' in benchmarks and 'hot_read_avg_ms' in benchmarks['cache']:
            if benchmarks['cache']['hot_read_avg_ms'] < 10:
                targets_met.append("Cache hot reads <10ms")
            else:
                targets_missed.append("Cache hot reads <10ms")

        # Database target: <50ms queries
        if 'database' in benchmarks and 'query_avg_ms' in benchmarks['database']:
            if benchmarks['database']['query_avg_ms'] < 50:
                targets_met.append("Database queries <50ms")
            else:
                targets_missed.append("Database queries <50ms")

        print()
        if targets_met:
            print("\033[1;32mTargets Met:\033[0m")
            for target in targets_met:
                print(f"  ✓ {target}")

        if targets_missed:
            print("\n\033[1;33mTargets Missed:\033[0m")
            for target in targets_missed:
                print(f"  ⚠ {target}")

    def save_results(self) -> None:
        """Save benchmark results to file"""
        results_file = self.data_dir / "benchmark_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n\033[1;32m✓\033[0m Results saved to: {results_file}")


def main():
    """Run performance benchmarks"""
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()
    benchmark.save_results()


if __name__ == "__main__":
    main()
