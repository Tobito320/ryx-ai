"""
Ryx AI - Startup Optimizer
Benchmarks and optimizes startup time
"""

import time
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir


@dataclass
class BenchmarkResult:
    """Result of a benchmark"""
    name: str
    duration_ms: float
    success: bool
    details: Optional[str] = None


class StartupOptimizer:
    """
    Optimizes Ryx AI startup time

    Features:
    - Benchmark startup components
    - Measure model loading time
    - Implement lazy loading strategy
    - Pre-warm cache on boot (if fast enough)
    - Create systemd service for boot loading
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or get_project_root()
        self.benchmark_file = self.project_root / "data" / "benchmarks.json"

    def benchmark_startup(self) -> Dict[str, BenchmarkResult]:
        """
        Benchmark full startup sequence

        Returns: Dict of component -> BenchmarkResult
        """
        results = {}

        # Benchmark imports
        results['imports'] = self._benchmark_imports()

        # Benchmark config loading
        results['config'] = self._benchmark_config_loading()

        # Benchmark database initialization
        results['database'] = self._benchmark_database_init()

        # Benchmark Ollama connection
        results['ollama'] = self._benchmark_ollama_connection()

        # Save results
        self._save_benchmarks(results)

        return results

    def _benchmark_imports(self) -> BenchmarkResult:
        """Benchmark module imports"""
        start = time.perf_counter()

        try:
            # Import all core modules
            from core.command_executor import CommandExecutor
            from core.history_manager import HistoryManager

            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='imports',
                duration_ms=duration,
                success=True,
                details="All core modules imported"
            )
        except ImportError as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='imports',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def _benchmark_config_loading(self) -> BenchmarkResult:
        """Benchmark configuration loading"""
        start = time.perf_counter()

        try:
            config_dir = self.project_root / "configs"
            configs_loaded = 0

            for config_file in ['settings.json', 'models.json', 'permissions.json']:
                config_path = config_dir / config_file
                if config_path.exists():
                    with open(config_path) as f:
                        json.load(f)
                    configs_loaded += 1

            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='config',
                duration_ms=duration,
                success=True,
                details=f"Loaded {configs_loaded} config files"
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='config',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def _benchmark_database_init(self) -> BenchmarkResult:
        """Benchmark database initialization"""
        import sqlite3

        start = time.perf_counter()

        try:
            db_path = self.project_root / "data" / "rag_knowledge.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Quick query to ensure tables exist
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            conn.close()

            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='database',
                duration_ms=duration,
                success=True,
                details=f"Database has {table_count} tables"
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='database',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def _benchmark_ollama_connection(self) -> BenchmarkResult:
        """Benchmark Ollama connection"""
        import requests

        start = time.perf_counter()

        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)

            if response.status_code == 200:
                models = response.json().get("models", [])
                duration = (time.perf_counter() - start) * 1000
                return BenchmarkResult(
                    name='ollama',
                    duration_ms=duration,
                    success=True,
                    details=f"Connected, {len(models)} models available"
                )
            else:
                duration = (time.perf_counter() - start) * 1000
                return BenchmarkResult(
                    name='ollama',
                    duration_ms=duration,
                    success=False,
                    details=f"HTTP {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='ollama',
                duration_ms=duration,
                success=False,
                details="Connection refused - Ollama not running"
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='ollama',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def benchmark_model_loading(self, model_name: str = "qwen2.5:1.5b") -> BenchmarkResult:
        """Benchmark model loading time"""
        import requests

        start = time.perf_counter()

        try:
            # Make a minimal request to load the model
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "test",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=60
            )

            duration = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                return BenchmarkResult(
                    name=f'model_load_{model_name}',
                    duration_ms=duration,
                    success=True,
                    details=f"Model loaded in {duration:.0f}ms"
                )
            else:
                return BenchmarkResult(
                    name=f'model_load_{model_name}',
                    duration_ms=duration,
                    success=False,
                    details=f"HTTP {response.status_code}"
                )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name=f'model_load_{model_name}',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def benchmark_full_query(self, prompt: str = "What is 2+2?") -> BenchmarkResult:
        """Benchmark a full query cycle"""
        import requests

        start = time.perf_counter()

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:1.5b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            duration = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                return BenchmarkResult(
                    name='full_query',
                    duration_ms=duration,
                    success=True,
                    details=f"Query completed in {duration:.0f}ms"
                )
            else:
                return BenchmarkResult(
                    name='full_query',
                    duration_ms=duration,
                    success=False,
                    details=f"HTTP {response.status_code}"
                )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                name='full_query',
                duration_ms=duration,
                success=False,
                details=str(e)
            )

    def _save_benchmarks(self, results: Dict[str, BenchmarkResult]):
        """Save benchmark results to file"""
        self.benchmark_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing benchmarks
        existing = {}
        if self.benchmark_file.exists():
            with open(self.benchmark_file) as f:
                existing = json.load(f)

        # Add new results
        timestamp = datetime.now().isoformat()
        existing[timestamp] = {
            name: {
                'duration_ms': result.duration_ms,
                'success': result.success,
                'details': result.details
            }
            for name, result in results.items()
        }

        # Keep only last 100 entries
        if len(existing) > 100:
            keys = sorted(existing.keys(), reverse=True)[:100]
            existing = {k: existing[k] for k in keys}

        with open(self.benchmark_file, 'w') as f:
            json.dump(existing, f, indent=2)

    def get_benchmark_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get benchmark history"""
        if not self.benchmark_file.exists():
            return {}

        with open(self.benchmark_file) as f:
            data = json.load(f)

        # Get most recent entries
        keys = sorted(data.keys(), reverse=True)[:limit]
        return {k: data[k] for k in keys}

    def get_startup_strategy(self) -> Dict[str, Any]:
        """
        Determine optimal startup strategy based on benchmarks

        Returns:
            {
                'strategy': 'boot_load' | 'lazy_load' | 'on_demand',
                'reason': str,
                'estimated_startup_ms': float
            }
        """
        # Run benchmarks
        results = self.benchmark_startup()

        total_time = sum(r.duration_ms for r in results.values())

        if total_time < 2000:  # Less than 2 seconds
            return {
                'strategy': 'boot_load',
                'reason': f'Fast startup ({total_time:.0f}ms), can load at system boot',
                'estimated_startup_ms': total_time
            }
        elif total_time < 5000:  # Less than 5 seconds
            return {
                'strategy': 'lazy_load',
                'reason': f'Moderate startup ({total_time:.0f}ms), lazy load on first use',
                'estimated_startup_ms': total_time
            }
        else:
            return {
                'strategy': 'on_demand',
                'reason': f'Slow startup ({total_time:.0f}ms), load components on demand',
                'estimated_startup_ms': total_time
            }

    def generate_systemd_service(self) -> str:
        """Generate systemd service file for boot loading"""
        service_content = f"""[Unit]
Description=Ryx AI Preloader
After=network.target ollama.service

[Service]
Type=oneshot
ExecStart={sys.executable} -c "import sys; sys.path.insert(0, '{self.project_root}'); from core.startup_optimizer import warmup; warmup()"
User={Path.home().name}
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""
        return service_content

    def install_systemd_service(self) -> bool:
        """Install systemd user service"""
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)

        service_file = service_dir / "ryx-preload.service"

        try:
            with open(service_file, 'w') as f:
                f.write(self.generate_systemd_service())

            return True
        except Exception:
            return False

    def format_benchmarks_for_display(self) -> str:
        """Format benchmark results for terminal display"""
        results = self.benchmark_startup()

        lines = []
        lines.append("")
        lines.append("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        lines.append("\033[1;36m│  Startup Benchmarks                      │\033[0m")
        lines.append("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        lines.append("")

        total_time = 0
        for name, result in results.items():
            icon = "\033[1;32m✓\033[0m" if result.success else "\033[1;31m✗\033[0m"
            duration = f"{result.duration_ms:.1f}ms"

            # Color code by duration
            if result.duration_ms < 50:
                duration = f"\033[1;32m{duration}\033[0m"  # Green
            elif result.duration_ms < 200:
                duration = f"\033[1;33m{duration}\033[0m"  # Yellow
            else:
                duration = f"\033[1;31m{duration}\033[0m"  # Red

            lines.append(f"  {icon} {name:<20} {duration:>15}  {result.details or ''}")
            total_time += result.duration_ms

        lines.append("")
        lines.append(f"  \033[1;37mTotal:\033[0m {total_time:.1f}ms")

        # Strategy recommendation
        strategy = self.get_startup_strategy()
        lines.append("")
        lines.append(f"  \033[1;33mRecommended:\033[0m {strategy['strategy']}")
        lines.append(f"  \033[2m{strategy['reason']}\033[0m")
        lines.append("")

        return "\n".join(lines)


def warmup():
    """
    Warmup function called by systemd service

    Pre-loads critical components to memory
    """
    try:
        # Import core modules to cache them
        from core.command_executor import CommandExecutor
        from core.history_manager import HistoryManager

        # Initialize database connections
        executor = CommandExecutor()
        history = HistoryManager()

        print("Ryx AI warmup complete")
    except Exception as e:
        print(f"Ryx AI warmup failed: {e}")
