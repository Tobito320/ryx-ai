"""
Ryx AI - Comprehensive System Status
Provides detailed system information and diagnostics
"""

import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from core.paths import get_data_dir, get_log_dir
from core.rag_system import RAGSystem
from core.metrics_collector import get_metrics


class SystemStatus:
    """Comprehensive system status and diagnostics"""

    def __init__(self):
        self.data_dir = get_data_dir()
        self.log_dir = get_log_dir()

    def get_ollama_status(self) -> Dict[str, Any]:
        """Get Ollama service status"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)

            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    'running': True,
                    'models': [m['name'] for m in models],
                    'model_count': len(models)
                }
        except:
            pass

        return {
            'running': False,
            'models': [],
            'model_count': 0
        }

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}

        # RAG database
        rag_db = self.data_dir / "rag_knowledge.db"
        if rag_db.exists():
            size_mb = rag_db.stat().st_size / (1024 * 1024)
            stats['rag'] = {
                'size_mb': round(size_mb, 2),
                'exists': True
            }

            # Get counts
            try:
                rag = RAGSystem()
                rag_stats = rag.get_stats()
                stats['rag'].update({
                    'cached_responses': rag_stats.get('cached_responses', 0),
                    'known_files': rag_stats.get('known_files', 0),
                    'cache_hits': rag_stats.get('total_cache_hits', 0)
                })
                rag.close()
            except:
                pass
        else:
            stats['rag'] = {'exists': False}

        # Metrics database
        metrics_db = self.data_dir / "metrics.db"
        if metrics_db.exists():
            size_mb = metrics_db.stat().st_size / (1024 * 1024)
            stats['metrics'] = {
                'size_mb': round(size_mb, 2),
                'exists': True
            }
        else:
            stats['metrics'] = {'exists': False}

        # Meta learning database
        meta_db = self.data_dir / "meta_learning.db"
        if meta_db.exists():
            size_mb = meta_db.stat().st_size / (1024 * 1024)
            stats['meta_learning'] = {
                'size_mb': round(size_mb, 2),
                'exists': True
            }
        else:
            stats['meta_learning'] = {'exists': False}

        return stats

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            metrics = get_metrics()
            return metrics.get_session_metrics()
        except:
            return {}

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for Ryx AI"""
        total_size = 0

        # Data directory
        if self.data_dir.exists():
            for file in self.data_dir.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size

        # Log directory
        if self.log_dir.exists():
            for file in self.log_dir.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size

        return {
            'total_mb': round(total_size / (1024 * 1024), 2)
        }

    def check_health(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        health = {
            'overall': 'healthy',
            'issues': []
        }

        # Check Ollama
        ollama = self.get_ollama_status()
        if not ollama['running']:
            health['issues'].append('Ollama not running')
            health['overall'] = 'degraded'

        # Check databases
        db_stats = self.get_database_stats()
        if not db_stats.get('rag', {}).get('exists'):
            health['issues'].append('RAG database not initialized')
            health['overall'] = 'degraded'

        return health

    def format_status_display(self) -> str:
        """Format comprehensive status display"""
        lines = []
        lines.append("")
        lines.append("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        lines.append("\033[1;36m│  Ryx AI - System Status                  │\033[0m")
        lines.append("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        lines.append("")

        # Ollama Status
        ollama = self.get_ollama_status()
        if ollama['running']:
            lines.append(f"\033[1;32m●\033[0m Ollama: \033[1;32mOnline\033[0m")
            lines.append(f"  Models: {ollama['model_count']} installed")
            for model in ollama['models'][:3]:
                lines.append(f"    • {model}")
            if ollama['model_count'] > 3:
                lines.append(f"    • ... and {ollama['model_count'] - 3} more")
        else:
            lines.append(f"\033[1;31m●\033[0m Ollama: \033[1;31mOffline\033[0m")
            lines.append(f"  \033[2mStart with: systemctl --user start ollama\033[0m")

        lines.append("")

        # Database Status
        db_stats = self.get_database_stats()
        lines.append("\033[1;37mDatabases:\033[0m")

        if db_stats.get('rag', {}).get('exists'):
            rag = db_stats['rag']
            lines.append(f"  \033[1;32m✓\033[0m RAG Knowledge ({rag['size_mb']} MB)")
            if 'cached_responses' in rag:
                lines.append(f"    • {rag['cached_responses']} cached responses")
                lines.append(f"    • {rag['known_files']} known files")
                lines.append(f"    • {rag['cache_hits']} total cache hits")
        else:
            lines.append(f"  \033[1;33m⚠\033[0m RAG Knowledge (not initialized)")

        if db_stats.get('metrics', {}).get('exists'):
            lines.append(f"  \033[1;32m✓\033[0m Metrics ({db_stats['metrics']['size_mb']} MB)")
        else:
            lines.append(f"  \033[1;33m⚠\033[0m Metrics (not initialized)")

        if db_stats.get('meta_learning', {}).get('exists'):
            lines.append(f"  \033[1;32m✓\033[0m Meta Learning ({db_stats['meta_learning']['size_mb']} MB)")
        else:
            lines.append(f"  \033[1;33m⚠\033[0m Meta Learning (not initialized)")

        lines.append("")

        # Performance Metrics
        perf = self.get_performance_metrics()
        if perf and perf.get('queries', 0) > 0:
            lines.append("\033[1;37mPerformance (This Session):\033[0m")
            lines.append(f"  Queries: {perf['queries']}")
            lines.append(f"  Cache Hit Rate: {perf['cache_hit_rate']:.1f}%")
            lines.append(f"  Avg Latency: {perf['avg_latency_ms']:.1f}ms")
            lines.append("")

        # Disk Usage
        disk = self.get_disk_usage()
        lines.append(f"\033[1;37mDisk Usage:\033[0m {disk['total_mb']} MB")
        lines.append("")

        # Health Status
        health = self.check_health()
        if health['overall'] == 'healthy':
            lines.append(f"\033[1;32m●\033[0m Overall Status: \033[1;32mHEALTHY\033[0m")
        else:
            lines.append(f"\033[1;33m●\033[0m Overall Status: \033[1;33m{health['overall'].upper()}\033[0m")

        if health['issues']:
            lines.append("")
            lines.append("\033[1;33mIssues:\033[0m")
            for issue in health['issues']:
                lines.append(f"  • {issue}")

        lines.append("")

        return "\n".join(lines)


def show_comprehensive_status():
    """Show comprehensive system status"""
    status = SystemStatus()
    print(status.format_status_display())
