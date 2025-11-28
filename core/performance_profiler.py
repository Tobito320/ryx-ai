"""
Ryx AI - Performance Profiler
Provides performance profiling and bottleneck detection
"""

import time
import functools
from typing import Callable, Dict, Any, List
from collections import defaultdict
from datetime import datetime


class PerformanceProfiler:
    """
    Performance profiling and timing utilities

    Features:
    - Function timing decorator
    - Bottleneck detection
    - Performance statistics
    - Hot path identification
    """

    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)

    def time_function(self, func: Callable) -> Callable:
        """
        Decorator to time function execution

        Usage:
            @profiler.time_function
            def my_function():
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000  # Convert to ms

            func_name = f"{func.__module__}.{func.__name__}"
            self.timings[func_name].append(duration)
            self.call_counts[func_name] += 1

            return result

        return wrapper

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}

        for func_name, timings in self.timings.items():
            if not timings:
                continue

            sorted_timings = sorted(timings)
            count = len(timings)

            stats[func_name] = {
                'count': count,
                'total_ms': sum(timings),
                'avg_ms': sum(timings) / count,
                'min_ms': min(timings),
                'max_ms': max(timings),
                'p50_ms': sorted_timings[count // 2],
                'p95_ms': sorted_timings[int(count * 0.95)] if count > 1 else sorted_timings[0],
                'p99_ms': sorted_timings[int(count * 0.99)] if count > 1 else sorted_timings[0],
            }

        return stats

    def get_hot_paths(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the slowest functions (hot paths)

        Args:
            limit: Number of functions to return

        Returns:
            List of dicts with function info
        """
        stats = self.get_statistics()

        # Sort by total time spent
        hot_paths = sorted(
            stats.items(),
            key=lambda x: x[1]['total_ms'],
            reverse=True
        )[:limit]

        return [
            {
                'function': name,
                **data
            }
            for name, data in hot_paths
        ]

    def get_bottlenecks(self, threshold_ms: float = 100) -> List[Dict[str, Any]]:
        """
        Identify bottlenecks (functions averaging over threshold)

        Args:
            threshold_ms: Minimum average time to consider a bottleneck

        Returns:
            List of bottleneck functions
        """
        stats = self.get_statistics()

        bottlenecks = [
            {
                'function': name,
                **data
            }
            for name, data in stats.items()
            if data['avg_ms'] > threshold_ms
        ]

        return sorted(bottlenecks, key=lambda x: x['avg_ms'], reverse=True)

    def format_report(self) -> str:
        """Format performance report for display"""
        lines = []
        lines.append("")
        lines.append("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        lines.append("\033[1;36m│  Performance Profile                     │\033[0m")
        lines.append("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        lines.append("")

        # Hot paths
        hot_paths = self.get_hot_paths(5)
        if hot_paths:
            lines.append("\033[1;33mHot Paths (Most Time Spent):\033[0m")
            for path in hot_paths:
                func_name = path['function'].split('.')[-1]
                lines.append(f"  • {func_name}")
                lines.append(f"    Total: {path['total_ms']:.1f}ms | Calls: {path['count']} | Avg: {path['avg_ms']:.1f}ms")
            lines.append("")

        # Bottlenecks
        bottlenecks = self.get_bottlenecks(50)
        if bottlenecks:
            lines.append("\033[1;33mBottlenecks (>50ms avg):\033[0m")
            for bottleneck in bottlenecks[:5]:
                func_name = bottleneck['function'].split('.')[-1]
                lines.append(f"  • {func_name}: {bottleneck['avg_ms']:.1f}ms avg")
            lines.append("")

        # Summary
        total_calls = sum(self.call_counts.values())
        total_time = sum(sum(timings) for timings in self.timings.values())

        lines.append("\033[1;33mSummary:\033[0m")
        lines.append(f"  Total function calls: {total_calls}")
        lines.append(f"  Total time: {total_time:.1f}ms")
        lines.append(f"  Functions tracked: {len(self.timings)}")
        lines.append("")

        return "\n".join(lines)

    def reset(self):
        """Reset all profiling data"""
        self.timings.clear()
        self.call_counts.clear()


# Context manager for timing code blocks
class Timer:
    """
    Context manager for timing code blocks

    Usage:
        with Timer("operation_name") as timer:
            # code to time
            pass

        print(f"Took {timer.duration_ms}ms")
    """

    def __init__(self, name: str = "operation"):
        self.name = name
        self.duration_ms = 0
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    return _profiler


def profile(func: Callable) -> Callable:
    """
    Decorator shorthand for profiling

    Usage:
        @profile
        def my_function():
            ...
    """
    return _profiler.time_function(func)
