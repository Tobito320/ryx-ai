"""
Ryx AI - Multi-Agent Search System

Supervisor dispatches search queries to multiple small agents in parallel,
then synthesizes results based on user's preferred style.

Architecture:
- Supervisor (7B): Understands query, dispatches, synthesizes
- Search Agents (1.5B-3B): Execute searches via SearXNG
- Rating System: Tracks agent performance over time
"""

import os
import json
import asyncio
import aiohttp
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseStyle(Enum):
    """Available response styles"""
    NORMAL = "normal"
    CONCISE = "concise"
    EXPLANATORY = "explanatory"
    LEARNING = "learning"
    FORMAL = "formal"


@dataclass
class SearchResult:
    """Result from a single search agent"""
    agent_id: str
    query: str
    results: List[Dict[str, Any]]
    summary: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None
    quality_score: float = 0.0


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    agent_id: str
    model: str
    total_queries: int = 0
    successful_queries: int = 0
    total_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.successful_queries / self.total_queries
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.total_latency_ms / self.total_queries


class SearchAgent:
    """
    Small model agent that executes search queries.
    Uses SearXNG for search, vLLM model for summarization.
    """
    
    def __init__(
        self,
        agent_id: str,
        vllm_url: str = None,
        searxng_url: str = None,
        model: str = None  # Will auto-detect from vLLM
    ):
        self.agent_id = agent_id
        # Use environment variables with fallbacks
        self.vllm_url = (vllm_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8001")).rstrip('/')
        self.searxng_url = (searxng_url or os.environ.get("SEARXNG_URL", "http://localhost:8888")).rstrip('/')
        self.model = model or self._detect_model()
        self.metrics = AgentMetrics(agent_id=agent_id, model=self.model)
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _detect_model(self) -> str:
        """Detect which model vLLM is serving"""
        import requests
        try:
            resp = requests.get(f"{self.vllm_url}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    return models[0]["id"]
        except:
            pass
        return "/models/medium/general/qwen2.5-7b-gptq"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, query: str, num_results: int = 3) -> SearchResult:
        """Execute search and return summarized results"""
        start_time = time.time()
        
        try:
            # 1. Search via SearXNG
            results = await self._searxng_search(query, num_results)
            
            if not results:
                return SearchResult(
                    agent_id=self.agent_id,
                    query=query,
                    results=[],
                    error="No search results"
                )
            
            # 2. Summarize results with small model
            summary = await self._summarize_results(query, results)
            
            latency = (time.time() - start_time) * 1000
            
            # Update metrics
            self.metrics.total_queries += 1
            self.metrics.successful_queries += 1
            self.metrics.total_latency_ms += latency
            self.metrics.last_used = datetime.now()
            
            return SearchResult(
                agent_id=self.agent_id,
                query=query,
                results=results,
                summary=summary,
                latency_ms=latency
            )
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.metrics.total_queries += 1
            self.metrics.total_latency_ms += latency
            
            return SearchResult(
                agent_id=self.agent_id,
                query=query,
                results=[],
                error=str(e),
                latency_ms=latency
            )
    
    async def _searxng_search(self, query: str, num_results: int) -> List[Dict]:
        """Search via SearXNG API"""
        session = await self._get_session()
        
        params = {
            "q": query,
            "format": "json",
            "engines": "duckduckgo,google",
            "language": "auto"
        }
        
        try:
            async with session.get(
                f"{self.searxng_url}/search",
                params=params
            ) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                results = data.get("results", [])[:num_results]
                
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500]
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"SearXNG search failed: {e}")
            return []
    
    async def _summarize_results(self, query: str, results: List[Dict]) -> str:
        """Use LLM to summarize search results"""
        session = await self._get_session()
        
        # Format results for prompt
        results_text = "\n".join([
            f"- {r['title']}: {r['content']}"
            for r in results
        ])
        
        prompt = f"""Based on these search results, briefly answer: {query}

Results:
{results_text}

Answer in 1-2 sentences. Be factual."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
        
        try:
            async with session.post(
                f"{self.vllm_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    return ""
                
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ""


class SearchSupervisor:
    """
    Supervisor that manages search agents.
    
    - Dispatches queries to multiple agents in parallel
    - Synthesizes results based on user's style preference
    - Rates and manages agent performance
    """
    
    STYLE_PROMPTS = {
        ResponseStyle.NORMAL: "Provide a balanced, helpful answer.",
        ResponseStyle.CONCISE: "Answer in maximum 2 sentences. Be extremely brief.",
        ResponseStyle.EXPLANATORY: "Explain in detail with examples. Be thorough.",
        ResponseStyle.LEARNING: "Explain like a teacher. Use analogies and build understanding step by step.",
        ResponseStyle.FORMAL: "Use formal, academic language. Be precise and professional."
    }
    
    def __init__(
        self,
        vllm_url: str = None,
        searxng_url: str = None,
        num_agents: int = 3,
        model: str = None  # Auto-detect from vLLM
    ):
        # Use environment variables with fallbacks
        self.vllm_url = (vllm_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8001")).rstrip('/')
        self.searxng_url = searxng_url or os.environ.get("SEARXNG_URL", "http://localhost:8888")
        
        # Auto-detect model from vLLM
        if model is None:
            import requests
            try:
                resp = requests.get(f"{self.vllm_url}/v1/models", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        model = models[0]["id"]
            except:
                pass
        self.model = model or "/models/medium/general/qwen2.5-7b-gptq"
        
        # Create search agents
        self.agents: List[SearchAgent] = [
            SearchAgent(
                agent_id=f"search-{i}",
                vllm_url=vllm_url,
                searxng_url=searxng_url,
                model=model  # Same model for now, will use smaller later
            )
            for i in range(num_agents)
        ]
        
        # Style preference (persisted)
        self.style = ResponseStyle.NORMAL
        self._load_style()
        
        # Last search results (for /sources)
        self.last_results: List[SearchResult] = []
        self.last_sources: List[Dict] = []
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _load_style(self):
        """Load style preference from config"""
        config_path = Path.home() / ".config" / "ryx" / "style.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                self.style = ResponseStyle(data.get("style", "normal"))
            except:
                pass
    
    def _save_style(self):
        """Save style preference to config"""
        config_path = Path.home() / ".config" / "ryx" / "style.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"style": self.style.value}))
    
    def set_style(self, style_name: str) -> bool:
        """Set response style"""
        try:
            self.style = ResponseStyle(style_name.lower())
            self._save_style()
            return True
        except ValueError:
            return False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close all sessions"""
        for agent in self.agents:
            await agent.close()
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, query: str) -> str:
        """
        Execute parallel search with all agents and synthesize result.
        
        Returns synthesized answer based on current style.
        """
        # Run all agents in parallel
        tasks = [agent.search(query) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        valid_results: List[SearchResult] = []
        for r in results:
            if isinstance(r, SearchResult) and not r.error:
                valid_results.append(r)
        
        if not valid_results:
            return "Sorry, I couldn't find any information about that."
        
        # Store for /sources command
        self.last_results = valid_results
        self.last_sources = []
        for r in valid_results:
            for source in r.results:
                if source not in self.last_sources:
                    self.last_sources.append(source)
        
        # Synthesize based on style
        answer = await self._synthesize(query, valid_results)
        
        # Rate agents based on latency and quality
        self._rate_agents(valid_results)
        
        return answer
    
    async def _synthesize(self, query: str, results: List[SearchResult]) -> str:
        """Synthesize final answer from multiple agent results"""
        session = await self._get_session()
        
        # Combine summaries from agents
        summaries = "\n".join([
            f"Source {i+1}: {r.summary}"
            for i, r in enumerate(results)
            if r.summary
        ])
        
        if not summaries:
            # Fallback to raw results
            all_results = []
            for r in results:
                all_results.extend(r.results)
            summaries = "\n".join([
                f"- {r['title']}: {r['content'][:200]}"
                for r in all_results[:5]
            ])
        
        style_instruction = self.STYLE_PROMPTS.get(self.style, self.STYLE_PROMPTS[ResponseStyle.NORMAL])
        
        prompt = f"""Answer this question based on the search results below.

Question: {query}

Search Results:
{summaries}

Style: {style_instruction}

Answer:"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        try:
            async with session.post(
                f"{self.vllm_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    return results[0].summary if results else "Search failed."
                
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return results[0].summary if results else "Search failed."
    
    def _rate_agents(self, results: List[SearchResult]):
        """Rate agents based on performance"""
        if not results:
            return
        
        # Find fastest agent
        fastest = min(results, key=lambda r: r.latency_ms)
        
        for r in results:
            # Quality score based on summary length and latency
            base_score = 0.5
            
            # Bonus for being fast
            if r.latency_ms == fastest.latency_ms:
                base_score += 0.3
            
            # Bonus for having summary
            if r.summary:
                base_score += 0.2
            
            r.quality_score = min(1.0, base_score)
            
            # Update agent metrics
            for agent in self.agents:
                if agent.agent_id == r.agent_id:
                    # Running average of quality score
                    n = agent.metrics.total_queries
                    old_avg = agent.metrics.avg_quality_score
                    agent.metrics.avg_quality_score = (old_avg * (n-1) + r.quality_score) / n
    
    def get_sources(self) -> List[Dict]:
        """Get sources from last search"""
        return self.last_sources
    
    def get_metrics(self) -> Dict[str, AgentMetrics]:
        """Get all agent metrics"""
        return {agent.agent_id: agent.metrics for agent in self.agents}
    
    def fire_worst_agent(self):
        """Replace worst performing agent with a copy of the best"""
        if len(self.agents) < 2:
            return
        
        # Find best and worst
        sorted_agents = sorted(
            self.agents,
            key=lambda a: (a.metrics.success_rate, a.metrics.avg_quality_score),
            reverse=True
        )
        
        best = sorted_agents[0]
        worst = sorted_agents[-1]
        
        if worst.metrics.total_queries < 10:
            # Not enough data to judge
            return
        
        if worst.metrics.success_rate < 0.5 or worst.metrics.avg_quality_score < 0.3:
            # Replace worst with clone of best
            logger.info(f"Firing {worst.agent_id}, replacing with clone of {best.agent_id}")
            idx = self.agents.index(worst)
            self.agents[idx] = SearchAgent(
                agent_id=f"search-{idx}",
                vllm_url=self.vllm_url,
                searxng_url=self.searxng_url,
                model=best.model
            )


# Singleton instance
_supervisor: Optional[SearchSupervisor] = None


def get_search_supervisor() -> SearchSupervisor:
    """Get or create search supervisor singleton"""
    global _supervisor
    if _supervisor is None:
        _supervisor = SearchSupervisor(
            vllm_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8001"),
            searxng_url=os.environ.get("SEARXNG_URL", "http://localhost:8888")
        )
    return _supervisor


async def search_query(query: str, style: Optional[str] = None) -> str:
    """
    Main search function.
    
    Args:
        query: User's question
        style: Optional style override
        
    Returns:
        Synthesized answer
    """
    supervisor = get_search_supervisor()
    
    if style:
        supervisor.set_style(style)
    
    return await supervisor.search(query)


def search_query_sync(query: str, style: Optional[str] = None) -> str:
    """Synchronous wrapper for search_query"""
    return asyncio.run(search_query(query, style))
