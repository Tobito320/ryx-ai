"""
Ryx AI - Supervisor Agent

The Supervisor is the brain of the council:
- Receives user requests
- Breaks them into tasks
- Assigns workers
- Aggregates and synthesizes results
- Applies response style
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .worker import WorkerPool, WorkerTask, WorkerResult, WorkerType
from .metrics import ModelMetrics
from .searxng import SearXNGClient, get_searxng

logger = logging.getLogger(__name__)


class ResponseStyle(Enum):
    """Response styles for the supervisor"""
    NORMAL = "normal"           # Balanced
    CONCISE = "concise"         # Short, to the point
    EXPLANATORY = "explanatory" # Detailed explanations
    LEARNING = "learning"       # Educational, step-by-step
    FORMAL = "formal"           # Professional tone


@dataclass
class SupervisorConfig:
    """Configuration for the supervisor"""
    model: str = "/models/medium/general/qwen2.5-7b-gptq"
    vllm_base_url: str = "http://localhost:8001"
    num_workers: int = 5
    style: ResponseStyle = ResponseStyle.NORMAL
    max_retries: int = 3


class Supervisor:
    """
    The Supervisor orchestrates the council of workers.
    
    Responsibilities:
    - Parse user intent
    - Decide which workers to use
    - Aggregate worker results
    - Generate final response
    - Track model metrics
    """
    
    # Style-specific prompts
    STYLE_PROMPTS = {
        ResponseStyle.NORMAL: "Provide a balanced, helpful response.",
        ResponseStyle.CONCISE: "Be extremely brief. Maximum 2-3 sentences. No fluff.",
        ResponseStyle.EXPLANATORY: "Explain thoroughly with examples and context. Help the user understand deeply.",
        ResponseStyle.LEARNING: "Teach step-by-step. Assume the user wants to learn. Use analogies.",
        ResponseStyle.FORMAL: "Use professional, formal language. Be precise and structured."
    }
    
    def __init__(self, config: SupervisorConfig = None):
        self.config = config or SupervisorConfig()
        self.worker_pool = WorkerPool(
            num_workers=self.config.num_workers,
            vllm_base_url=self.config.vllm_base_url
        )
        self.metrics = ModelMetrics()
        self._searxng = None
    
    @property
    def searxng(self) -> SearXNGClient:
        """Get SearXNG client"""
        if self._searxng is None:
            self._searxng = get_searxng()
        return self._searxng
    
    async def _call_supervisor_model(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024
    ) -> str:
        """Call the supervisor's 7B model"""
        import aiohttp
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.vllm_base_url}/v1/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Supervisor model error: HTTP {resp.status}")
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    async def _refine_prompt(self, user_input: str, context: Dict[str, Any] = None) -> tuple[str, bool]:
        """
        Refine the user's prompt for better agent performance.
        
        - Fix typos
        - Clarify intent
        - Handle follow-up queries like "shorter", "more", "explain"
        - Make it specific and actionable
        
        Returns:
            Tuple of (refined_prompt, is_follow_up)
        """
        # Check if this is a follow-up/modification request
        follow_up_patterns = {
            "shorter": "Make this response much shorter (2-3 sentences max)",
            "kürzer": "Make this response much shorter (2-3 sentences max)", 
            "more": "Expand on this with more detail",
            "mehr": "Expand on this with more detail",
            "explain": "Explain this in more detail with examples",
            "erkläre": "Explain this in more detail with examples",
            "simpler": "Simplify this explanation",
            "einfacher": "Simplify this explanation",
        }
        
        lower_input = user_input.lower().strip()
        
        # Direct follow-up command with context?
        if lower_input in follow_up_patterns and context and context.get("last_response"):
            return (f"{follow_up_patterns[lower_input]}:\n\n{context['last_response'][:800]}", True)
        
        # Short input that looks like a follow-up?
        if len(user_input.split()) <= 3 and context and context.get("last_response"):
            # Check if it's a refinement request
            refinement_words = ["shorter", "longer", "simpler", "detailed", "more", "less",
                               "kürzer", "länger", "einfacher", "mehr", "weniger"]
            if any(w in lower_input for w in refinement_words):
                return (f"{user_input.capitalize()} this response:\n\n{context['last_response'][:500]}", True)
        
        refine_prompt = f"""You are a prompt refinement assistant. 
Your job is to take a user's informal query and refine it into a clear, specific prompt.

User input: "{user_input}"

Rules:
1. Fix any typos or grammatical errors
2. Keep the original intent
3. Make it specific and actionable
4. If it's a question, keep it as a question
5. Don't add information the user didn't ask for
6. Output ONLY the refined prompt, nothing else

Refined prompt:"""

        try:
            refined = await self._call_supervisor_model(
                prompt=refine_prompt,
                max_tokens=150
            )
            # Clean up the response
            refined = refined.strip().strip('"').strip("'")
            return (refined if refined else user_input, False)
        except:
            return (user_input, False)
    
    def _is_search_query(self, query: str) -> bool:
        """Detect if query needs web search"""
        search_indicators = [
            "what is", "who is", "how to", "why does", "when did",
            "was ist", "wer ist", "wie", "warum", "wann",
            "explain", "define", "search", "find", "look up",
            "erkläre", "suche", "finde",
            "?",  # Questions often need search
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in search_indicators)
    
    async def handle_search(
        self,
        query: str,
        style: ResponseStyle = None
    ) -> Dict[str, Any]:
        """
        Handle a search query using parallel workers.
        
        Args:
            query: User's search query
            style: Response style to use
            
        Returns:
            Dict with response and sources
        """
        style = style or self.config.style
        start_time = datetime.now()
        
        # Step 1: Parallel search using workers
        search_results = await self.worker_pool.parallel_search(
            query=query,
            num_searches=3
        )
        
        # Collect all search content
        all_content = []
        sources = []
        
        for result in search_results:
            if result.success and result.result:
                all_content.append(result.result)
                # Parse sources from result
                for line in result.result.split("\n"):
                    if line.strip().startswith("["):
                        sources.append(line.strip())
        
        if not all_content:
            # Fallback: direct SearXNG search
            direct_results = await self.searxng.search(query, num_results=5)
            for r in direct_results:
                all_content.append(f"{r.title}: {r.content}")
                sources.append(f"[{len(sources)+1}] {r.title} - {r.url}")
        
        # Step 2: Supervisor synthesizes the results
        synthesis_prompt = f"""Based on these search results, answer the user's question: "{query}"

Search Results:
{chr(10).join(all_content[:3])}

{self.STYLE_PROMPTS[style]}
Include citation numbers [1], [2], etc. when referencing sources."""
        
        try:
            response = await self._call_supervisor_model(
                prompt=synthesis_prompt,
                system="You are a helpful assistant that synthesizes search results into clear answers.",
                max_tokens=512 if style == ResponseStyle.CONCISE else 1024
            )
            
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record metrics
            for result in search_results:
                if result.model_used:
                    self.metrics.record_task(
                        model_name=result.model_used,
                        success=result.success,
                        latency_ms=result.latency_ms,
                        quality_score=7.0 if result.success else 3.0
                    )
            
            return {
                "response": response,
                "sources": sources[:10],
                "latency_ms": latency,
                "workers_used": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Supervisor synthesis error: {e}")
            return {
                "response": f"Search found results but synthesis failed: {e}",
                "sources": sources[:10],
                "error": str(e)
            }
    
    async def handle_query(
        self,
        query: str,
        style: ResponseStyle = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle any user query.
        
        Args:
            query: User's input
            style: Response style
            context: Additional context (includes last_response for follow-ups)
            
        Returns:
            Dict with response and metadata
        """
        style = style or self.config.style
        context = context or {}
        
        # Step 1: Refine the user's prompt (with context for follow-ups)
        refined_query, is_follow_up = await self._refine_prompt(query, context)
        logger.debug(f"Refined: '{query}' → '{refined_query}' (follow_up={is_follow_up})")
        
        # Step 2: If follow-up, respond directly (no search needed)
        if is_follow_up:
            try:
                response = await self._call_supervisor_model(
                    prompt=refined_query,
                    system=self.STYLE_PROMPTS[style],
                    max_tokens=256 if "shorter" in query.lower() or "kürzer" in query.lower() else 512
                )
                return {
                    "response": response,
                    "sources": [],
                    "type": "follow_up"
                }
            except Exception as e:
                logger.error(f"Follow-up error: {e}")
                return {"response": f"Error: {e}", "error": str(e)}
        
        # Step 3: Check if this needs search
        if self._is_search_query(refined_query):
            return await self.handle_search(refined_query, style)
        
        # Step 4: Simple query - use supervisor model directly
        try:
            response = await self._call_supervisor_model(
                prompt=refined_query,
                system=self.STYLE_PROMPTS[style],
                max_tokens=512 if style == ResponseStyle.CONCISE else 1024
            )
            
            return {
                "response": response,
                "sources": [],
                "type": "direct"
            }
            
        except Exception as e:
            logger.error(f"Supervisor query error: {e}")
            return {
                "response": f"Error: {e}",
                "error": str(e)
            }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get performance metrics for display"""
        return self.metrics.get_summary()
    
    def set_style(self, style: str) -> bool:
        """Set response style"""
        try:
            self.config.style = ResponseStyle(style.lower())
            return True
        except ValueError:
            return False


# Singleton
_supervisor: Optional[Supervisor] = None


def get_supervisor() -> Supervisor:
    """Get supervisor singleton"""
    global _supervisor
    if _supervisor is None:
        import os
        config = SupervisorConfig(
            vllm_base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8001"),
            model=os.environ.get("SUPERVISOR_MODEL", "/models/medium/general/qwen2.5-7b-gptq")
        )
        _supervisor = Supervisor(config)
    return _supervisor


def reset_supervisor():
    """Reset supervisor (useful for testing)"""
    global _supervisor
    _supervisor = None
