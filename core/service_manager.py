"""
Ryx AI - Service Manager

Manages RyxHub services (FastAPI backend, React frontend, WebSocket).
Also manages SearXNG for privacy-first web search.
"""
import os
import subprocess
import signal
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from core.paths import get_project_root, get_runtime_dir


class SearXNGManager:
    """Manages SearXNG service for privacy-first web search"""
    
    DEFAULT_PORT = 8888
    SEARXNG_IMAGE = "searxng/searxng:latest"
    
    def __init__(self):
        self.runtime_dir = get_runtime_dir()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.runtime_dir / "searxng.pid"
        self.config_dir = get_project_root() / "configs" / "searxng"
        
    def ensure_running(self) -> Dict:
        """
        Ensure SearXNG is running. Start if not running.
        Returns dict with success, url, and any messages.
        """
        # Check if already running
        if self.is_running():
            return {
                'success': True,
                'url': f'http://localhost:{self.DEFAULT_PORT}',
                'message': 'SearXNG already running'
            }
        
        # Try to start
        return self.start()
    
    def is_running(self) -> bool:
        """Check if SearXNG is accessible"""
        import requests
        try:
            response = requests.get(
                f'http://localhost:{self.DEFAULT_PORT}/', 
                timeout=2
            )
            return response.status_code == 200
        except:
            return False
    
    def start(self) -> Dict:
        """Start SearXNG using available method (podman/docker or local)"""
        # Try podman first (Arch Linux preference)
        if self._has_command('podman'):
            return self._start_with_podman()
        
        # Try docker
        if self._has_command('docker'):
            return self._start_with_docker()
        
        # Try local installation
        return self._start_local()
    
    def _has_command(self, cmd: str) -> bool:
        """Check if command exists"""
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except:
            return False
    
    def _start_with_podman(self) -> Dict:
        """Start SearXNG with podman"""
        try:
            # Check if container already exists
            result = subprocess.run(
                ['podman', 'ps', '-a', '--filter', 'name=ryx-searxng', '--format', '{{.Names}}'],
                capture_output=True, text=True
            )
            
            container_exists = 'ryx-searxng' in result.stdout
            
            if container_exists:
                # Start existing container
                subprocess.run(
                    ['podman', 'start', 'ryx-searxng'],
                    capture_output=True, check=True
                )
            else:
                # Create and start new container
                subprocess.run([
                    'podman', 'run', '-d',
                    '--name', 'ryx-searxng',
                    '-p', f'{self.DEFAULT_PORT}:8080',
                    '-e', 'SEARXNG_BASE_URL=http://localhost:8888/',
                    self.SEARXNG_IMAGE
                ], capture_output=True, check=True)
            
            # Wait for startup
            for _ in range(10):
                if self.is_running():
                    self._update_ryx_config()
                    return {
                        'success': True,
                        'url': f'http://localhost:{self.DEFAULT_PORT}',
                        'message': 'SearXNG started via podman'
                    }
                time.sleep(1)
            
            return {
                'success': False,
                'error': 'SearXNG started but not responding'
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Podman error: {e.stderr if e.stderr else str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _start_with_docker(self) -> Dict:
        """Start SearXNG with docker"""
        try:
            # Check if container already exists
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=ryx-searxng', '--format', '{{.Names}}'],
                capture_output=True, text=True
            )
            
            container_exists = 'ryx-searxng' in result.stdout
            
            if container_exists:
                subprocess.run(['docker', 'start', 'ryx-searxng'], capture_output=True, check=True)
            else:
                subprocess.run([
                    'docker', 'run', '-d',
                    '--name', 'ryx-searxng',
                    '-p', f'{self.DEFAULT_PORT}:8080',
                    '-e', 'SEARXNG_BASE_URL=http://localhost:8888/',
                    self.SEARXNG_IMAGE
                ], capture_output=True, check=True)
            
            for _ in range(10):
                if self.is_running():
                    self._update_ryx_config()
                    return {
                        'success': True,
                        'url': f'http://localhost:{self.DEFAULT_PORT}',
                        'message': 'SearXNG started via docker'
                    }
                time.sleep(1)
            
            return {
                'success': False,
                'error': 'SearXNG started but not responding'
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Docker error: {e.stderr if e.stderr else str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _start_local(self) -> Dict:
        """Try to start local SearXNG installation"""
        # Check for common local installations
        local_paths = [
            '/usr/local/searxng',
            '/opt/searxng',
            Path.home() / 'searxng',
            Path.home() / '.local' / 'share' / 'searxng'
        ]
        
        for path in local_paths:
            searxng_run = Path(path) / 'searxng-run'
            if searxng_run.exists():
                try:
                    proc = subprocess.Popen(
                        [str(searxng_run)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    
                    with open(self.pid_file, 'w') as f:
                        f.write(str(proc.pid))
                    
                    for _ in range(10):
                        if self.is_running():
                            self._update_ryx_config()
                            return {
                                'success': True,
                                'url': f'http://localhost:{self.DEFAULT_PORT}',
                                'message': f'SearXNG started from {path}'
                            }
                        time.sleep(1)
                        
                except Exception as e:
                    continue
        
        return {
            'success': False,
            'error': (
                'SearXNG not found. Install with:\n'
                '  podman run -d --name ryx-searxng -p 8888:8080 searxng/searxng\n'
                'Or: docker run -d --name ryx-searxng -p 8888:8080 searxng/searxng'
            )
        }
    
    def stop(self) -> Dict:
        """Stop SearXNG"""
        try:
            # Try podman first
            if self._has_command('podman'):
                subprocess.run(['podman', 'stop', 'ryx-searxng'], capture_output=True)
                return {'success': True, 'message': 'SearXNG stopped'}
            
            # Try docker
            if self._has_command('docker'):
                subprocess.run(['docker', 'stop', 'ryx-searxng'], capture_output=True)
                return {'success': True, 'message': 'SearXNG stopped'}
            
            # Try local PID
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                self.pid_file.unlink()
                return {'success': True, 'message': 'SearXNG stopped'}
            
            return {'success': False, 'error': 'SearXNG not found'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _update_ryx_config(self):
        """Update ryx_config.json with SearXNG URL"""
        config_path = get_project_root() / 'configs' / 'ryx_config.json'
        
        try:
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
            else:
                config = {}
            
            if 'search' not in config:
                config['search'] = {}
            
            config['search']['searxng_url'] = f'http://localhost:{self.DEFAULT_PORT}'
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception:
            # Non-critical, continue anyway
            pass


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
