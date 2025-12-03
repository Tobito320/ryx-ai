"""
Ryx AI - SearXNG Client

Async client for SearXNG meta-search engine.
Used by worker agents for parallel search.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result"""
    title: str
    url: str
    content: str
    engine: str
    score: float = 0.0


class SearXNGClient:
    """
    Async SearXNG client for meta-search.
    
    SearXNG aggregates results from multiple search engines
    (Google, DuckDuckGo, Bing, etc.) without tracking.
    """
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(
        self,
        query: str,
        categories: List[str] = None,
        engines: List[str] = None,
        language: str = "en",
        num_results: int = 10
    ) -> List[SearchResult]:
        """
        Search using SearXNG.
        
        Args:
            query: Search query
            categories: Categories like 'general', 'images', 'news'
            engines: Specific engines like 'google', 'duckduckgo'
            language: Language code
            num_results: Max results to return
            
        Returns:
            List of SearchResult objects
        """
        params = {
            "q": query,
            "format": "json",
            "language": language,
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)
        
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.base_url}/search",
                params=params
            ) as resp:
                if resp.status != 200:
                    logger.error(f"SearXNG error: HTTP {resp.status}")
                    return []
                
                data = await resp.json()
                results = []
                
                for item in data.get("results", [])[:num_results]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=item.get("content", ""),
                        engine=item.get("engine", "unknown"),
                        score=item.get("score", 0.0)
                    ))
                
                return results
                
        except asyncio.TimeoutError:
            logger.error("SearXNG timeout")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"SearXNG connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"SearXNG error: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if SearXNG is running"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/healthz") as resp:
                return resp.status == 200
        except:
            # Try search endpoint as fallback
            try:
                session = await self._get_session()
                async with session.get(
                    f"{self.base_url}/search",
                    params={"q": "test", "format": "json"}
                ) as resp:
                    return resp.status == 200
            except:
                return False


# Singleton
_client: Optional[SearXNGClient] = None


def get_searxng() -> SearXNGClient:
    """Get SearXNG client singleton"""
    global _client
    if _client is None:
        import os
        base_url = os.environ.get("SEARXNG_URL", "http://localhost:8888")
        _client = SearXNGClient(base_url)
    return _client
