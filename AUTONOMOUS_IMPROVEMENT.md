# RYX AI - AUTONOMOUS SELF-IMPROVEMENT SYSTEM
**Created**: 2025-12-10
**Purpose**: Ryx improves itself. Copilot monitors and intervenes only on complete failure.

---

## 🎯 THE CORE PRINCIPLE

**Ryx fixes Ryx. Ryx builds Ryx.**

Copilot does NOT:
- Give Ryx the correct file paths
- Tell Ryx which function to call
- Fix Ryx's code directly
- Do Ryx's work

Copilot ONLY:
- Prompts Ryx to improve itself
- Monitors for complete failures (9 failed attempts)
- Intervenes to fix fundamental blockers
- Approves/denies permission requests

---

## 🔄 THE AUTONOMOUS LOOP

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RYX AUTONOMOUS SELF-IMPROVEMENT                      │
└─────────────────────────────────────────────────────────────────────────┘

STEP 1: SELF-DISCOVERY
────────────────────────
Copilot prompts: "Improve yourself using the cloned repos"

Ryx MUST:
├── Find the repos (not given paths)
├── Verify they exist
├── Correct Copilot if info is wrong
├── List what repos are available
└── Understand what each repo does

STEP 2: SELF-BENCHMARK
────────────────────────
Ryx runs benchmark on itself:
├── Discovers its own weaknesses
├── Scores each capability
├── Identifies lowest scores
└── Prioritizes what to fix

STEP 3: RESEARCH
────────────────────────
For each weakness, Ryx:
├── Searches cloned repos for solutions
├── If not found → searches online
├── If found online → [PERMISSION] clone new repo
├── Documents what it found
└── Creates improvement plan

STEP 4: ATTEMPT IMPROVEMENT
────────────────────────
Ryx tries to improve (up to 9 attempts):
├── Implements change in test/sandbox
├── Runs benchmark
├── If score improved → document & continue
├── If score same/worse → try different approach
└── After 9 fails → escalate to Copilot

STEP 5: APPLY FOR REAL
────────────────────────
When improvement is proven:
├── [PERMISSION] Request to edit real files
├── If approved → apply changes
├── Run final benchmark
├── Document in improvement log
└── Move to next weakness

STEP 6: REPEAT
────────────────────────
Loop back to STEP 2 with new baseline
```

---

## 🔐 PERMISSION SYSTEM

### Requires Permission (Ryx must ask)
1. **Clone new repos** - "May I clone [repo_url]?"
2. **Edit core files** - "May I edit [file_path]?"
3. **Delete files** - "May I delete [file_path]?"
4. **Install packages** - "May I install [package]?"

### Auto-Approved (No permission needed)
1. Read any file in project
2. Run benchmarks
3. Create files in `data/` or `tests/`
4. Edit files in `tests/` directory
5. Search online for information

### Denied (Never allowed without explicit override)
1. Modify MISSION.md or SELF_IMPROVEMENT_CYCLE.md
2. Delete benchmark logs
3. Modify git history
4. Access files outside project

---

## 📊 SELF-BENCHMARK REQUIREMENTS

Ryx must be able to:

1. **Discover its own capabilities**
   - Find all its modules
   - Understand what each does
   - Identify testable functions

2. **Score each capability**
   - Create test cases
   - Run tests
   - Calculate success rate
   - Compare to baseline

3. **Identify weaknesses**
   - Rank capabilities by score
   - Focus on lowest scores
   - Understand WHY it's failing

---

## 📁 REPO DISCOVERY

Ryx is told: "Look at the cloned repos"

Ryx must figure out:
- Where are they? (search for common locations)
- What repos exist?
- What can each repo teach?

**Expected locations to search:**
- ~/cloned_repositorys/
- ~/repos/
- ~/projects/
- /home/*/cloned*/
- Current project's submodules

**If Copilot gives wrong info:**
Ryx should say: "That path doesn't exist. I found repos at [actual_path] instead."

---

## 📝 IMPROVEMENT LOG FORMAT

Location: `data/improvement_logs/YYYY-MM-DD_NNN.yaml`

```yaml
improvement_id: "2025-12-10_001"
timestamp: "2025-12-10T16:00:00Z"

# What was weak
weakness:
  category: "edit_success"
  score_before: 9/30
  description: "File edits fail when whitespace differs"

# Research phase
research:
  repos_searched:
    - name: "aider"
      path: "/home/tobi/cloned_repositorys/aider"
      relevant_files:
        - "aider/coders/editblock_coder.py"
        - "aider/coders/wholefile_coder.py"
      learnings: "Uses fuzzy matching with difflib"
    - name: "healing-agent"
      found: false
      searched_online: true
      cloned_from: "https://github.com/..."
  
  online_search:
    queries:
      - "python fuzzy text matching edit"
      - "code edit reliability llm"
    results:
      - url: "..."
        useful: true
        key_insight: "..."

# Implementation attempts
attempts:
  - attempt: 1
    change: "Added Levenshtein distance matching"
    result: "FAIL"
    score: 9/30
    error: "Import error"
    
  - attempt: 2
    change: "Fixed import, added fallback"
    result: "SUCCESS"
    score: 15/30
    improvement: "+6 points"

# Final result
result:
  status: "SUCCESS"
  score_after: 15/30
  improvement: "+6 points"
  files_changed:
    - path: "core/reliable_editor.py"
      permission_granted: true
      backup: ".ryx.backups/reliable_editor.py.20251210.bak"
  
  documentation:
    what_worked: "Levenshtein distance for fuzzy matching"
    what_didnt: "Exact regex matching too strict"
    future_ideas: "Add AST-aware matching for code"
```

---

## 🚨 COPILOT INTERVENTION RULES

### When to Intervene
1. Ryx failed 9 times on same improvement
2. Ryx is in infinite loop
3. Ryx broke something critical
4. Ryx requests help explicitly

### How to Intervene
1. Identify WHY Ryx is stuck (fundamental blocker)
2. Fix the blocker (NOT the improvement itself)
3. Document what was blocking
4. Let Ryx continue

### Example Interventions
- "Ryx can't find repos because find command syntax wrong" → Fix find logic
- "Ryx can't edit files because editor method missing" → Add missing method
- "Ryx can't benchmark because test runner broken" → Fix test runner

---

## 🎮 COMMANDS

### Start Self-Improvement
```
Copilot: "Ryx, improve yourself using the cloned repos"
```

### Check Status
```
Copilot: "Ryx, show improvement status"
```

### Manual Benchmark
```
Copilot: "Ryx, run benchmark"
```

### Approve Permission
```
Ryx: "May I edit core/reliable_editor.py?"
Copilot: "Approved" or "Denied: [reason]"
```

---

## 📈 SUCCESS METRICS

### Short Term (This Session)
- Ryx can find repos without being told paths
- Ryx can benchmark itself
- Ryx can identify weaknesses
- Ryx can research solutions

### Medium Term (This Week)
- Ryx improves at least one capability
- Score increases from 35 to 50+
- Ryx documents improvements properly

### Long Term (This Month)
- Score reaches 80+
- Ryx handles most improvements autonomously
- Copilot intervention < 10% of cycles

---

## 🔮 THE GOAL

**Ryx becomes self-sustaining.**

Eventually:
- Ryx notices it's weak at something
- Ryx researches how to improve
- Ryx implements improvement
- Ryx verifies improvement
- Ryx documents for future
- Copilot just watches

**Ryx takes over Copilot's job.**
