"""
Model Router for Multi-Instance vLLM
Routes requests to the appropriate vLLM instance based on model ID.
"""

import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio


@dataclass
class ModelInstance:
    """Configuration for a vLLM model instance."""
    model_id: str
    name: str
    base_url: str
    port: int
    status: str = "unknown"
    category: str = "general"
    size: str = "medium"


class ModelRouter:
    """
    Routes inference requests to the appropriate vLLM instance.

    Supports multiple vLLM instances running on different ports,
    each serving a different model. Automatically routes requests
    based on the model ID.
    """

    def __init__(self):
        # Map model IDs to their vLLM instances
        self.instances: Dict[str, ModelInstance] = {
            "/models/medium/general/qwen2.5-7b-gptq": ModelInstance(
                model_id="/models/medium/general/qwen2.5-7b-gptq",
                name="Qwen 2.5 7B GPTQ",
                base_url="http://localhost:8001",
                port=8001,
                category="general",
                size="medium"
            ),
            "/models/medium/coding/qwen2.5-coder-7b-gptq": ModelInstance(
                model_id="/models/medium/coding/qwen2.5-coder-7b-gptq",
                name="Qwen 2.5 Coder 7B GPTQ",
                base_url="http://localhost:8002",
                port=8002,
                category="coding",
                size="medium"
            ),
            "/models/small/general/qwen2.5-3b": ModelInstance(
                model_id="/models/small/general/qwen2.5-3b",
                name="Qwen 2.5 3B",
                base_url="http://localhost:8003",
                port=8003,
                category="general",
                size="small"
            ),
        }

        # Default instance (fallback)
        self.default_instance = "/models/medium/general/qwen2.5-7b-gptq"

    async def check_health(self, model_id: str) -> bool:
        """Check if a specific model instance is healthy."""
        instance = self.instances.get(model_id)
        if not instance:
            return False

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{instance.base_url}/health") as resp:
                    if resp.status == 200:
                        instance.status = "online"
                        return True
        except Exception:
            pass

        instance.status = "offline"
        return False

    async def check_all_health(self) -> Dict[str, bool]:
        """Check health of all model instances."""
        tasks = [self.check_health(model_id) for model_id in self.instances.keys()]
        results = await asyncio.gather(*tasks)
        return {
            model_id: result
            for model_id, result in zip(self.instances.keys(), results)
        }

    def get_instance(self, model_id: Optional[str] = None) -> ModelInstance:
        """Get the vLLM instance for a specific model."""
        if not model_id or model_id not in self.instances:
            model_id = self.default_instance
        return self.instances[model_id]

    def list_models(self) -> List[ModelInstance]:
        """List all configured model instances."""
        return list(self.instances.values())

    async def route_request(
        self,
        model_id: str,
        endpoint: str,
        method: str = "POST",
        **kwargs
    ) -> Any:
        """
        Route a request to the appropriate vLLM instance.

        Args:
            model_id: The model to use
            endpoint: API endpoint (e.g., "/v1/chat/completions")
            method: HTTP method
            **kwargs: Additional arguments to pass to the request

        Returns:
            The response from the vLLM instance
        """
        instance = self.get_instance(model_id)
        url = f"{instance.base_url}{endpoint}"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.request(method, url, **kwargs) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"vLLM error: {error_text}")

                return await resp.json()

    async def start_instance(self, model_id: str) -> Dict[str, Any]:
        """
        Start a specific model instance.

        Note: This requires the docker-compose file to be running.
        This function only checks if the instance is available.
        """
        instance = self.instances.get(model_id)
        if not instance:
            return {
                "success": False,
                "message": f"Unknown model: {model_id}",
                "status": "not_found"
            }

        # Check if instance is running
        is_healthy = await self.check_health(model_id)
        if is_healthy:
            return {
                "success": True,
                "message": f"Model {instance.name} is already running on port {instance.port}",
                "status": "online",
                "port": instance.port
            }

        return {
            "success": False,
            "message": f"Model {instance.name} is not running. Start it with: docker-compose -f docker/vllm/model-router.yml up -d vllm-{instance.size}-{instance.category}",
            "status": "offline",
            "instructions": f"docker-compose -f docker/vllm/model-router.yml up -d vllm-{instance.size}-{instance.category}"
        }


# Global router instance
router = ModelRouter()
