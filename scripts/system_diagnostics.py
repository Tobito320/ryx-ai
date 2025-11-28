#!/usr/bin/env python3
"""
Ryx AI - System Diagnostics
Comprehensive system diagnostics and troubleshooting tool
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from typing import Dict, List, Any

from core.system_status import SystemStatus
from core.health_monitor import HealthMonitor
from core.metrics_collector import get_metrics
from core.performance_profiler import get_profiler
from core.rag_system import RAGSystem
from core.meta_learner import MetaLearner
from core.paths import get_project_root, get_data_dir


class SystemDiagnostics:
    """Comprehensive system diagnostics and troubleshooting"""

    def __init__(self) -> None:
        """Initialize diagnostics with all system components"""
        self.project_root = get_project_root()
        self.data_dir = get_data_dir()
        self.status = SystemStatus()
        self.health_monitor = HealthMonitor(self.project_root)

    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Run complete system diagnostics"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - System Diagnostics\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }

        # Check Ollama
        print("\033[1;33m1. Checking Ollama Service...\033[0m")
        ollama_status = self.status.get_ollama_status()
        diagnostics['components']['ollama'] = ollama_status

        if ollama_status['running']:
            print(f"  \033[1;32m✓\033[0m Ollama: Online")
            print(f"  \033[1;37m→\033[0m Models: {ollama_status['model_count']}")
        else:
            print(f"  \033[1;31m✗\033[0m Ollama: Offline")
            print(f"  \033[1;33m→\033[0m Run: systemctl --user start ollama")

        # Check databases
        print("\n\033[1;33m2. Checking Databases...\033[0m")
        db_stats = self.status.get_database_stats()
        diagnostics['components']['databases'] = db_stats

        for db_name, stats in db_stats.items():
            if stats.get('exists'):
                print(f"  \033[1;32m✓\033[0m {db_name}: {stats['size_mb']} MB")
                if 'cached_responses' in stats:
                    print(f"    → Cached: {stats['cached_responses']} responses")
                    print(f"    → Known files: {stats['known_files']}")
            else:
                print(f"  \033[1;31m✗\033[0m {db_name}: Not initialized")

        # Check disk usage
        print("\n\033[1;33m3. Checking Disk Usage...\033[0m")
        disk_usage = self.status.get_disk_usage()
        diagnostics['disk_usage'] = disk_usage
        print(f"  \033[1;37m→\033[0m Total: {disk_usage['total_mb']} MB")

        # Check for common issues
        print("\n\033[1;33m4. Checking for Common Issues...\033[0m")
        issues = self._check_common_issues()
        diagnostics['issues'] = issues

        if not issues:
            print(f"  \033[1;32m✓\033[0m No issues detected")
        else:
            for issue in issues:
                print(f"  \033[1;33m⚠\033[0m {issue['description']}")
                if 'fix' in issue:
                    print(f"    → Fix: {issue['fix']}")

        # Check performance metrics
        print("\n\033[1;33m5. Checking Performance...\033[0m")
        try:
            metrics = get_metrics()
            perf = metrics.get_session_metrics()

            if perf.get('queries', 0) > 0:
                print(f"  \033[1;37m→\033[0m Queries: {perf['queries']}")
                print(f"  \033[1;37m→\033[0m Cache Hit Rate: {perf['cache_hit_rate']:.1f}%")
                print(f"  \033[1;37m→\033[0m Avg Latency: {perf['avg_latency_ms']:.1f}ms")
                diagnostics['performance'] = perf
            else:
                print(f"  \033[1;37m→\033[0m No metrics available yet")
        except Exception as e:
            print(f"  \033[1;31m✗\033[0m Could not load metrics: {e}")

        # Overall health
        print("\n\033[1;33m6. Overall Health\033[0m")
        health = self.status.check_health()
        diagnostics['health'] = health

        if health['overall'] == 'healthy':
            print(f"  \033[1;32m✓\033[0m System: HEALTHY")
        else:
            print(f"  \033[1;33m⚠\033[0m System: {health['overall'].upper()}")
            for issue in health['issues']:
                print(f"    → {issue}")

        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return diagnostics

    def _check_common_issues(self) -> List[Dict[str, str]]:
        """Check for common issues"""
        issues = []

        # Check if Ollama is running
        ollama = self.status.get_ollama_status()
        if not ollama['running']:
            issues.append({
                'type': 'ollama_offline',
                'description': 'Ollama service is not running',
                'fix': 'systemctl --user start ollama'
            })

        # Check if databases exist
        db_stats = self.status.get_database_stats()
        if not db_stats.get('rag', {}).get('exists'):
            issues.append({
                'type': 'no_rag_db',
                'description': 'RAG database not initialized',
                'fix': 'Run a query to initialize the database'
            })

        # Check disk space
        disk = self.status.get_disk_usage()
        if disk['total_mb'] > 1000:  # > 1GB
            issues.append({
                'type': 'high_disk_usage',
                'description': f'High disk usage: {disk["total_mb"]} MB',
                'fix': 'ryx ::clean --aggressive'
            })

        return issues

    def save_diagnostics(self, diagnostics: Dict[str, Any]) -> None:
        """Save diagnostics to file"""
        report_file = self.data_dir / "diagnostics_report.json"
        with open(report_file, 'w') as f:
            json.dump(diagnostics, f, indent=2)

        print(f"\033[1;32m✓\033[0m Diagnostics saved to: {report_file}")


def main():
    """Run system diagnostics"""
    diagnostics_tool = SystemDiagnostics()
    results = diagnostics_tool.run_full_diagnostics()
    diagnostics_tool.save_diagnostics(results)


if __name__ == "__main__":
    main()
