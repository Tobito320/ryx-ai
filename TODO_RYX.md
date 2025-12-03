# Ryx Improvement TODO

## Critical Issues Fixed ✅
- [x] Removed Ollama completely - now using vLLM only
- [x] Intent detection improved - "erstelle Lern-Tabelle" no longer creates code
- [x] Search now triggers for educational topics (axiome, theorie, lern, etc.)
- [x] /style command works (normal, concise, explanatory, learning, formal)
- [x] /sources command shows search sources

## Issues Still Present
- [ ] **Hallucination on educational content** - Model doesn't follow search results well
  - Root cause: SearXNG returns snippets, not full page content
  - Fix needed: Add page scraping for educational topics
  
- [ ] **Double Ctrl+C to exit** - Currently single Ctrl+C exits
  - Need to implement interrupt handling

- [ ] **Multi-agent search not connected** - search_agents.py exists but not integrated
  - The parallel vLLM requests work but agents aren't orchestrating

## Next Steps
1. Implement page scraper for educational content (get full article text)
2. Add double Ctrl+C handling
3. Connect multi-agent system to main brain
4. Test with real user scenarios

## Architecture Notes
- vLLM running on port 8000 with Qwen2.5-7B-GPTQ
- SearXNG running on port 8888
- Session state persists in data/session_state.json
- Response style persists across sessions
