"""
Ryx AI - Service Manager

Manages RyxHub services (FastAPI backend, React frontend, WebSocket).
"""
import os
import subprocess
import signal
import json
from pathlib import Path
from typing import Dict, List, Optional
from core.paths import get_project_root, get_runtime_dir


class ServiceManager:
    """Manages RyxHub service lifecycle"""

    def __init__(self):
        self.project_root = get_project_root()
        self.runtime_dir = get_runtime_dir()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.runtime_dir / "ryxhub.pid"
        self.config_file = self.runtime_dir / "ryxhub.json"

    def start_ryxhub(self) -> Dict:
        """
        Start RyxHub services (Vite React frontend + optional FastAPI backend).

        Returns:
            dict: {success: bool, error: str, info: list[str]}
        """
        # Check if already running
        if self._is_running():
            return {
                'success': False,
                'error': 'RyxHub is already running',
                'info': self._get_running_info()
            }

        pids = {}
        info = []

        try:
            # Frontend (Vite React) - Primary UI
            frontend_port = 5173
            frontend_dir = self.project_root / "ryxhub"

            if not frontend_dir.exists():
                return {
                    'success': False,
                    'error': f'RyxHub directory not found: {frontend_dir}'
                }

            if not (frontend_dir / "package.json").exists():
                return {
                    'success': False,
                    'error': f'package.json not found in {frontend_dir}'
                }

            # Check if node_modules exists, install if not
            if not (frontend_dir / "node_modules").exists():
                info.append("Installing frontend dependencies...")
                install_result = subprocess.run(
                    ["npm", "install"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True
                )
                if install_result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'npm install failed: {install_result.stderr}'
                    }
                info.append("Dependencies installed successfully")

            # Start Vite dev server
            frontend_proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port)],
                cwd=str(frontend_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env={**os.environ, "BROWSER": "none"}
            )
            pids['frontend'] = frontend_proc.pid
            info.append(f"RyxHub UI: http://localhost:{frontend_port}")

            # Optional: Start FastAPI backend if exists
            backend_port = 8000
            backend_dir = self.project_root / "ryx_pkg" / "interfaces" / "web" / "backend"
            
            if backend_dir.exists() and (backend_dir / "main.py").exists():
                backend_proc = subprocess.Popen(
                    [
                        "python3", "-m", "uvicorn",
                        "main:app",
                        "--host", "127.0.0.1",
                        "--port", str(backend_port),
                        "--reload"
                    ],
                    cwd=str(backend_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                pids['backend'] = backend_proc.pid
                info.append(f"FastAPI backend: http://localhost:{backend_port}")
                info.append(f"WebSocket: ws://localhost:{backend_port}/ws")

            # Save PIDs
            self._save_pids(pids)

            # Open browser after short delay
            import threading
            import webbrowser
            def open_browser():
                import time
                time.sleep(2)
                webbrowser.open(f"http://localhost:{frontend_port}")
            threading.Thread(target=open_browser, daemon=True).start()

            return {
                'success': True,
                'info': info,
                'pids': pids
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Failed to start service: {e}'
            }
        except FileNotFoundError as e:
            return {
                'success': False,
                'error': f'Required command not found: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def stop_ryxhub(self) -> Dict:
        """
        Stop all RyxHub services.

        Returns:
            dict: {success: bool, error: str}
        """
        if not self._is_running():
            return {
                'success': False,
                'error': 'RyxHub is not running'
            }

        pids = self._load_pids()
        stopped = []
        failed = []

        for service, pid in pids.items():
            try:
                # Verify the process is still the one we started
                import psutil
                try:
                    proc = psutil.Process(pid)
                    # Check if process name contains expected keywords
                    proc_name = proc.name().lower()
                    proc_cmdline = ' '.join(proc.cmdline()).lower()
                    
                    # Only kill if it looks like our process
                    if any(kw in proc_name or kw in proc_cmdline 
                           for kw in ['python', 'uvicorn', 'npm', 'node']):
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                        stopped.append(service)
                    else:
                        # Process doesn't match, skip
                        stopped.append(f"{service} (already stopped)")
                except psutil.NoSuchProcess:
                    # Process already dead
                    stopped.append(service)
            except ProcessLookupError:
                # Process already dead
                stopped.append(service)
            except PermissionError:
                try:
                    os.kill(pid, signal.SIGTERM)
                    stopped.append(service)
                except Exception:
                    failed.append(service)
            except Exception as e:
                failed.append(f"{service}: {e}")

        # Clean up PID file
        self._clear_pids()

        if failed:
            return {
                'success': False,
                'error': f'Failed to stop: {", ".join(failed)}',
                'stopped': stopped
            }

        return {
            'success': True,
            'stopped': stopped
        }

    def get_status(self) -> Dict:
        """
        Get status of all services.

        Returns:
            dict: {service_name: {running: bool, pid: int, ports: list}}
        """
        status = {
            'RyxHub': {
                'running': False,
                'ports': []
            }
        }

        if self._is_running():
            pids = self._load_pids()
            status['RyxHub']['running'] = True
            status['RyxHub']['pids'] = pids

        # Add port info
            if 'frontend' in pids:
                status['RyxHub']['ports'].append("RyxHub UI: http://localhost:5173")
            if 'backend' in pids:
                status['RyxHub']['ports'].append("FastAPI: http://localhost:8000")

        return status

    def _is_running(self) -> bool:
        """Check if RyxHub is running"""
        if not self.pid_file.exists():
            return False

        pids = self._load_pids()
        if not pids:
            return False

        # Check if any process is still alive
        for pid in pids.values():
            try:
                os.kill(pid, 0)
                return True
            except (ProcessLookupError, PermissionError):
                continue

        # All processes dead, clean up
        self._clear_pids()
        return False

    def _get_running_info(self) -> List[str]:
        """Get info about running services"""
        info = []
        pids = self._load_pids()

        if 'frontend' in pids:
            info.append("RyxHub UI: http://localhost:5173")
        if 'backend' in pids:
            info.append("FastAPI backend: http://localhost:8000")

        return info

    def _save_pids(self, pids: Dict):
        """Save PIDs to file"""
        with open(self.pid_file, 'w') as f:
            json.dump(pids, f)

    def _load_pids(self) -> Dict:
        """Load PIDs from file"""
        if not self.pid_file.exists():
            return {}
        try:
            with open(self.pid_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _clear_pids(self):
        """Clear PID file"""
        if self.pid_file.exists():
            self.pid_file.unlink()
