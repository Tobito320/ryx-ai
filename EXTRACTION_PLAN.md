# Repository Extraction Plan

## Goal
Extract all valuable concepts from cloned repos to push Ryx from 80% → 95%+ on real-world tests.

## Current Status (Based on Audit)

### Repos Scanned: 30
- Ready to Archive: TBD
- High Value: TBD  
- Medium Value: TBD
- Low Value: TBD

## Extraction Checklist

### Priority 1: Critical Missing Features (For 80% → 90%)

#### [ ] Clarification System
**Source**: Aider, SWE-agent, RepairAgent
**Files to check**:
- `aider/coders/base_coder.py` - User interaction patterns
- `SWE-agent/agent/prompts.py` - Clarifying questions
- `RepairAgent/agent/clarifier.py` - When to ask vs guess

**Implementation**:
```python
# Add to ryx_brain.py
def _needs_clarification(self, prompt: str) -> bool:
    """Detect if prompt is too vague"""
    vague_indicators = ['it', 'this', 'that', 'thing']
    no_target = not any(file in prompt for file in ['.py', '.js', 'file'])
    return any(indicator in prompt.split() for indicator in vague_indicators) and no_target

def _generate_clarification(self, prompt: str) -> str:
    """Ask clarifying question"""
    if 'add' in prompt.lower():
        return "Which file should I add this to?"
    if 'fix' in prompt.lower():
        return "What needs to be fixed? Please specify file or function."
    return "Can you provide more details?"
```

#### [ ] Plan Object Fix
**Source**: Internal Ryx code
**Issue**: Missing attributes crash competitor benchmarks

**Implementation**:
```python
# Fix in ryx_brain.py Plan dataclass
@dataclass
class Plan:
    intent: Intent
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    question: Optional[str] = None
    confidence: float = 1.0
    requires_confirmation: bool = False
    fallback_intents: List[Intent] = field(default_factory=list)
    
    # ADD THESE:
    files_to_check: List[str] = field(default_factory=list)
    response: str = ""
    guidance: str = ""
```

#### [ ] Conversation Memory
**Source**: MemGPT, letta-code, AutoGPT
**Files to check**:
- `MemGPT/memgpt/agent.py` - Persistent conversation state
- `letta-code/letta/memory.py` - Context across turns
- `AutoGPT/autogpt/memory/` - Long-term memory

**Implementation**:
```python
# Add to ryx_brain.py
class ConversationMemory:
    def __init__(self):
        self.recent_files = []  # Last 5 files worked on
        self.current_task = None
        self.user_preferences = {}
    
    def remember_file(self, filepath: str):
        self.recent_files.append(filepath)
        self.recent_files = self.recent_files[-5:]
    
    def infer_target(self, vague_prompt: str) -> Optional[str]:
        """If user says 'fix it', assume they mean last file"""
        if 'it' in vague_prompt and self.recent_files:
            return self.recent_files[-1]
        return None
```

### Priority 2: Advanced Features (For 90% → 95%)

#### [ ] Fuzzy Edit Matching (from Aider)
**Source**: `aider/coders/editblock_coder.py`
- Better handling of whitespace differences
- Partial line matching
- Similarity scoring

#### [ ] Repo Map (from Aider)
**Source**: `aider/repomap.py`
- Quick codebase overview
- Symbol extraction
- Dependency graph

#### [ ] Multi-file Context (from SWE-agent)
**Source**: `SWE-agent/agent/context.py`
- Track related files automatically
- Suggest files user might need

#### [ ] Better Error Recovery (from healing-agent)
**Source**: `healing-agent/healer/recovery.py`
- Self-healing decorators
- Automatic retry with variations
- Learn from failures

### Priority 3: Nice-to-Have (For 95% → 100%)

#### [ ] Code Understanding (AST/Tree-sitter)
**Source**: multiple repos
- Parse code structure
- Understand relationships
- Smart refactoring

#### [ ] Test Generation
**Source**: `pr-agent/pr_agent/algo/test_generator.py`
- Auto-generate tests
- Coverage analysis

#### [ ] Advanced Planning (from OpenDevin/Devika)
- Multi-step task decomposition
- Parallel execution
- Progress tracking

## Extraction Workflow

### Step 1: Identify (DONE)
- Run audit script ✅
- Categorize repos ✅
- Find high-value targets ✅

### Step 2: Extract (IN PROGRESS)
For each concept:
1. Find best implementation in repos
2. Read and understand the code
3. Adapt to Ryx's architecture
4. Test with real prompts
5. Benchmark improvement

### Step 3: Validate
- Run brutal tests
- Run competitor benchmark
- Real-world usage test
- Measure improvement

### Step 4: Archive
When repo is fully extracted:
```bash
mv /home/tobi/cloned_repositorys/REPO_NAME /home/tobi/cloned_repositorys/_ARCHIVE/
```

## Progress Tracking

### Completed Extractions:
- [x] Basic intent detection (from multiple repos)
- [x] ReliableEditor fuzzy matching (from Aider)
- [x] Self-improvement loop (from self_improving_coding_agent)
- [x] Vague phrase detection (manual improvement)

### In Progress:
- [ ] Clarification system
- [ ] Plan object fix
- [ ] Conversation memory

### Not Started:
- [ ] Repo map
- [ ] Advanced error recovery
- [ ] Multi-file context
- [ ] Test generation
- [ ] Code AST understanding

## Success Criteria

- [ ] 90%+ on brutal real-world tests
- [ ] 80%+ on competitor benchmark (no crashes)
- [ ] User experience: 8/10
- [ ] Can handle "fix it" with context
- [ ] Asks clarifying questions when needed
- [ ] Remembers what user is working on

## Estimated Timeline

- Priority 1 features: 8-12 hours
- Priority 2 features: 16-24 hours  
- Priority 3 features: 24-40 hours

**Total to 95%: 2-3 days focused work**

---

Last updated: 2025-12-10
