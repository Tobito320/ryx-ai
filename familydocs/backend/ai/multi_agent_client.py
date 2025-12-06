"""
Multi-Agent Client - Communicates with vLLM agents
Handles HTTP requests to specialized agent endpoints
"""
import httpx
import logging
from typing import List, Dict, Optional, AsyncGenerator
import json

from config import settings
from ai.agents import Agent, AgentType, get_agent

logger = logging.getLogger(__name__)


class MultiAgentClient:
    """Client for communicating with multiple vLLM agent instances"""

    def __init__(self):
        """Initialize client with agent URLs from config"""
        self.agent_urls = {
            AgentType.CHAT: settings.vllm_chat_agent_url,
            AgentType.DOC_ANALYST: settings.vllm_doc_analyst_url,
            AgentType.BOARD_PLANNER: settings.vllm_board_planner_url,
            AgentType.BRIEF_WRITER: settings.vllm_brief_writer_url,
        }

        # HTTP client with timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def generate(
        self,
        agent: Agent,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict:
        """
        Generate response from an agent

        Args:
            agent: Agent to use
            messages: Chat messages (OpenAI format)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Whether to stream response

        Returns:
            Response dict from vLLM
        """
        # Get agent URL
        agent_url = self.agent_urls.get(agent.type)
        if not agent_url:
            raise ValueError(f"No URL configured for agent {agent.type}")

        # Prepend system message with agent's specialized prompt
        full_messages = [
            {"role": "system", "content": agent.system_prompt},
            *messages
        ]

        # Request payload (OpenAI-compatible)
        payload = {
            "model": agent.model_name,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        try:
            # Make request to vLLM
            response = await self.client.post(
                f"{agent_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Agent {agent.type.value} responded (tokens: {result.get('usage', {}).get('total_tokens', 0)})")

            return result

        except httpx.HTTPError as e:
            logger.error(f"❌ Agent {agent.type.value} request failed: {e}")
            raise

    async def generate_stream(
        self,
        agent: Agent,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from an agent

        Args:
            agent: Agent to use
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max tokens

        Yields:
            Chunks of generated text
        """
        agent_url = self.agent_urls.get(agent.type)
        if not agent_url:
            raise ValueError(f"No URL configured for agent {agent.type}")

        # Prepend system message
        full_messages = [
            {"role": "system", "content": agent.system_prompt},
            *messages
        ]

        payload = {
            "model": agent.model_name,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with self.client.stream(
                "POST",
                f"{agent_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield content

                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPError as e:
            logger.error(f"❌ Streaming failed for agent {agent.type.value}: {e}")
            raise

    async def health_check(self, agent_type: AgentType) -> bool:
        """
        Check if an agent is healthy

        Args:
            agent_type: Agent to check

        Returns:
            True if healthy, False otherwise
        """
        agent_url = self.agent_urls.get(agent_type)
        if not agent_url:
            return False

        try:
            response = await self.client.get(
                f"{agent_url.replace('/v1', '')}/health",
                timeout=5.0
            )
            return response.status_code == 200

        except Exception as e:
            logger.warning(f"⚠️ Health check failed for {agent_type.value}: {e}")
            return False

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all agents

        Returns:
            Dict of agent -> health status
        """
        results = {}
        for agent_type in AgentType:
            results[agent_type.value] = await self.health_check(agent_type)

        return results

    def get_agent_info(self) -> Dict:
        """Get information about all configured agents"""
        return {
            agent_type.value: {
                "name": get_agent(agent_type).name,
                "url": url,
                "model": get_agent(agent_type).model_name
            }
            for agent_type, url in self.agent_urls.items()
        }


# Global client instance
client = MultiAgentClient()
