#!/usr/bin/env python3
"""
Tests for search agent failover to backup SearXNG endpoint.
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer


@pytest.mark.anyio
async def test_search_agent_uses_backup_on_primary_failure():
    """SearchAgent should fall back to backup endpoint when primary fails."""
    primary_app = web.Application()
    
    async def primary_handler(_):
        return web.Response(status=500)
    
    primary_app.router.add_get("/search", primary_handler)
    
    backup_app = web.Application()
    
    async def backup_handler(request):
        return web.json_response(
            {"results": [{"title": "ok", "url": "http://example.com", "content": "content"}]}
        )
    
    backup_app.router.add_get("/search", backup_handler)
    
    primary_server = TestServer(primary_app)
    backup_server = TestServer(backup_app)
    agent = None
    
    await primary_server.start_server()
    await backup_server.start_server()
    
    try:
        primary_url = str(primary_server.make_url("")).rstrip("/")
        backup_url = str(backup_server.make_url("")).rstrip("/")
        
        from core.search_agents import SearchAgent
        
        class TestSearchAgent(SearchAgent):
            async def _summarize_results(self, query, results):
                return "summary"
        
        agent = TestSearchAgent(
            "test-agent",
            vllm_url="http://127.0.0.1:1",  # avoid real model call
            searxng_url=primary_url,
            backup_searxng_url=backup_url,
        )
        
        result = await agent.search("ryx ai", num_results=1)
        
        assert not result.error
        assert result.results
        assert result.results[0]["title"] == "ok"
        assert result.summary == "summary"
    finally:
        if agent:
            await agent.close()
        await primary_server.close()
        await backup_server.close()
