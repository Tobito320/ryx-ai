"""
SandboxManager - Unified interface for Docker and E2B sandboxes.

Supports:
- Docker sandbox (local, free)
- E2B cloud sandbox (production, managed)

Usage:
    sandbox = SandboxManager(sandbox_type="docker")
    await sandbox.init(websocket)
    result = await sandbox.run_task(code, websocket)
    await sandbox.cleanup(websocket)
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Literal
from datetime import datetime

logger = logging.getLogger(__name__)


class SandboxManager:
    """Unified sandbox manager supporting Docker and E2B"""
    
    def __init__(self, sandbox_type: Literal["docker", "e2b"] = "docker"):
        self.sandbox_type = sandbox_type
        self.sandbox = None
        self.client = None
        self.container = None
        self.sandbox_id: Optional[str] = None
        self.created_at: Optional[str] = None
    
    async def init(self, websocket=None):
        """Initialize sandbox environment"""
        if websocket:
            await websocket.send_json({
                "type": "status",
                "phase": "sandbox_init",
                "message": f"🔒 Initializing {self.sandbox_type} sandbox..."
            })
        
        self.created_at = datetime.utcnow().isoformat()
        
        if self.sandbox_type == "docker":
            await self._init_docker()
        elif self.sandbox_type == "e2b":
            await self._init_e2b()
        
        logger.info(f"Sandbox initialized: {self.sandbox_type} ({self.sandbox_id})")
        
        if websocket:
            await websocket.send_json({
                "type": "status",
                "phase": "sandbox_ready",
                "message": f"✅ Sandbox ready ({self.sandbox_id})"
            })
    
    async def _init_docker(self):
        """Initialize Docker sandbox"""
        try:
            import docker
            self.client = docker.from_env()
            self.sandbox_id = f"ryx-sandbox-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            logger.info(f"Docker client initialized: {self.sandbox_id}")
        except ImportError:
            raise RuntimeError("Docker package not installed. Run: pip install docker")
        except Exception as e:
            raise RuntimeError(f"Docker initialization failed: {e}")
    
    async def _init_e2b(self):
        """Initialize E2B cloud sandbox"""
        try:
            from e2b_code_interpreter import Sandbox
            
            api_key = os.getenv("E2B_API_KEY")
            if not api_key:
                raise RuntimeError("E2B_API_KEY environment variable not set")
            
            self.sandbox = await Sandbox.create(api_key=api_key)
            self.sandbox_id = self.sandbox.sandbox_id
            logger.info(f"E2B sandbox created: {self.sandbox_id}")
        except ImportError:
            raise RuntimeError("E2B package not installed. Run: pip install e2b-code-interpreter")
    
    async def run_task(self, task_code: str, websocket=None) -> Dict[str, Any]:
        """Execute task in sandbox"""
        if websocket:
            await websocket.send_json({
                "type": "status",
                "phase": "sandbox_executing",
                "message": "⚙️ Executing in sandbox..."
            })
        
        try:
            if self.sandbox_type == "e2b":
                return await self._run_e2b(task_code, websocket)
            elif self.sandbox_type == "docker":
                return await self._run_docker(task_code, websocket)
        except Exception as e:
            logger.exception("Sandbox task execution failed")
            return {"status": "error", "error": str(e)}
    
    async def _run_e2b(self, code: str, websocket=None) -> Dict[str, Any]:
        """Run code in E2B sandbox"""
        if not self.sandbox:
            raise RuntimeError("E2B sandbox not initialized")
        
        result = await self.sandbox.run_code(code)
        
        return {
            "status": "success",
            "stdout": result.text,
            "stderr": result.error,
            "logs": result.logs,
            "results": result.results
        }
    
    async def _run_docker(self, code: str, websocket=None) -> Dict[str, Any]:
        """Run code in Docker sandbox"""
        if not self.client:
            raise RuntimeError("Docker client not initialized")
        
        try:
            # Run container with strict limits
            self.container = self.client.containers.run(
                "ryx-agent:sandbox",
                command=["exec", code],
                mem_limit="2g",
                cpu_quota=100000,
                network_mode="bridge",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                user="1000:1000",
                remove=False,  # Keep for logs
                detach=True
            )
            
            # Wait for completion with timeout
            result = self.container.wait(timeout=60)
            logs = self.container.logs().decode('utf-8')
            
            # Parse JSON output if possible
            try:
                output = json.loads(logs.strip().split('\n')[-1])
            except json.JSONDecodeError:
                output = {"raw_output": logs}
            
            return {
                "status": "success" if result['StatusCode'] == 0 else "error",
                "exit_code": result['StatusCode'],
                "logs": logs,
                "output": output
            }
        
        except Exception as e:
            if self.container:
                try:
                    self.container.kill()
                except:
                    pass
            raise RuntimeError(f"Docker execution failed: {e}")
    
    async def run_browser_action(self, url: str, websocket=None) -> Dict[str, Any]:
        """Run browser action in sandbox"""
        if websocket:
            await websocket.send_json({
                "type": "status",
                "phase": "browser_action",
                "message": f"🌐 Navigating to {url}..."
            })
        
        if self.sandbox_type == "docker":
            return await self._docker_browser(url, websocket)
        elif self.sandbox_type == "e2b":
            return await self._e2b_browser(url, websocket)
    
    async def _docker_browser(self, url: str, websocket=None) -> Dict[str, Any]:
        """Browser action in Docker sandbox"""
        if not self.client:
            raise RuntimeError("Docker client not initialized")
        
        self.container = self.client.containers.run(
            "ryx-agent:sandbox",
            command=["browse", url],
            mem_limit="2g",
            cpu_quota=100000,
            network_mode="bridge",
            remove=False,
            detach=True
        )
        
        result = self.container.wait(timeout=60)
        logs = self.container.logs().decode('utf-8')
        
        try:
            output = json.loads(logs.strip().split('\n')[-1])
        except json.JSONDecodeError:
            output = {"raw_output": logs}
        
        return output
    
    async def _e2b_browser(self, url: str, websocket=None) -> Dict[str, Any]:
        """Browser action in E2B sandbox"""
        code = f'''
import httpx
response = httpx.get("{url}", timeout=30)
print(f"Status: {{response.status_code}}")
print(f"Content length: {{len(response.text)}}")
with open("/output/page.html", "w") as f:
    f.write(response.text)
'''
        return await self._run_e2b(code, websocket)
    
    async def upload_file(self, local_path: str, sandbox_path: str = "/workspace"):
        """Upload file to sandbox"""
        if self.sandbox_type == "e2b" and self.sandbox:
            with open(local_path, 'rb') as f:
                await self.sandbox.upload_file(f, sandbox_path)
        elif self.sandbox_type == "docker":
            # Docker uses volume mounts, copy to workspace dir
            import shutil
            workspace = os.path.join(os.path.dirname(__file__), "sandbox/workspace")
            os.makedirs(workspace, exist_ok=True)
            shutil.copy(local_path, workspace)
    
    async def download_file(self, sandbox_path: str, local_path: str):
        """Download file from sandbox"""
        if self.sandbox_type == "e2b" and self.sandbox:
            content = await self.sandbox.download_file(sandbox_path)
            with open(local_path, 'wb') as f:
                f.write(content)
        elif self.sandbox_type == "docker":
            # Read from output volume
            output_dir = "/tmp/sandbox_output"
            src = os.path.join(output_dir, os.path.basename(sandbox_path))
            if os.path.exists(src):
                import shutil
                shutil.copy(src, local_path)
    
    async def cleanup(self, websocket=None):
        """Destroy sandbox and cleanup resources"""
        if websocket:
            await websocket.send_json({
                "type": "status",
                "phase": "sandbox_cleanup",
                "message": "🗑️ Destroying sandbox..."
            })
        
        try:
            if self.sandbox_type == "e2b" and self.sandbox:
                await self.sandbox.close()
                self.sandbox = None
            
            if self.sandbox_type == "docker":
                if self.container:
                    try:
                        self.container.remove(force=True)
                    except:
                        pass
                    self.container = None
            
            logger.info(f"Sandbox destroyed: {self.sandbox_id}")
            
            if websocket:
                await websocket.send_json({
                    "type": "status",
                    "phase": "sandbox_destroyed",
                    "message": "✅ Sandbox destroyed"
                })
        
        except Exception as e:
            logger.warning(f"Sandbox cleanup error: {e}")
    
    async def __aenter__(self):
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# Convenience function
async def create_sandbox(sandbox_type: str = "docker", websocket=None) -> SandboxManager:
    """Create and initialize a sandbox"""
    sandbox = SandboxManager(sandbox_type=sandbox_type)
    await sandbox.init(websocket)
    return sandbox
