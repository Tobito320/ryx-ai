# Ryx Comprehensive TODO - Multi-Agent Self-Improving System

Generated: 2025-12-03

---

## 🎯 PHASE 1: MULTI-AGENT COUNCIL ARCHITECTURE

### 1.1 Supervisor Agent Improvements
- [ ] **Prompt Refinement Engine**: Supervisor should refine vague user prompts into precise agent tasks
  - [ ] Implement prompt optimization heuristics
  - [ ] Test with 100+ real user prompts from learning domain
  - [ ] Add cost tracking (token usage per prompt refinement)
  
- [ ] **Task Complexity Classification**: Categorize incoming tasks (simple, medium, complex)
  - [ ] Define complexity scoring algorithm
  - [ ] Route simple tasks to 1 agent, complex to 3-5 agents
  - [ ] Add decision tree visualization (debug mode)
  
- [ ] **Agent Assignment Logic**: Select best agents for task
  - [ ] Build agent capability matrix (search, code, analysis, etc.)
  - [ ] Implement skill-to-task matching algorithm
  - [ ] Add fairness balancing (rotate agents, prevent starvation)

### 1.2 Parallel Agent Execution
- [ ] **True Async Execution**: Remove all synchronous bottlenecks
  - [ ] Make all agent calls concurrent (currently some are sequential)
  - [ ] Add timeout per agent (configurable, default 30s)
  - [ ] Implement early exit if first agent succeeds (optional)
  
- [ ] **Agent Result Aggregation**: Combine multiple agent outputs
  - [ ] Implement consensus algorithm for multiple agents
  - [ ] Add result quality scoring (relevance, completeness, confidence)
  - [ ] Detect conflicting answers and flag for supervisor review
  
- [ ] **Agent Failure Handling**: Handle individual agent crashes gracefully
  - [ ] Don't stop entire task if 1 agent fails
  - [ ] Automatically promote next-best agent
  - [ ] Log failures per agent and model for metrics
  
- [ ] **Load Balancing**: Distribute work across GPU/CPU
  - [ ] Monitor vLLM queue depth
  - [ ] Throttle new tasks if queue > threshold
  - [ ] Implement priority queue (user task vs background improvement)

---

## 🔍 PHASE 2: SEARCH SYSTEM OVERHAUL

### 2.1 Multi-Agent Search
- [ ] **5 Parallel Search Agents** (using 1.5B-3B models)
  - [ ] Agent A: SearXNG direct search
  - [ ] Agent B: Wikipedia + academic search
  - [ ] Agent C: Reddit/forum analysis
  - [ ] Agent D: Stack Overflow/technical docs
  - [ ] Agent E: Content synthesis from cache
  - [ ] Load balance across 2-3 small models (round-robin)

- [ ] **Search Result Merging**
  - [ ] Remove duplicate results (fuzzy matching on titles)
  - [ ] Rank by relevance score
  - [ ] Combine snippets intelligently
  - [ ] Detect contradictions between sources

- [ ] **Smart Scraping**
  - [ ] Integrate Playwright for full page scraping (not just snippets)
  - [ ] Extract article text, code blocks, tables from pages
  - [ ] Implement cache (store scraped content for 24h)
  - [ ] Add rate limiting (don't scrape same site >2x/min)
  - [ ] Store scraped content in embeddings for RAG

### 2.2 Response Generation with Styles
- [ ] **Style System** (already started, needs completion)
  - [ ] **concise**: 2-3 sentences, bullet points, essential facts only
  - [ ] **explanatory**: Full context, analogies, step-by-step breakdown
  - [ ] **learning**: Scaffolding, questions for reflection, resources
  - [ ] **formal**: Academic tone, citations, proper terminology
  - [ ] **normal**: Balanced, conversational, friendly
  
- [ ] **Context Window Management**
  - [ ] Truncate search results if >8k tokens
  - [ ] Implement smart chunking (keep coherent sections)
  - [ ] Add page references: "[1] Title - URL"
  - [ ] Ensure sources always included, even if truncated

- [ ] **Source Tracking**
  - [ ] Every search response logs sources used
  - [ ] `/sources` command shows sources with access time
  - [ ] Add confidence score per source (0-100%)
  - [ ] Track which sources supervisor actually used

---

## 📊 PHASE 3: BENCHMARK & METRICS SYSTEM

### 3.1 Comprehensive Benchmarks
- [ ] **Search Quality Benchmark**
  - [ ] 50 hand-curated questions (2-3 domain categories)
  - [ ] Expected answers with ground truth
  - [ ] Metric: Answer relevance score (0-100)
  - [ ] Track: Speed, token usage, # agents used
  - [ ] Baseline: Current system performance

- [ ] **Response Quality Benchmark**
  - [ ] Same 50 questions, evaluate response quality
  - [ ] Metric: User satisfaction (simulated with scoring rubric)
  - [ ] Per-style evaluation (concise vs explanatory)
  - [ ] Track: Hallucination rate, completeness

- [ ] **Agent Performance Tracking**
  - [ ] Success rate per agent (%)
  - [ ] Average latency per agent (ms)
  - [ ] Cost per agent (tokens/request)
  - [ ] Reliability score (uptime, crash rate)

- [ ] **System-Level Metrics**
  - [ ] End-to-end latency (user query → response)
  - [ ] Total token cost per query
  - [ ] GPU utilization (%)
  - [ ] Memory usage (GB)
  - [ ] Requests per minute (throughput)

### 3.2 Metrics Dashboard
- [ ] **Per-Model Metrics** (displayed with `/metrics`)
  - [ ] Search: Best models, worst models (ranked by quality)
  - [ ] Analysis: Best models, worst models
  - [ ] Code: Best models, worst models
  - [ ] Reasoning: Best models, worst models
  
- [ ] **Per-Agent Metrics**
  - [ ] Success/failure ratio
  - [ ] Average response time
  - [ ] Reliability score
  - [ ] Specialization score (what it's best at)
  
- [ ] **Historical Tracking**
  - [ ] Track metrics per session
  - [ ] Compare current metrics to baseline
  - [ ] Show improvement/regression trends
  - [ ] Export data for external analysis

---

## 🧠 PHASE 4: SELF-IMPROVEMENT LOOP

### 4.1 Learning from Failures
- [ ] **Failure Classification**
  - [ ] Categorize failures: wrong_answer, timeout, hallucination, incomplete
  - [ ] Root cause analysis (which agent/model failed?)
  - [ ] Store failure patterns in experience database

- [ ] **Alternative Strategies on Failure**
  - [ ] If search fails → try different search keywords (synonym expansion)
  - [ ] If agent timeout → reassign to faster model
  - [ ] If hallucination detected → scrape source material directly
  - [ ] Track which strategies work best

- [ ] **Experience Replay**
  - [ ] Store successful task solutions
  - [ ] On similar future tasks, reuse solution
  - [ ] Example: "explain IPv6" → reuse previous search results

### 4.2 Model Self-Modification (Future)
- [ ] **Safe Code Modification Sandbox**
  - [ ] Supervisor can propose changes to agent prompts
  - [ ] Test changes on benchmark before applying
  - [ ] Rollback if metrics degrade
  - [ ] Version control for agent prompts

- [ ] **Dynamic Agent Configuration**
  - [ ] Adjust timeout based on task complexity
  - [ ] Adjust # agents based on time budget
  - [ ] Adjust model selection based on task type
  - [ ] Learn these adjustments from experience

---

## 🔧 PHASE 5: INFRASTRUCTURE & SERVICES

### 5.1 Docker Service Management
- [ ] **Service Lifecycle Commands**
  - [ ] `ryx start` - Start all services (vLLM, SearXNG, RyxHub)
  - [ ] `ryx stop` - Stop all services gracefully
  - [ ] `ryx status` - Show service status + metrics
  - [ ] `ryx logs <service>` - Tail logs for specific service
  - [ ] `ryx cleanup` - Remove unused Docker images/containers
  
- [ ] **Startup Optimization**
  - [ ] vLLM: Load model async, don't block CLI startup
  - [ ] SearXNG: Pre-warm on startup (first request will be fast)
  - [ ] Health checks on all services before accepting requests
  - [ ] Graceful degradation (search works without vLLM, etc.)

- [ ] **Configuration Management**
  - [ ] Store service config in `configs/services.json`
  - [ ] Allow override with env vars
  - [ ] Support multiple deployment profiles (dev, prod, testing)

### 5.2 Model Management
- [ ] **Model Registry** (`configs/models.json`)
  - [ ] Current structure: categories → models with specs
  - [ ] Add: Load time estimate, VRAM usage, best-for field
  - [ ] Add: Model performance metrics (inference speed, quality)
  
- [ ] **Model Lifecycle**
  - [ ] `ryx model list` - Show all available models
  - [ ] `ryx model load <name>` - Load specific model
  - [ ] `ryx model unload <name>` - Free VRAM
  - [ ] `ryx model metrics <name>` - Performance stats
  
- [ ] **Model Switching**
  - [ ] Allow task-specific model selection
  - [ ] Fall back to backup model if primary times out
  - [ ] Track which models are loaded in memory

### 5.3 Interrupt Handling
- [ ] **Double Ctrl+C to Exit** (not single press)
  - [ ] First Ctrl+C: Cancel current operation, show "Press Ctrl+C again to exit"
  - [ ] Second Ctrl+C (within 2s): Clean shutdown of services
  - [ ] After first Ctrl+C, show remaining operations that can be cancelled
  
- [ ] **Graceful Cancellation**
  - [ ] Cancel in-flight agent requests
  - [ ] Save session state before exit
  - [ ] Warn if unsaved work exists
  - [ ] Kill zombie processes on cleanup

---

## 🎓 PHASE 6: LEARNING DOMAIN FEATURES

### 6.1 Educational Content Recognition
- [ ] **Detect Learning Intent**
  - [ ] Keywords: "learn", "explain", "axiom", "theorem", "definition", "theory"
  - [ ] Language detection (German: "erklär", "lerne", "axiome")
  - [ ] Context analysis (preceding questions, topic domain)
  
- [ ] **Structured Learning Responses**
  - [ ] Learning style: Scaffolding format
  - [ ] Include: Concept → Examples → Practice → Reflection
  - [ ] Add resources: Textbooks, papers, courses
  - [ ] Visual aids: Recommend diagrams if available

### 6.2 Spreadsheet Generation
- [ ] **Learning Spreadsheet Creation**
  - [ ] Parse learning content
  - [ ] Extract concepts, definitions, examples
  - [ ] Generate CSV/XLSX with structure
  - [ ] Format: Concept | Definition | Example | Resources | Difficulty
  
- [ ] **Smart Organization**
  - [ ] Group by complexity level
  - [ ] Cross-reference related concepts
  - [ ] Add prerequisite information
  - [ ] Include practice problems

---

## 🔐 PHASE 7: QUALITY & RELIABILITY

### 7.1 Hallucination Detection
- [ ] **Cross-Reference Checking**
  - [ ] Compare response to search sources
  - [ ] Flag claims not supported by any source
  - [ ] Highlight confidence level per statement
  - [ ] Implement ground truth comparison

- [ ] **Source Attribution**
  - [ ] Every factual claim must have [N] source reference
  - [ ] Missing references = hallucination alert
  - [ ] Track attribution accuracy over time

### 7.2 Error Recovery
- [ ] **Timeout Handling**
  - [ ] If agent timeout > 3: Remove from pool temporarily
  - [ ] Reduce agent count, add more capable model
  - [ ] Alert user if query takes >30s
  
- [ ] **Fallback Strategies**
  - [ ] Simple query timeout → use cached results
  - [ ] Search timeout → use local embeddings (RAG)
  - [ ] All agents timeout → return partial results
  - [ ] All systems down → offline mode with cached info

### 7.3 Session Persistence
- [ ] **State Management**
  - [ ] Save session after each request
  - [ ] Restore on next `ryx` session
  - [ ] Include: Response style, recent queries, context
  - [ ] Periodically clean old sessions (>7 days)

- [ ] **Conversation Memory**
  - [ ] Track multi-turn conversations
  - [ ] Maintain context across messages
  - [ ] Implement sliding window (keep last 10 messages)
  - [ ] Include in future request context

---

## 🚀 PHASE 8: ADVANCED OPTIMIZATIONS

### 8.1 Prompt Engineering
- [ ] **Dynamic Prompt Templates**
  - [ ] Per-task prompt engineering (search vs analysis vs coding)
  - [ ] Few-shot examples for each task type
  - [ ] Chain-of-thought for complex reasoning
  - [ ] Test prompt effectiveness on benchmarks

- [ ] **Model-Specific Prompts**
  - [ ] Different prompts for 1.5B, 3B, 7B, 14B models
  - [ ] Optimize for model capabilities
  - [ ] Implement adaptive prompting based on model feedback

### 8.2 Caching & Optimization
- [ ] **Multi-Level Caching**
  - [ ] L1: Response cache (exact query → exact response)
  - [ ] L2: Embedding cache (similar queries use similar results)
  - [ ] L3: SearXNG result cache (24h TTL)
  - [ ] L4: Scraped content cache (7d TTL)
  - [ ] L5: Model output cache (contextual, 1h TTL)

- [ ] **Smart Resource Usage**
  - [ ] Pre-load frequently-used models
  - [ ] Batch requests to vLLM when possible
  - [ ] Use GPU batching for multiple agents
  - [ ] Monitor memory and swap gracefully

### 8.3 Observability
- [ ] **Logging & Tracing**
  - [ ] Trace request through entire system
  - [ ] Log decision points (which agent picked? why?)
  - [ ] Debug mode: Show intermediate reasoning steps
  - [ ] Export traces for analysis
  
- [ ] **Performance Profiling**
  - [ ] Measure latency per component
  - [ ] Identify bottlenecks (agent wait, search, aggregation)
  - [ ] Create performance timeline visualization
  - [ ] Set SLA targets (e.g., 95th percentile <5s)

---

## 🔄 PHASE 9: CONTINUOUS IMPROVEMENT LOOP

### 9.1 Automated Benchmarking
- [ ] **Regular Benchmark Runs**
  - [ ] Run benchmarks every 24h (cron job)
  - [ ] Compare to baseline + previous run
  - [ ] Alert on regression >5%
  - [ ] Celebrate improvement >10% with logs
  
- [ ] **A/B Testing Framework**
  - [ ] Test new agent configuration on 10% of queries
  - [ ] Compare metrics to baseline (90%)
  - [ ] Automatic rollout if better
  - [ ] Rollback if worse

### 9.2 Model Lifecycle Management
- [ ] **Model Rating System**
  - [ ] Rate each model on multiple axes:
    - [ ] Speed (tokens/sec)
    - [ ] Quality (correctness on benchmarks)
    - [ ] Reliability (crash rate)
    - [ ] Cost (tokens used per query)
  - [ ] Calculate composite score per model
  - [ ] Fire lowest-scoring models periodically
  
- [ ] **Model Replacement**
  - [ ] Monitor for newer model releases
  - [ ] Test new models on benchmarks
  - [ ] Replace underperforming models automatically
  - [ ] Keep version history of model changes

### 9.3 Agent Optimization
- [ ] **Agent Tuning**
  - [ ] Adjust timeout per agent based on performance
  - [ ] Adjust # parallel agents based on task complexity
  - [ ] Optimize agent specialization (focus on strength)
  - [ ] Track optimization effectiveness

- [ ] **Learning System Improvements**
  - [ ] Analyze failed queries
  - [ ] Find common failure patterns
  - [ ] Propose system improvements
  - [ ] Test improvements on benchmarks before deploy

---

## 🎭 PHASE 10: SESSION MODE ENHANCEMENTS

### 10.1 User Experience
- [ ] **Natural Language Commands**
  - [ ] Remove `/search` prefix, just type query
  - [ ] Recognize intent automatically
  - [ ] Auto-select response style based on context
  - [ ] Add smart suggestions when user pauses
  
- [ ] **Interactive Mode Features**
  - [ ] Syntax highlighting for code
  - [ ] Tables for structured data
  - [ ] Progress bars for long operations
  - [ ] Collapsible sections for detailed info

### 10.2 Context & History
- [ ] **Multi-Turn Conversation**
  - [ ] Remember previous questions in session
  - [ ] Use conversation history for context
  - [ ] Allow follow-ups ("tell me more", "summarize")
  - [ ] Implement conversation branching (explore alternative paths)

- [ ] **Quick Access**
  - [ ] `/recent` - Show recent queries and responses
  - [ ] `/export` - Export conversation as PDF/Markdown
  - [ ] `/bookmark` - Save important responses
  - [ ] `/search-history` - Previous search queries

### 10.3 Debugging & Transparency
- [ ] **Debug Mode** (`ryx --debug`)
  - [ ] Show supervisor's reasoning (which agents picked? why?)
  - [ ] Show agent responses before aggregation
  - [ ] Show search queries sent to SearXNG
  - [ ] Show fallback strategies being used
  
- [ ] **Explain Mode** (`ryx --explain`)
  - [ ] After each response, show how it was generated
  - [ ] Which models were used
  - [ ] Which sources were relied on
  - [ ] Confidence levels per claim

---

## 📦 PHASE 11: CODE FEATURES (Lower Priority)

### 11.1 Code Task Improvements
- [ ] **Test-Driven Generation**
  - [ ] Generate tests before code (TDD)
  - [ ] Validate code against tests
  - [ ] Track test coverage
  
- [ ] **Multi-File Context**
  - [ ] Understand project structure
  - [ ] Reference related files automatically
  - [ ] Maintain consistency across files

### 11.2 Code Analysis
- [ ] **Linting & Style**
  - [ ] Auto-lint generated code
  - [ ] Match project's code style
  - [ ] Suggest improvements
  
- [ ] **Security Analysis**
  - [ ] Check for common vulnerabilities
  - [ ] Suggest security best practices
  - [ ] Warn about dangerous patterns

---

## 🐛 KNOWN BUGS & ISSUES

### Current Issues
- [ ] vLLM takes 60+ seconds to start (blocking CLI)
- [ ] SearXNG search sometimes returns no results
- [ ] Unclosed aiohttp sessions in logs
- [ ] Hallucinations on educational content (no scraping)
- [ ] No supervisor prompt refinement
- [ ] No true multi-agent execution (agents run sequentially)
- [ ] Model switching commands not implemented

### Architectural Issues
- [ ] Supervisor not connected to multi-agent search system
- [ ] No benchmark system for metrics
- [ ] No experience replay / learning memory
- [ ] No self-healing feedback loop
- [ ] Services don't auto-start/stop cleanly

---

## 📋 REFERENCE: FEATURES FROM CLONED REPOS

### From `self_improving_coding_agent/`
- ✅ Multi-agent orchestration pattern
- ✅ Benchmark system architecture
- ✅ Agent specialization (reasoner, reviewer, explorer)
- ⚠️ Self-improvement loop (conceptual, not implemented)
- ❌ Prompt refinement engine
- ❌ Result aggregation strategies

### From `RepairAgent/`
- ✅ Error classification system
- ✅ Fix strategy generation
- ✅ Automatic rollback on failure
- ❌ Root cause analysis depth
- ❌ Learning from repair patterns

### From `build-your-claude-code-from-scratch/`
- ✅ Tool calling patterns
- ✅ Context management
- ✅ Streaming responses
- ❌ Advanced MCP client features
- ❌ Smart tool selection

### From `healing-agent/`
- ✅ Self-healing architecture concepts
- ✅ State recovery mechanisms
- ❌ Fault isolation between agents
- ❌ Adaptive healing strategies

### From `Aider/`
- ✅ Interactive CLI patterns
- ✅ Repository context understanding
- ✅ Edit conflict resolution
- ❌ Autonomous code improvement
- ❌ Multi-file refactoring

---

## 🎯 PRIORITIZATION FOR CLAUDE OPUS

**Immediate (Week 1-2)**: Phases 1-3 (Council, Search, Metrics)
**Short-term (Week 3-4)**: Phases 4-5 (Self-Improvement, Infrastructure)
**Medium-term (Week 5-6)**: Phases 6-7 (Learning, Quality)
**Long-term (Week 7+)**: Phases 8-11 (Optimizations, Code)

Focus: **Multi-agent system > Search > Metrics** initially. Coding features are lower priority as per requirements.

---

## 📊 SUCCESS METRICS

When complete, Ryx should:
- ✅ Answer 80%+ of test questions correctly (baseline: 50%)
- ✅ Average response latency <5s (baseline: 15s)
- ✅ Use 30% fewer tokens (baseline: no tracking)
- ✅ Zero hallucinations on education domain (baseline: >20%)
- ✅ All agents respond in <2s (baseline: some >30s)
- ✅ Support 5+ simultaneous queries without degradation
- ✅ Auto-recover from 95% of failures without user intervention
