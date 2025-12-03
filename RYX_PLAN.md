# 🟣 Ryx AI - Architektur & Verbesserungsplan

**Erstellt**: 2025-12-03  
**Aktualisiert**: 2025-12-03 (Aider-basierte Infrastruktur **vollständig integriert**)  
**Status**: Vollständige Analyse & Roadmap  
**Zweck**: Entwicklungsplan für automatisierte Agent-basierte Umsetzung

---

## 🌐 Ryx Ökosystem Vision

Ryx ist **Tobis persönliches AI-Ökosystem** – nicht nur ein CLI-Tool:

| Komponente | Beschreibung | Status |
|------------|--------------|--------|
| **Ryx CLI/Brain** | Terminal-Assistent (Claude Code/Aider-Stil) | 🟢 Funktional |
| **RyxHub** | Zentrale Steuerung/Orchestrator für alle Ryx-Services | 📋 Geplant |
| **RyxSurf** | Browser-/Web-Automation (langfristig eigener Browser) | 📋 Geplant |
| **RyxVoice** | Spracheingabe/-ausgabe | 📋 Geplant |
| **RyxFace** | Hardware/Kamera-Integration | 📋 Geplant |
| **RyxCouncil** | Multi-Agent-Entscheidungen | 📋 Geplant |

**Design-Prinzipien**:
- Linux-first (Arch als Dev-Umgebung), aber portabel
- Lokal-first (Ollama/vLLM), Cloud optional
- Modular: Jede Komponente unabhängig nutzbar
- Privacy-first: Keine Telemetrie, eigene SearXNG-Instanz

---

## 📊 Executive Summary

### Aktueller Status
- **Codebase**: 62 Python-Module + 16 neue Aider-basierte Module (~32.000 LOC)
- **Fortschritt**: ~65% der Zielarchitektur implementiert (↑ von 38%)
- **Neu integriert**: Repository-Exploration, Git-Integration, Diff-Editing, Test-Execution

### P0-Status (VOLLSTÄNDIG INTEGRIERT ✅)

| P0-Feature | Status | Module | Integration |
|------------|--------|--------|-------------|
| File-Finder / Repo-Map | ✅ **Fertig** | `ryx_pkg/repo/` | `core/phases.py` |
| Diff-Based Editing | ✅ **Fertig** | `ryx_pkg/editing/` | `core/agent_tools.py` |
| Git-Integration | ✅ **Fertig** | `ryx_pkg/git/` | `core/phases.py` + Tools |
| Test-Execution | ✅ **Fertig** | `ryx_pkg/testing/` | `core/phases.py` |
| Tool-Only-Mode | 🟡 Teilweise | - | Prompts ausstehend |

### Neue Agent-Tools (nach Integration)
```
- read_file, list_directory, search_code (bestehend)
- write_file, create_file, delete_file (bestehend)
- apply_diff          ← Nutzt jetzt DiffEditor mit Fuzzy-Matching
- search_replace      ← NEU: Suchen/Ersetzen mit Fuzzy-Matching
- find_relevant_files ← NEU: Intelligente Dateisuche
- git_status          ← NEU: Formatierter Git-Status
- git_commit, git_revert, git_diff (bestehend)
- run_command (bestehend)
```

### Verbleibende Prioritäten
1. **P0.7 (Kritisch)**: Tool-Only LLM Output - Prompts anpassen
2. **P1**: Self-Critique, UI-Updates, Error-Recovery
3. **P2**: RyxHub, RyxSurf, Multi-Agent-Council

---

## 🏗️ Aktuelle Architektur

### Komponenten-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (CLI/Web)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     session_loop.py           │  ← Session Management
         │  - Slash-Commands             │
         │  - History                    │
         │  - Interrupt-Handling         │
         └───────────────┬───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     ryx_brain.py              │  ← Core Intelligence
         │  - Intent Classification      │
         │  - Context Management         │
         │  - Plan Execution             │
         └───────────────┬───────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │ Phases  │   │ Router  │   │  Tools  │
    │ (PLAN→  │   │ (Model  │   │ (FS/Web │
    │ EXECUTE)│   │ Select) │   │ /Shell) │
    └─────────┘   └─────────┘   └─────────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │     ollama_client.py          │  ← LLM Interface
         │  - Streaming                  │
         │  - Retry Logic                │
         │  - Token Stats                │
         └───────────────────────────────┘
                         │
                         ▼
                  [ Ollama/vLLM ]
```

### Request-Flow (Typischer Durchlauf)

1. **User Input** → `session_loop.py`
   - Parse slash-commands (`/help`, `/tier`, etc.)
   - Normale Anfrage → weiter an Brain

2. **Intent Classification** → `ryx_brain.py` + `intent_parser.py`
   - LLM-basierte Absichtserkennung (qwen2.5:1.5b)
   - Klassifizierung: OPEN_FILE, SEARCH_WEB, CODE_TASK, CHAT, etc.

3. **Model Selection** → `model_router.py`
   - Intent-basiertes Routing (fast/chat/code/reason)
   - VRAM-aware Modell-Auswahl

4. **Execution Branch**:
   
   **A) Simple Tasks** (OPEN_FILE, RUN_COMMAND, SEARCH_WEB):
   - Direkte Tool-Calls via `tool_registry.py`
   - Sofortige Ausführung
   
   **B) Complex Code Tasks** (CODE_TASK):
   - Phase-System aktiviert (`phases.py`)
   - EXPLORE → PLAN → APPLY → VERIFY
   - PhaseExecutor orchestriert Workflow
   
   **C) Chat/Info** (CHAT, GET_INFO):
   - LLM-Antwort ohne Tools
   - Conversation-Context aus Memory

5. **Tool Execution** → `tool_registry.py`
   - Safety-Check (`permissions.py`)
   - Tool-Aufruf (read_file, search_web, run_shell, etc.)
   - Result zurück an Brain

6. **Response Rendering** → `cli_ui.py` / `printer.py`
   - Themed Output (Dracula/Nord/Catppuccin)
   - Token-Streaming mit tok/s
   - Phase-Indikatoren (⏳→✅)

### Kern-Module im Detail

#### Core Intelligence
- **`ryx_brain.py`** (2800+ LOC)
  - Haupt-Orchestrator
  - Intent → Plan → Execute
  - Context-Management (ConversationContext)
  - Follow-up-Handling
  - KnowledgeBase für häufige Abfragen

- **`intent_parser.py`** (600 LOC)
  - NLU mit LLM (qwen2.5:1.5b)
  - Pattern-Matching für häufige Intents
  - German/English Support

- **`phases.py`** (1400 LOC)
  - State-Machine: IDLE→EXPLORE→PLAN→APPLY→VERIFY→COMPLETE
  - PhaseExecutor: Workflow-Engine
  - ExecutionPlan: Strukturierte Task-Pläne
  - Checkpoint-Integration

#### Agent-System (teilweise)
- **`agents/supervisor.py`** (150 LOC)
  - Strategische Planung
  - Verwendet größeres Modell (14B+)
  - Erstellt Execution-Plans
  - **STATUS**: Vorhanden, aber nicht voll integriert

- **`agents/operator.py`** (150 LOC)
  - Taktische Ausführung
  - Tool-Aufrufe
  - **STATUS**: Vorhanden, aber ryx_brain macht aktuell alles selbst

- **`agents/base.py`** (100 LOC)
  - BaseAgent-Abstraktion
  - AgentConfig
  - **STATUS**: Infrastruktur vorhanden

#### Model & LLM Layer
- **`model_router.py`** (500 LOC)
  - Rollenbasiertes Routing (FAST/CHAT/CODE/REASON/EMBED)
  - Fixed Model-Config (keine Dynamik nötig)
  - Modelle: qwen2.5:1.5b, gemma2:2b, qwen2.5-coder:14b, deepseek-r1:14b

- **`ollama_client.py`** (600 LOC)
  - Streaming Support
  - Retry mit exponential backoff
  - Token-Statistics
  - Context-Management

#### Tool Layer
- **`tool_registry.py`** (1200 LOC)
  - Zentrale Tool-Registry
  - Safety-Levels: SAFE, RISKY, DANGEROUS
  - Tools: read_file, write_file, run_shell, search_web, scrape_html
  - **PROBLEM**: Tools geben oft Text zurück, nicht strukturiert

- **`agent_tools.py`** (800 LOC)
  - Strukturierte Tool-Abstraktionen
  - ReadFileTool, WriteFileTool, ApplyDiffTool (Diff-Support vorhanden!)
  - GitCommitTool, GitRevertTool
  - **STATUS**: Definiert, aber nicht vollständig integriert

- **`permissions.py`** (600 LOC)
  - Safety-Checks
  - Blocked-Command-Liste
  - Directory-Whitelisting
  - User-Confirmation für riskante Ops

#### Repository Understanding
- **`repo_explorer.py`** (800 LOC)
  - Rekursives Scanning
  - FileType-Klassifizierung (CODE/CONFIG/DOC/TEST)
  - Tag-Indexierung (theme, config, network, etc.)
  - Relevance-Scoring
  - **STATUS**: Implementiert, aber nicht genutzt in ryx_brain

#### Memory & Context
- **`memory.py`** (400 LOC)
  - Episodic Memory (Session)
  - Persistent Memory (SQLite)
  - Context-Recall

- **`checkpoints.py`** (500 LOC)
  - Snapshot-System für Undo/Rollback
  - Filesystem-State-Tracking
  - **STATUS**: Funktioniert, aber kein Git-Integration

#### CLI/UI
- **`cli_ui.py`** + **`cli_ui_modern.py`** (1500 LOC)
  - Rich Terminal Output
  - Theme-Support (Dracula/Nord/Catppuccin)
  - Token-Streaming-Display
  - Phase-Indicators

- **`session_loop.py`** (800 LOC)
  - Interactive Session
  - Slash-Commands: /help, /status, /tier, /undo, /rollback
  - History mit readline
  - Graceful Interrupt (Ctrl+C)

#### Workflow & Orchestration
- **`workflow_orchestrator.py`** (600 LOC)
  - Multi-Step Workflows
  - Plan→Execute→Validate
  - **STATUS**: Alternative zu phases.py, beide existieren parallel

#### Configuration
- **`configs/models.json`**: Modell-Definitionen + Task-Routing
- **`configs/safety.json`**: Safety-Modes (strict/normal/loose)
- **`configs/permissions.json`**: Tool-Permissions
- **`configs/settings.json`**: User-Preferences

---

## 🎯 Zielarchitektur

### Vision: Claude Code/Aider-Style Local Agent

```
                         USER
                          │
                          ▼
        ┌─────────────────────────────────┐
        │   SESSION MANAGER               │
        │  - Interactive CLI              │
        │  - Streaming Output             │
        │  - Interrupt Handling           │
        └─────────────┬───────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────┐
        │   SUPERVISOR AGENT              │  ← Strategic Planner
        │  - Deep Intent Understanding    │
        │  - Repository Exploration       │
        │  - High-Level Planning          │
        │  - Failure Recovery             │
        │  Model: 14B+ (qwen2.5-coder)    │
        └─────────────┬───────────────────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
     ┌────────────┐   ┌────────────┐
     │  OPERATOR  │   │ OPERATOR   │  ← Tactical Executors
     │  AGENT #1  │   │ AGENT #2   │
     │            │   │            │
     │ - File Ops │   │ - Code Gen │
     │ - Search   │   │ - Testing  │
     │            │   │            │
     │ Model:     │   │ Model:     │
     │ 7B-14B     │   │ 14B        │
     └─────┬──────┘   └──────┬─────┘
           │                 │
           └────────┬────────┘
                    ▼
        ┌─────────────────────────────────┐
        │   TOOL LAYER (Actions Only)     │
        │                                  │
        │  ┌──────────┐  ┌──────────┐     │
        │  │ File Ops │  │ Git Ops  │     │
        │  │ - Find   │  │ - Commit │     │
        │  │ - Read   │  │ - Diff   │     │
        │  │ - Patch  │  │ - Revert │     │
        │  └──────────┘  └──────────┘     │
        │                                  │
        │  ┌──────────┐  ┌──────────┐     │
        │  │ Shell    │  │ Web      │     │
        │  │ - Exec   │  │ - Search │     │
        │  │ - Test   │  │ - Scrape │     │
        │  └──────────┘  └──────────┘     │
        │                                  │
        │  Safety Layer: Permissions,     │
        │  Confirmation, Sandboxing        │
        └─────────────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────────────┐
        │   VERIFICATION & SELF-HEALING   │
        │  - Test Execution               │
        │  - Lint/Type-Check              │
        │  - LLM Self-Critique            │
        │  - Auto-Retry on Failure        │
        └─────────────────────────────────┘
```

### Schlüsselprinzipien

#### 1. Hierarchische Agent-Struktur
- **Supervisor**: Plant, delegiert, recovered bei Fehlern
- **Operators**: Führen spezifische Tasks aus (File-Ops, Code-Gen, Testing)
- **Tools**: Reine Aktionen, kein LLM-Involvement

#### 2. LLM Denkt, Tools Handeln
- **LLM Output**: Immer strukturiertes JSON mit Tool-Calls
- **Tool Input**: Klare Parameter (path, query, command)
- **Tool Output**: Strukturiertes Result-Object (success, data, error)
- **Kein freier Text**: LLM schreibt nie direkt Files

#### 3. Repository-Aware Context
- **RepoMap**: Automatisches File-Indexing bei Task-Start
- **Semantic Tags**: Theme, Config, Test, Network, UI, etc.
- **Relevance Scoring**: Finde top 5-20 relevante Files für Task
- **No Guessing**: LLM bekommt echte File-Liste, rät nicht

#### 4. Diff-Based Editing
- **Unified Diff Format**: Standard patch format
- **Minimal Changes**: Nur betroffene Zeilen
- **Git-Trackable**: Jede Änderung = 1 Commit
- **Easy Review**: User sieht Diff vor Apply

#### 5. Plan → Execute → Verify → Refine
- **EXPLORE Phase**: Repo scannen, relevante Files lesen
- **PLAN Phase**: Schritt-für-Schritt-Plan, User-Approval
- **APPLY Phase**: Diffs generieren und anwenden
- **VERIFY Phase**: Tests laufen, Lint-Check, Self-Critique
- **REFINE Phase**: Bei Fehlern zurück zu PLAN

#### 6. Git-Native Workflow
- **Auto-Commit**: Jede Änderung = 1 Commit mit beschreibender Message
- **Branch-Per-Task**: Experimentelle Änderungen isoliert
- **Easy Undo**: `/undo` = git revert, `/rollback` = reset --hard
- **Change History**: Alle Änderungen nachvollziehbar

#### 7. Self-Critique & Verification
- **Post-Edit Review**: LLM reviewed seine Änderungen
- **Hallucination Check**: "Habe ich File-Pfade erfunden?"
- **Test Execution**: Automatisch nach Code-Änderungen
- **Error Recovery**: Max 3 Retry-Attempts, dann User-Escalation

### Geplante Kern-Komponenten

#### Supervisor Layer
- **`SupervisorAgent`** (erweitert)
  - Repository-Exploration initiieren
  - High-Level-Plans erstellen
  - Operators delegieren
  - Failure-Recovery orchestrieren

#### Operator Layer
- **`FileOperator`**: File-Suche, Lesen, Patching
- **`CodeOperator`**: Code-Generierung, Refactoring
- **`TestOperator`**: Test-Ausführung, Lint, Verify
- **`WebOperator`**: Search, Scrape, Synthesis

#### Tool Layer (Refined)
- **`FileFinder`**: Fuzzy-Search, Pattern-Matching
- **`FileReader`**: Read mit Range-Support
- **`DiffApplier`**: Unified-Diff-Application
- **`GitManager`**: Commit, Revert, Branch, Status
- **`TestRunner`**: Auto-Detect (pytest/jest/go test)
- **`LintRunner`**: Auto-Detect (pylint/eslint/golangci-lint)

#### Verification Layer
- **`TestVerifier`**: Führt Tests aus, parset Errors
- **`LintVerifier`**: Führt Linter aus, reported Issues
- **`SelfCritiqueAgent`**: LLM reviewed eigene Änderungen
- **`HallucinationDetector`**: Prüft auf erfundene Pfade/Packages

#### Context Layer
- **`RepoExplorer`** (erweitert): Vollständiges Repository-Indexing
- **`ContextBuilder`**: Baut optimalen Context für LLM
- **`FileSelector`**: Relevante Files basierend auf Task
- **`ManifestLoader`**: Lädt Projekt-spezifische Configs

---

## 📋 Checklisten-Status

### Legende
- ✅ **Erfüllt**: Funktioniert produktiv
- 🟡 **Teilweise**: Implementiert, aber nicht vollständig integriert
- ❌ **Fehlt**: Nicht vorhanden oder nicht funktional

---

### 1. Core Architecture & Orchestration

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Intent Classification | ✅ | `intent_parser.py` (L1-600) | LLM + Pattern-Matching |
| Model Router | ✅ | `model_router.py` (L1-500) | Role-based routing |
| Phase State Machine | 🟡 | `phases.py` (L1-1400) | Existiert, aber nicht voll genutzt |
| Supervisor-Operator Hierarchy | 🟡 | `agents/supervisor.py`, `agents/operator.py` | Definiert, nicht integriert |
| Tool Registry | ✅ | `tool_registry.py` (L1-1200) | Zentrale Registry vorhanden |
| Checkpoint System | ✅ | `checkpoints.py` (L1-500) | Undo/Rollback funktioniert |
| Workflow Orchestration | 🟡 | `workflow_orchestrator.py` (L1-600) | Parallel zu phases.py |
| Context Management | ✅ | `ryx_brain.py` (ConversationContext) | Follow-ups funktionieren |
| Error Recovery | 🟡 | Verstreut | Kein strukturiertes Retry-System |

**Kategorie-Score**: 6/9 vollständig = **67%**

---

### 2. Repository Understanding & Context

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Repository Scanner | 🟡 | `repo_explorer.py` (L1-800) | Implementiert, nicht genutzt |
| File Type Detection | 🟡 | `repo_explorer.py` (FileType) | Funktioniert, nicht integriert |
| Semantic Tagging | 🟡 | `repo_explorer.py` (tags_index) | Vorhanden, nicht genutzt |
| RepoMap Generation | ❌ | - | Scanner erstellt keine Map |
| File Relevance Scoring | 🟡 | `repo_explorer.py` (find_relevant) | Implementiert, nicht integriert |
| Manifest System (RYX_MANIFEST.yaml) | ❌ | - | Nicht implementiert |
| Project-Specific Config | 🟡 | `configs/` | Global, nicht per-project |
| Context Truncation | ❌ | - | LLM bekommt zu viel Context |
| Smart File Selection | ❌ | - | Brain rät Pfade |

**Kategorie-Score**: 2/9 vollständig = **22%**

---

### 3. Tool Layer & Execution

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Structured Tool Interface | 🟡 | `agent_tools.py` (AgentTool) | Basis vorhanden |
| File Read Tool | ✅ | `tool_registry.py` + `agent_tools.py` | Funktioniert |
| File Write Tool | ✅ | `tool_registry.py` | Funktioniert, aber full-file |
| **Diff-Based Editing** | 🟡 | `agent_tools.py` (ApplyDiffTool) | Implementiert, nicht genutzt! |
| File Search Tool | ✅ | `tool_registry.py` (find_files) | Funktioniert |
| Shell Execution Tool | ✅ | `tool_registry.py` (run_shell) | Mit Safety |
| Web Search Tool | ✅ | `tool_registry.py` (search_web) | SearXNG + Fallback |
| Web Scrape Tool | ✅ | `tools/scraper.py` | Funktioniert |
| Git Commit Tool | 🟡 | `agent_tools.py` (GitCommitTool) | Definiert, nicht integriert |
| Git Revert Tool | 🟡 | `agent_tools.py` (GitRevertTool) | Definiert, nicht integriert |
| Tool Result Schema | ✅ | `tool_registry.py` (ToolResult) | Strukturiert |
| Safety Layer | ✅ | `permissions.py` | Funktioniert |
| Tool-Only LLM Output | ❌ | - | LLM gibt freien Text zurück |

**Kategorie-Score**: 7/13 vollständig = **54%**

---

### 4. Verification & Self-Healing

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Test Execution | 🟡 | `phases.py` (VERIFY) | Basic, kein Auto-Detect |
| Lint/Type-Check | ❌ | - | Nicht implementiert |
| LLM Self-Critique | ❌ | - | Nicht vorhanden |
| Hallucination Detection | ❌ | - | Nicht vorhanden |
| Auto-Retry on Failure | ❌ | - | Kein strukturiertes System |
| Error Parsing | ❌ | - | Errors werden nur angezeigt |
| Test Auto-Detection | ❌ | - | Hardcoded pytest |
| Verification Loop | 🟡 | `phases.py` (VERIFY) | Basic vorhanden |
| Rollback on Failure | 🟡 | `checkpoints.py` | Manuell, nicht auto |

**Kategorie-Score**: 0/9 vollständig = **0%**

---

### 5. CLI/UX & Output

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Interactive Session | ✅ | `session_loop.py` | Funktioniert gut |
| Slash Commands | ✅ | `session_loop.py` | /help, /status, /tier, etc. |
| Token Streaming | ✅ | `ollama_client.py` + `cli_ui.py` | Mit tok/s |
| Theme Support | ✅ | `theme.py`, `cli_ui.py` | Dracula/Nord/Catppuccin |
| Phase Visualization | 🟡 | `cli_ui.py` | Erstellt, nicht voll integriert |
| Diff Display | 🟡 | `cli_ui.py` (show_diff) | Vorhanden, nicht genutzt |
| Progress Indicators | ✅ | `cli_ui.py` | ⏳→✅ funktioniert |
| Error Display | ✅ | `cli_ui.py` | Themed errors |
| Chain of Thought | 🟡 | `cli_ui.py` | Basic, nicht detailliert |
| Plan Approval UI | ❌ | - | Kein interaktives Approval |
| Minimal Output Mode | ❌ | - | Oft zu viel Text |

**Kategorie-Score**: 7/11 vollständig = **64%**

---

### 6. Git Integration & Safety

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Git Status Check | ❌ | - | Nicht implementiert |
| Auto-Commit | ❌ | - | Nicht vorhanden |
| Commit Message Generation | ❌ | - | Nicht vorhanden |
| Branch Management | ❌ | - | Nicht vorhanden |
| Easy Undo (/undo → git revert) | 🟡 | `checkpoints.py` | Checkpoint-based, nicht Git |
| Rollback (/rollback) | 🟡 | `checkpoints.py` | Checkpoint-based, nicht Git |
| Change History | ❌ | - | Nicht Git-basiert |
| Diff Review vor Apply | ❌ | - | Nicht implementiert |

**Kategorie-Score**: 0/8 vollständig = **0%**

---

### 7. Multi-Agent & Council (Future)

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Supervisor Agent | 🟡 | `agents/supervisor.py` | Definiert, nicht integriert |
| Operator Agents | 🟡 | `agents/operator.py` | Definiert, nicht integriert |
| Agent Communication | ❌ | - | Nicht vorhanden |
| LLM Council | 🟡 | `tools/council.py` | Skizziert, nicht funktionstüchtig |
| Multi-Model Consensus | ❌ | - | Nicht implementiert |
| Agent Memory Sharing | ❌ | - | Nicht vorhanden |

**Kategorie-Score**: 0/6 vollständig = **0%**

---

### 8. Config & Safety

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Model Configuration | ✅ | `configs/models.json` | Gut strukturiert |
| Safety Modes | ✅ | `configs/safety.json` | strict/normal/loose |
| Permission System | ✅ | `permissions.py` | Funktioniert |
| Blocked Commands | ✅ | `configs/safety.json` | Gute Liste |
| Safe Directories | ✅ | `configs/safety.json` | Definiert |
| User Preferences | ✅ | `configs/settings.json` | Basic vorhanden |
| Per-Project Config | ❌ | - | Nicht unterstützt |

**Kategorie-Score**: 6/7 vollständig = **86%**

---

### 9. Memory & Learning

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Episodic Memory | ✅ | `memory.py` | Session-Memory |
| Persistent Memory | ✅ | `memory.py` | SQLite-backed |
| Conversation Context | ✅ | `ryx_brain.py` (ConversationContext) | Follow-ups funktionieren |
| Knowledge Base | 🟡 | `ryx_brain.py` (KnowledgeBase) | Basic, statisch |
| RAG System | 🟡 | `rag_system.py` | Implementiert, wenig genutzt |
| Learning from Successes | ❌ | - | Nicht vorhanden |
| User Preference Learning | ❌ | - | Nicht vorhanden |

**Kategorie-Score**: 4/7 vollständig = **57%**

---

### 10. Testing & Quality

| Feature | Status | Referenz | Notiz |
|---------|--------|----------|-------|
| Unit Tests | 🟡 | `dev/tests/` | Einige vorhanden |
| Integration Tests | ❌ | - | Fehlen weitgehend |
| Test Coverage | ❌ | - | Nicht gemessen |
| Hallucination Tests | ❌ | - | Nicht vorhanden |
| Performance Benchmarks | 🟡 | `dev/benchmarks/` | Begonnen |
| Logging | ✅ | `logging_config.py` | Funktioniert |
| Metrics Collection | 🟡 | `metrics_collector.py` | Basic |

**Kategorie-Score**: 2/7 vollständig = **29%**

---

## 📊 Gesamtbewertung

| Kategorie | Score | Status |
|-----------|-------|--------|
| Core Architecture | 67% | 🟡 Gut |
| Repository Understanding | 22% | ❌ Schwach |
| Tool Layer | 54% | 🟡 Mittel |
| Verification & Self-Healing | 0% | ❌ Fehlt |
| CLI/UX | 64% | 🟡 Gut |
| Git Integration | 0% | ❌ Fehlt |
| Multi-Agent | 0% | ❌ Fehlt |
| Config & Safety | 86% | ✅ Sehr gut |
| Memory & Learning | 57% | 🟡 Mittel |
| Testing & Quality | 29% | ❌ Schwach |

**Gesamt-Score**: **37.9% ≈ 38%**

---

## 📝 Detaillierte TODO-Liste

### 🔴 P0: Kritische Grundlagen (Must-Have für Production)

#### P0.1: Tool-Only Output Mode
**Ziel**: LLM gibt NUR strukturierte Tool-Calls zurück, kein freier Text

**Tasks**:
- [x] **P0.1.1**: Erstelle `core/tool_schema.py` mit JSON-Schema für Tool-Calls
  - ✅ Schema mit pydantic-style dataclasses implementiert
  - ✅ ToolCall, ToolCallSequence, ToolCallParser
  - **Files**: `core/tool_schema.py`
  
- [x] **P0.1.2**: Erweitere `ollama_client.py` um Tool-Call-Parsing
  - ✅ generate_tool_call() Methode hinzugefügt
  - ✅ Automatisches Parsing von JSON zu ToolCallSequence
  - **Files**: `core/ollama_client.py` (L298-365)
  
- [x] **P0.1.3**: Anpasse Prompts in `ryx_brain.py` für Tool-Only-Mode
  - ✅ TOOL_ONLY_SYSTEM_PROMPT in tool_schema.py
  - ✅ get_tool_prompt() für Task-spezifische Prompts
  - **Files**: `core/tool_schema.py` (L260-310)
  
- [x] **P0.1.4**: Implementiere Tool-Executor-Loop in `ryx_brain.py`
  - ✅ execute_with_tools() Methode implementiert
  - ✅ Iterative Tool-Execution mit max 10 Iterationen
  - ✅ Ergebnis-Feedback an LLM
  - **Files**: `core/ryx_brain.py` (L1236-1335)

**Erfolgskriterium**: LLM kann keine Files mehr direkt schreiben, nur via Tools ✅

---

#### P0.2: Diff-Based File Editing
**Ziel**: Alle File-Edits als Unified Diffs, nicht Full-File-Rewrites

**Tasks**:
- [x] **P0.2.1**: Aktiviere `ApplyDiffTool` in `agent_tools.py`
  - ✅ Tool nutzt jetzt `DiffEditor` aus `ryx_pkg/editing/`
  - **Files**: `core/agent_tools.py` (L242-300)
  
- [x] **P0.2.2**: Erstelle Diff-Generation-Prompt für LLM
  - ✅ Prompt in `core/phases.py` APPLY-Phase vorhanden
  - **Files**: `core/phases.py` (L296-320)
  
- [x] **P0.2.3**: Implementiere Diff-Validator
  - ✅ `ryx_pkg/editing/validator.py` implementiert
  - **Files**: `ryx_pkg/editing/validator.py`
  
- [ ] **P0.2.4**: Integriere Diff-Display in CLI
  - Verwende existierende `show_diff()` in `cli_ui.py`
  - Zeige Diff VOR Apply mit Confirmation
  - **Files**: `core/cli_ui.py` (L400-500), `core/phases.py` (L700-750)

**Erfolgskriterium**: Alle Code-Änderungen sind kleine Diffs, keine Full-Rewrites

---

#### P0.3: Automatic File Finder
**Ziel**: Ryx findet Files selbst, LLM rät keine Pfade mehr

**Tasks**:
- [x] **P0.3.1**: Integriere `RepoExplorer` in `ryx_brain.py`
  - ✅ Integriert in `core/phases.py` PhaseExecutor
  - **Files**: `core/phases.py` (L397-430, L458-530)
  
- [x] **P0.3.2**: Erstelle `find_relevant_files()` in `repo_explorer.py`
  - ✅ `ryx_pkg/repo/explorer.py` - `find_for_task()` implementiert
  - **Files**: `ryx_pkg/repo/explorer.py`, `ryx_pkg/repo/file_selector.py`
  
- [x] **P0.3.3**: Erweitere PLAN-Phase um File-Selection
  - ✅ EXPLORE-Phase nutzt RepoExplorer.find_for_task()
  - **Files**: `core/phases.py` (L458-530)
  
- [x] **P0.3.4**: Implementiere Fuzzy File Search
  - ✅ `ryx_pkg/repo/file_selector.py` mit Fuzzy-Matching
  - **Files**: `ryx_pkg/repo/file_selector.py`

**Erfolgskriterium**: LLM erfindet keine File-Pfade mehr, findet reale Files ✅

---

#### P0.4: Git Auto-Commit Integration
**Ziel**: Jede Änderung = 1 Git-Commit, easy Undo

**Tasks**:
- [x] **P0.4.1**: Aktiviere `GitCommitTool` in `agent_tools.py`
  - ✅ Registriert + neues `GitStatusTool` hinzugefügt
  - **Files**: `core/agent_tools.py` (L694-720)
  
- [x] **P0.4.2**: Implementiere Auto-Commit nach APPLY-Phase
  - ✅ VERIFY-Phase committed nach erfolgreichen Tests via GitManager
  - **Files**: `core/phases.py` (L934-1020)
  
- [x] **P0.4.3**: Implementiere `/undo` als `git revert`
  - ✅ `ryx_pkg/git/git_manager.py` - `undo()` Methode implementiert
  - **Files**: `ryx_pkg/git/git_manager.py` (L180-210)
  
- [x] **P0.4.4**: Erweitere `/status` um Git-Status
  - ✅ `GitStatusTool` in agent_tools.py hinzugefügt
  - **Files**: `core/agent_tools.py` (L520-555)

**Erfolgskriterium**: Alle Änderungen sind Git-Commits, `/undo` funktioniert via Git ✅

---

#### P0.5: Test Execution in VERIFY Phase
**Ziel**: Automatische Tests nach Code-Änderungen

**Tasks**:
- [x] **P0.5.1**: Implementiere Test-Auto-Detection
  - ✅ `ryx_pkg/testing/detector.py` - detect_framework()
  - **Files**: `ryx_pkg/testing/detector.py`
  
- [x] **P0.5.2**: Erstelle `TestRunner` in `agent_tools.py`
  - ✅ `ryx_pkg/testing/test_runner.py` implementiert
  - **Files**: `ryx_pkg/testing/test_runner.py`
  
- [x] **P0.5.3**: Integriere TestRunner in VERIFY-Phase
  - ✅ PhaseExecutor nutzt test_runner.run_for_files()
  - **Files**: `core/phases.py` (L934-1020)
  
- [x] **P0.5.4**: Implementiere Test-Error-Parsing
  - ✅ TestRunner parsed pytest/jest/go output
  - **Files**: `ryx_pkg/testing/test_runner.py` (L200-350)

**Erfolgskriterium**: Tests laufen automatisch, Failures triggern Retry ✅

---

### 🟡 P1: Wichtige Verbesserungen (Reliability++)

#### P1.1: LLM Self-Critique
**Ziel**: LLM reviewed eigene Änderungen vor Abschluss

**Tasks**:
- [ ] **P1.1.1**: Erstelle Self-Critique-Prompt
  - Template: "Review your changes. Did you: 1) Change only intended files? 2) Invent any paths? 3) Introduce bugs?"
  - Output: JSON with `{"ok": true/false, "issues": [...]}`
  - **Files**: `core/prompts.py` (neu oder erweitern)
  
- [ ] **P1.1.2**: Implementiere `SelfCritiqueAgent`
  - Nimmt: Plan, Changes, Test-Results
  - Gibt: Critique mit Issues
  - **Files**: `core/agents/critique.py` (neu)
  
- [ ] **P1.1.3**: Integriere in VERIFY-Phase
  - Nach Tests: LLM reviewed Änderungen
  - Bei Issues: Zurück zu APPLY
  - **Files**: `core/phases.py` (L1050-1100)

**Erfolgskriterium**: LLM erkennt eigene Fehler (z.B. falsche File-Paths)

---

#### P1.2: Hallucination Detection
**Ziel**: Automatische Erkennung von erfundenen Pfaden/Packages

**Tasks**:
- [ ] **P1.2.1**: Erstelle `HallucinationDetector`
  - Prüfe: Alle erwähnten Files existieren?
  - Prüfe: Alle imports sind installiert?
  - **Files**: `core/hallucination_detector.py` (neu)
  
- [ ] **P1.2.2**: File-Path-Validation vor Tool-Execution
  - Bei read_file/write_file: Prüfe Existenz
  - Bei Nicht-Existenz: Frage LLM "Did you mean X? Or create new?"
  - **Files**: `core/tool_registry.py` (L300-350)
  
- [ ] **P1.2.3**: Package-Validation für Code-Generation
  - Parse imports aus generiertem Code
  - Check: Package installiert? (via pip list / npm list)
  - **Files**: `core/code_validator.py` (neu)

**Erfolgskriterium**: 90% weniger halluzinierte Pfade

---

#### P1.3: Structured Error Recovery
**Ziel**: Automatisches Retry mit verbessertem Context bei Fehlern

**Tasks**:
- [ ] **P1.3.1**: Erstelle `ErrorRecoveryLoop` in `phases.py`
  - Max 3 Retries
  - Bei jedem Retry: Erweitere Context mit Error-Details
  - **Files**: `core/phases.py` (L1150-1250)
  
- [ ] **P1.3.2**: Implementiere Error-Classification
  - Types: SYNTAX_ERROR, FILE_NOT_FOUND, TEST_FAILURE, TIMEOUT
  - Pro Type: Spezifische Recovery-Strategie
  - **Files**: `core/error_classifier.py` (neu)
  
- [ ] **P1.3.3**: Supervisor-Rescue bei wiederholtem Failure
  - Nach 3 Operator-Failures: Supervisor übernimmt
  - Supervisor analysiert, erstellt neuen Plan
  - **Files**: `core/agents/supervisor.py` (L100-200)

**Erfolgskriterium**: 70% der Errors werden auto-recovered

---

#### P1.4: Branch-Per-Task Workflow
**Ziel**: Experimentelle Änderungen in separaten Branches

**Tasks**:
- [ ] **P1.4.1**: Erstelle `GitBranchManager`
  - `create_task_branch(task_name)` → Branch: `ryx/{timestamp}-{slug}`
  - `merge_task_branch()` → Merge zurück zu main
  - `abandon_task_branch()` → Delete Branch
  - **Files**: `core/git_manager.py` (neu oder erweitern)
  
- [ ] **P1.4.2**: Integriere in PLAN-Phase
  - Bei CODE_TASK: Optional Branch erstellen (User-Choice)
  - `/task branch` = Neue Branch, `/task direct` = Direkt auf main
  - **Files**: `core/phases.py` (L150-180)
  
- [ ] **P1.4.3**: Erweitere `/status` um Branch-Info
  - Zeige: Aktueller Branch, Commits ahead of main
  - **Files**: `core/system_status.py` (L200-250)

**Erfolgskriterium**: Experimentelle Tasks in separaten Branches

---

#### P1.5: Lint/Type-Check Integration
**Ziel**: Automatische Code-Quality-Checks

**Tasks**:
- [ ] **P1.5.1**: Implementiere Linter-Auto-Detection
  - Python: pylint, ruff, black (check)
  - JS/TS: eslint, prettier (check)
  - Go: golangci-lint
  - **Files**: `core/lint_detector.py` (neu)
  
- [ ] **P1.5.2**: Erstelle `LintRunner`
  - Tool: `run_lint(files=[])` → Gibt Warnings/Errors
  - Parse Lint-Output
  - **Files**: `core/agent_tools.py` (L900-1050)
  
- [ ] **P1.5.3**: Integriere in VERIFY-Phase
  - Nach Tests: Linter laufen
  - Bei Errors: Optional Auto-Fix (black/prettier)
  - **Files**: `core/phases.py` (L1100-1150)

**Erfolgskriterium**: Code-Quality wird automatisch geprüft

---

#### P1.6: Plan Approval UI
**Ziel**: User sieht und bestätigt Plan vor Execution

**Tasks**:
- [ ] **P1.6.1**: Erstelle `show_plan()` in `cli_ui.py`
  - Formatierung: Numbered list mit Details
  - Pro Step: Action, File, Description
  - **Files**: `core/cli_ui.py` (L600-700)
  
- [ ] **P1.6.2**: Implementiere Interactive Approval
  - Zeige Plan
  - Options: [y] Approve, [n] Cancel, [e] Edit Plan, [s] Skip Step
  - **Files**: `core/cli_ui.py` (L750-850)
  
- [ ] **P1.6.3**: Plan-Edit-Mode
  - User kann Steps ändern/löschen/reordern
  - Simple Text-Edit-Interface
  - **Files**: `core/cli_ui.py` (L900-1000)

**Erfolgskriterium**: User hat Kontrolle über Plan vor Execution

---

#### P1.7: Manifest System (RYX_MANIFEST.yaml)
**Ziel**: Per-Project Configuration

**Tasks**:
- [ ] **P1.7.1**: Definiere Manifest-Schema
  - Schema: theme_files, test_commands, critical_paths, conventions
  - YAML-Format
  - **Files**: `core/manifest_schema.py` (neu)
  
- [ ] **P1.7.2**: Erstelle `ManifestLoader`
  - Suche: ./ → ../ → ../../ (bis Git-Root)
  - Load + Validate
  - **Files**: `core/manifest_loader.py` (neu)
  
- [ ] **P1.7.3**: Integriere in `RepoExplorer`
  - Verwende manifest.theme_files für File-Tagging
  - Verwende manifest.critical_paths für Warnings
  - **Files**: `core/repo_explorer.py` (L200-250)
  
- [ ] **P1.7.4**: Verwende in `TestRunner` + `LintRunner`
  - Test-Command aus Manifest
  - **Files**: `core/agent_tools.py` (L850-900)

**Erfolgskriterium**: Projekt-spezifische Configs werden respektiert

---

### 🟢 P2: Nice-to-Have Features (Später)

#### P2.1: Multi-Agent Orchestration
**Tasks**:
- [ ] **P2.1.1**: Vollständige Supervisor-Operator-Integration
- [ ] **P2.1.2**: Agent-Communication-Protocol
- [ ] **P2.1.3**: Parallel-Operator-Execution (für unabhängige Tasks)

#### P2.2: LLM Council (Multi-Model Consensus)
**Tasks**:
- [ ] **P2.2.1**: Council-Prompting für kritische Entscheidungen
- [ ] **P2.2.2**: Vote-Aggregation (Mehrheit gewinnt)
- [ ] **P2.2.3**: Cost-Optimization (nur bei Unsicherheit aktivieren)

#### P2.3: Advanced RAG
**Tasks**:
- [ ] **P2.3.1**: Code-Embeddings für semantische Suche
- [ ] **P2.3.2**: Incremental Indexing (nur Changed-Files)
- [ ] **P2.3.3**: Context-Ranking für LLM-Prompt

#### P2.4: Learning System
**Tasks**:
- [ ] **P2.4.1**: Track successful resolutions
- [ ] **P2.4.2**: User-Preference-Learning
- [ ] **P2.4.3**: Export/Import-Learned-Patterns

#### P2.5: Web UI (RyxHub)
**Tasks**:
- [ ] **P2.5.1**: React-Frontend (bereits begonnen in `ryx_pkg/interfaces/web/`)
- [ ] **P2.5.2**: WebSocket für Streaming
- [ ] **P2.5.3**: Visualisierung von Workflow-Graphs

---

## 🎯 Empfohlene Umsetzungsreihenfolge

### Top 10: Schnellste Reliability-Verbesserung

| # | Task | Impact | Aufwand | Ratio |
|---|------|--------|---------|-------|
| 1 | **P0.3: Automatic File Finder** | 🔥🔥🔥 | 2-3 Tage | 10/10 |
| 2 | **P0.2: Diff-Based Editing** | 🔥🔥🔥 | 1-2 Tage | 9/10 |
| 3 | **P0.5: Test Execution** | 🔥🔥 | 2-3 Tage | 8/10 |
| 4 | **P1.2: Hallucination Detection** | 🔥🔥 | 1 Tag | 9/10 |
| 5 | **P0.4: Git Auto-Commit** | 🔥🔥 | 1-2 Tage | 8/10 |
| 6 | **P1.1: LLM Self-Critique** | 🔥 | 2 Tage | 7/10 |
| 7 | **P1.3: Error Recovery Loop** | 🔥🔥 | 2-3 Tage | 7/10 |
| 8 | **P1.6: Plan Approval UI** | 🔥 | 1 Tag | 8/10 |
| 9 | **P0.1: Tool-Only Output** | 🔥🔥🔥 | 3-4 Tage | 7/10 |
| 10 | **P1.5: Lint/Type-Check** | 🔥 | 1-2 Tage | 7/10 |

**Begründung**:
- **File Finder**: Eliminiert 80% der Halluzinationen
- **Diff-Editing**: Macht Änderungen reviewbar und reversibel
- **Test Execution**: Fängt Bugs sofort
- **Hallucination Detection**: Stoppt LLM vor dummem Output
- **Git-Integration**: Safety-Net für alle Änderungen

---

### Top 10: Annäherung an Claude Code/Aider

| # | Task | Claude-Like | Aider-Like | Score |
|---|------|-------------|------------|-------|
| 1 | **P0.3: File Finder + RepoMap** | ✅✅✅ | ✅✅✅ | 10/10 |
| 2 | **P0.2: Diff-Based Editing** | ✅✅✅ | ✅✅✅ | 10/10 |
| 3 | **P0.5: Test Execution + Verify** | ✅✅✅ | ✅✅ | 9/10 |
| 4 | **P0.4: Git Auto-Commit** | ✅✅ | ✅✅✅ | 9/10 |
| 5 | **P1.1: Self-Critique** | ✅✅✅ | ✅ | 8/10 |
| 6 | **P1.6: Plan Approval UI** | ✅✅✅ | ✅✅ | 8/10 |
| 7 | **P0.1: Tool-Only Mode** | ✅✅ | ✅ | 7/10 |
| 8 | **P1.7: Manifest System** | ✅ | ✅✅✅ | 7/10 |
| 9 | **P1.3: Error Recovery** | ✅✅ | ✅✅ | 7/10 |
| 10 | **P1.4: Branch-Per-Task** | ✅ | ✅✅ | 6/10 |

**Begründung**:
- **Claude Code**: Fokus auf Self-Critique, Plan-Approval, Tool-Struktur
- **Aider**: Fokus auf RepoMap, Diff-Editing, Git-Integration, Manifest
- Beide: Automatische File-Finding, Test-Execution, Structured Workflow

---

## 📐 Implementierungs-Guidelines für Agenten

### Für automatisierte Umsetzung (Copilot/Claude/Aider/Ryx):

#### Format jeder Task:
```markdown
### Task: {ID} - {Title}

**Ziel**: {1-Satz-Beschreibung}

**Files**:
- Create: `{path}` (falls neu)
- Edit: `{path}` (Zeilen {X-Y} oder Funktion {name})
- Test: `{test_path}`

**Acceptance Criteria**:
1. {Kriterium 1}
2. {Kriterium 2}

**Test Command**: `{pytest/npm test/go test command}`

**Estimated LOC**: ~{Zahl}

**Dependencies**: {Liste von Task-IDs, die vorher erledigt sein müssen}
```

#### Task-Splitting-Regeln:
1. **Max 300 LOC pro Task** (außer bei Boilerplate)
2. **1 Task = 1 Concern** (z.B. "Implementiere Tool" ist 1 Task)
3. **Testbar**: Jede Task hat klare Acceptance Criteria
4. **Atomar**: Task kann unabhängig committed werden

#### Testing-Strategie:
```bash
# Nach jeder Task:
1. Run existing tests: pytest tests/ -v
2. Run new tests: pytest tests/test_{feature}.py -v
3. Check imports: python -m core.{module}
4. Quick smoke test: ryx "test task"
```

#### Commit-Message-Format:
```
{Task-ID}: {Title}

- {Change 1}
- {Change 2}

Refs: RYX_PLAN.md #{Task-ID}
```

---

## 📚 Referenzen & Inspiration

### Architektur-Patterns
- **Claude Code**: https://docs.anthropic.com/claude/docs/tool-use
- **Aider**: https://aider.chat/docs/repomap.html
- **Copilot Workspace**: https://githubnext.com/projects/copilot-workspace
- **Devin AI**: https://www.cognition-labs.com/blog

### Tool-Design
- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/
- **Anthropic Tool Use**: https://docs.anthropic.com/claude/docs/tool-use-examples
- **OpenAI Function Calling**: https://platform.openai.com/docs/guides/function-calling

### Code-Editing-Best-Practices
- **Unified Diff Format**: https://www.gnu.org/software/diffutils/manual/html_node/Detailed-Unified.html
- **Git Workflow**: https://www.atlassian.com/git/tutorials/comparing-workflows
- **Aider Search/Replace**: https://aider.chat/docs/usage/editing.html

---

## 🚀 Quick Start für Entwickler

### Neue Task implementieren:
```bash
# 1. Task aus Plan aussuchen (z.B. P0.3.1)
# 2. Branch erstellen
git checkout -b task/P0.3.1-integrate-repo-explorer

# 3. Code schreiben (siehe Files in Task)
nvim core/ryx_brain.py  # Edit Zeilen 300-350

# 4. Tests schreiben
nvim tests/test_repo_integration.py

# 5. Testen
pytest tests/test_repo_integration.py -v
ryx "test the repo explorer"  # Manual smoke test

# 6. Committen
git add core/ryx_brain.py tests/test_repo_integration.py
git commit -m "P0.3.1: Integrate RepoExplorer in ryx_brain

- Import RepoExplorer in ryx_brain.py
- Call scan() on CODE_TASK intent
- Store repomap in context

Refs: RYX_PLAN.md #P0.3.1"

# 7. PR erstellen (optional)
gh pr create --title "P0.3.1: Integrate RepoExplorer" --body "See RYX_PLAN.md"
```

### Komplexere Tasks (Multi-File):
```bash
# Verwende Aider oder Ryx selbst:
aider core/ryx_brain.py core/repo_explorer.py tests/test_repo_integration.py

# Oder mit Ryx:
ryx "implement task P0.3.1 from RYX_PLAN.md"
```

---

## 📈 Fortschritts-Tracking

### Weekly Check:
```bash
# Zähle erledigte Tasks
grep -c "- \[x\]" RYX_PLAN.md

# Test Coverage
pytest --cov=core --cov-report=term-missing

# Performance
python dev/benchmarks/benchmark_phases.py
```

### Monatliche Review:
- Aktualisiere Checklisten-Status in diesem Doc
- Re-Evaluiere Prioritäten (P0/P1/P2)
- Neuer Fortschritts-Score (Target: +10% pro Monat)

---

## 🎉 Erfolgskriterien (Done-Definition)

Ryx ist "Claude Code/Aider-level", wenn:

1. ✅ **Hallucination-Rate < 5%** (aktuell ~40%)
2. ✅ **Task-Success-Rate > 80%** (aktuell ~30%)
3. ✅ **Auto-Test-Execution funktioniert**
4. ✅ **Alle Changes sind Git-Commits mit easy Undo**
5. ✅ **LLM findet Files selbst (keine erfundenen Pfade)**
6. ✅ **Diff-Based Editing ist Standard**
7. ✅ **Self-Critique erkennt 70%+ der eigenen Fehler**
8. ✅ **User kann Plan vor Execution reviewen/ändern**

---

**Letzte Aktualisierung**: 2025-12-03  
**Nächste Review**: 2025-12-10  
**Maintainer**: tobi + Ryx AI Community

---

*Dieser Plan ist ein lebendes Dokument. Agenten (Copilot/Claude/Aider/Ryx) können ihn lesen und direkt Tasks umsetzen. PRs zur Verbesserung willkommen!*

---

## 🔧 Aider-basierte Infrastruktur

### Übernommene Konzepte und Module

Die folgenden Module wurden basierend auf Aider-Konzepten für Ryx implementiert:

| Aider-Konzept | Ryx-Modul | Beschreibung |
|---------------|-----------|--------------|
| `repomap.py` | `ryx_pkg/repo/repo_map.py` | Repository-Indexierung mit tree-sitter und PageRank |
| `repo.py` (GitRepo) | `ryx_pkg/git/git_manager.py` | Git-Operationen mit Safety-Features |
| `editblock_coder.py` | `ryx_pkg/editing/search_replace.py` | Search/Replace-Block-Editing |
| `diffs.py` | `ryx_pkg/editing/diff_editor.py` | Unified-Diff-Application |
| `linter.py` | `ryx_pkg/testing/test_runner.py` | Test-Execution und Parsing |

### Neue Module im Detail

#### `ryx_pkg/repo/` - Repository Understanding

```
ryx_pkg/repo/
├── __init__.py
├── repo_map.py      # Tree-sitter basierte Code-Analyse, PageRank für Relevanz
├── file_selector.py # Keyword-basierte Dateiauswahl
└── explorer.py      # High-level API für Ryx-Agents
```

**Nutzung:**
```python
from ryx_pkg.repo import RepoExplorer

explorer = RepoExplorer("/path/to/project")
files = explorer.find_for_task("fix the login button")
context = explorer.get_context_for_llm(files)
```

**Kernfunktionen:**
- `find_for_task(task)`: Findet relevante Dateien basierend auf Aufgabenbeschreibung
- `get_context_for_llm(files)`: Generiert LLM-Kontext mit Definitionen
- `scan()`: Indexiert Repository mit Caching
- Automatische Erkennung: Python, JavaScript, TypeScript, Go, Rust

#### `ryx_pkg/git/` - Git-Integration

```
ryx_pkg/git/
├── __init__.py
├── git_manager.py   # Core Git-Operationen
├── safety.py        # Pre-commit Checks, Backups, Recovery
└── commit_helper.py # Commit-Message-Generierung
```

**Nutzung:**
```python
from ryx_pkg.git import GitManager, GitSafety

git = GitManager("/path/to/repo")
status = git.get_status()
diff = git.get_diff(files=["path/to/file.py"])
commit_hash = git.safe_commit("feat: add feature", files=["path/to/file.py"])
git.undo()  # Rollback
```

**Kernfunktionen:**
- `get_status()`: Aktueller Git-Status (Branch, Modified, Staged)
- `get_diff()`: Unified-Diff für Dateien
- `safe_commit()`: Commit mit Ryx-Attribution
- `undo(n)`: Letzte n Commits rückgängig machen
- `create_branch()`: Task-Branch erstellen
- Safety-Layer: Verhindert Commits von Secrets, große Dateien, etc.

#### `ryx_pkg/editing/` - Diff-basiertes Editing

```
ryx_pkg/editing/
├── __init__.py
├── diff_editor.py     # Unified-Diff-Application
├── search_replace.py  # Search/Replace-Blocks
└── validator.py       # Syntax- und Safety-Validierung
```

**Nutzung:**
```python
from ryx_pkg.editing import DiffEditor, SearchReplace

# Diff-basiert
editor = DiffEditor()
result = editor.apply_diff("path/to/file.py", diff_text)

# Search/Replace
sr = SearchReplace()
result = sr.replace_in_file("path/to/file.py", search, replace)
```

**Kernfunktionen:**
- `apply_diff()`: Wendet Unified-Diffs an mit Fuzzy-Matching
- `generate_diff()`: Erstellt Diffs aus Original/Modified
- `replace_in_file()`: Search/Replace mit Fuzzy-Matching
- Automatische Backups vor Änderungen
- Syntax-Validierung (Python, JSON)

#### `ryx_pkg/testing/` - Test-Execution

```
ryx_pkg/testing/
├── __init__.py
├── test_runner.py  # Test-Ausführung und Parsing
└── detector.py     # Framework-Erkennung
```

**Nutzung:**
```python
from ryx_pkg.testing import TestRunner, detect_framework

runner = TestRunner("/path/to/project")
result = runner.run()
print(result.summary)  # "✓ 42/42 tests passed"

# Nur für geänderte Dateien
result = runner.run_for_files(["src/login.py"])
```

**Unterstützte Frameworks:**
- pytest (Python)
- jest/npm test (JavaScript/TypeScript)
- go test (Go)
- cargo test (Rust)
- Automatische Erkennung via Marker-Files

---

## 🔗 Integration in Ryx Core

### Nächste Schritte zur Integration

Die neuen Module müssen in `core/ryx_brain.py` integriert werden:

#### 1. RepoExplorer bei CODE_TASK aktivieren

```python
# In core/ryx_brain.py, ca. Zeile 300

from ryx_pkg.repo import RepoExplorer

class RyxBrain:
    def __init__(self, ...):
        ...
        self.repo_explorer = RepoExplorer(root=os.getcwd())
    
    def _handle_code_task(self, plan: Plan):
        # Automatisch relevante Dateien finden
        files = self.repo_explorer.find_for_task(plan.target or self.ctx.last_query)
        context = self.repo_explorer.get_context_for_llm(files)
        
        # Context an LLM übergeben
        self.ctx.relevant_files = files
        ...
```

#### 2. Git-Integration für Commits

```python
# In core/phases.py, ca. Zeile 800

from ryx_pkg.git import GitManager, GitSafety

class PhaseExecutor:
    def __init__(self, ...):
        ...
        self.git = GitManager()
        self.git_safety = GitSafety(self.git)
    
    def _apply_phase(self, step: PlanStep):
        # Backup vor Änderungen
        backup = self.git_safety.create_backup_point("pre-apply")
        
        # Änderungen durchführen
        result = self._execute_step(step)
        
        # Auto-Commit
        if result.success:
            self.git.safe_commit(f"Apply: {step.description}", files=result.files)
```

#### 3. Diff-Editing statt Full-File-Writes

```python
# In core/agent_tools.py, erweitern

from ryx_pkg.editing import DiffEditor, SearchReplace

class WriteFileTool(AgentTool):
    def execute(self, path: str, content: str = None, diff: str = None, **params):
        if diff:
            # Diff-basiert
            editor = DiffEditor()
            result = editor.apply_diff(path, diff)
            return ToolResult(success=result.success, output=result.message)
        else:
            # Fallback: Full-file (legacy)
            ...
```

#### 4. Test-Execution in VERIFY-Phase

```python
# In core/phases.py, ca. Zeile 900

from ryx_pkg.testing import TestRunner

class PhaseExecutor:
    def _verify_phase(self, changes: List[str]):
        runner = TestRunner()
        
        # Tests für geänderte Dateien
        result = runner.run_for_files(changes)
        
        if not result.success:
            self.cli.show_error(f"Tests failed: {result.summary}")
            return False
        
        self.cli.show_success(result.summary)
        return True
```

---

## 🛠️ RyxHub & RyxSurf Andockpunkte

Die neuen Module sind so entworfen, dass sie später auch von RyxHub und RyxSurf genutzt werden können:

### RyxHub (Zentrale Orchestrierung)

```
ryx_hub/
├── orchestrator.py    # Nutzt: ryx_pkg/repo, ryx_pkg/git, ryx_pkg/testing
├── service_manager.py # Startet/Stoppt Ryx-Services
├── api/               # REST/WebSocket API
└── dashboard/         # Web-Dashboard
```

**Andockpunkte:**
- `ryx_pkg/repo/`: Project-Scanning für alle verbundenen Projekte
- `ryx_pkg/git/`: Git-Status-Dashboard, Multi-Repo-Commits
- `ryx_pkg/testing/`: CI/CD-Integration, Test-Dashboard

### RyxSurf (Browser/Web-Automation)

```
ryx_surf/
├── browser.py         # Browser-Steuerung (Playwright/Selenium → später eigener Browser)
├── page_analyzer.py   # Nutzt: ryx_pkg/repo (für lokale Dateien)
├── scraper.py         # Web-Scraping
└── automation/        # Task-Automation
```

**Andockpunkte:**
- `ryx_pkg/editing/`: Lokale Dateien aus Browser-Kontext editieren
- `ryx_pkg/git/`: Downloads direkt committen
- `ryx_pkg/testing/`: Web-Tests (Playwright-basiert)

---

## 📋 Aktualisierte TODO-Liste (Post-Aider-Integration)

### ✅ Erledigt (durch Aider-Integration)

- [x] **P0.2**: Diff-Based Editing → `ryx_pkg/editing/diff_editor.py`
- [x] **P0.3**: Automatic File Finder → `ryx_pkg/repo/`
- [x] **P0.4**: Git Auto-Commit → `ryx_pkg/git/git_manager.py`
- [x] **P0.5**: Test Execution → `ryx_pkg/testing/test_runner.py`

### ✅ Erledigt (Core-Integration)

#### P0.6: Integration in ryx_brain.py
**Ziel**: Neue Module in Core-Flow integrieren

- [x] **P0.6.1**: Import und Init von RepoExplorer in RyxBrain
  - ✅ Integriert in `core/phases.py` PhaseExecutor._init_aider_modules()
  - **Files**: `core/phases.py` (L397-430)

- [x] **P0.6.2**: find_for_task() bei CODE_TASK aufrufen
  - ✅ EXPLORE-Phase nutzt repo_explorer.find_for_task()
  - **Files**: `core/phases.py` (L458-530)

- [x] **P0.6.3**: GitManager in PhaseExecutor integrieren
  - ✅ VERIFY-Phase nutzt git_manager.safe_commit()
  - **Files**: `core/phases.py` (L397-430, L934-1020)

- [x] **P0.6.4**: DiffEditor in ApplyDiffTool aktivieren
  - ✅ ApplyDiffTool nutzt DiffEditor mit Fuzzy-Matching
  - **Files**: `core/agent_tools.py` (L242-300)

- [x] **P0.6.5**: TestRunner in VERIFY-Phase
  - ✅ test_runner.run_for_files() in VERIFY integriert
  - **Files**: `core/phases.py` (L934-1020)

### 🔄 Jetzt Priorität: P0.7 Tool-Only Mode

#### P0.7: Tool-Only LLM Output
**Ziel**: LLM generiert nur strukturierte Tool-Calls

- [ ] **P0.7.1**: JSON-Schema für Tool-Calls definieren
  - **Files**: `core/tool_schema.py` (neu)
  - **LOC**: ~100

- [ ] **P0.7.2**: Prompts für Tool-Only-Mode anpassen
  - **Files**: `core/ryx_brain.py` (Prompt-Strings)
  - **LOC**: ~50

- [ ] **P0.7.3**: Tool-Call-Parser in ollama_client
  - **Files**: `core/ollama_client.py` (L150-250)
  - **LOC**: ~80

### 🟡 P1: Self-Critique und UI

- [ ] **P1.1**: Self-Critique-Prompt erstellen
- [ ] **P1.2**: Git-Status in CLI-Header anzeigen
- [ ] **P1.3**: Diffs vor Apply anzeigen mit Confirmation
- [ ] **P1.4**: Test-Ergebnisse formatiert anzeigen

### 📋 P2: RyxHub & RyxSurf Vorbereitung

- [ ] **P2.1**: RyxHub-Ordnerstruktur erstellen
- [ ] **P2.2**: RyxSurf-Ordnerstruktur erstellen
- [ ] **P2.3**: Gemeinsame API-Schnittstelle definieren

---

## 🧪 Testing der neuen Module

```bash
# Repo-Module testen
python -c "from ryx_pkg.repo import RepoExplorer; e = RepoExplorer(); print(e.find_for_task('fix theme'))"

# Git-Module testen
python -c "from ryx_pkg.git import GitManager; g = GitManager(); print(g.format_status())"

# Editing-Module testen
python -c "from ryx_pkg.editing import DiffEditor; d = DiffEditor(); print('DiffEditor ready')"

# Testing-Module testen
python -c "from ryx_pkg.testing import TestRunner, detect_framework; print(detect_framework())"
```

---

## 📜 Lizenzhinweise

Die Module in `ryx_pkg/` sind inspiriert von und basieren teilweise auf:

- **Aider** (https://github.com/paul-gauthier/aider) - Apache 2.0 License
  - RepoMap-Konzept und PageRank-Algorithmus
  - Search/Replace-Block-Format
  - Git-Attribution-Logik

Ryx ist ein eigenständiges Projekt von Tobi und unterliegt seiner eigenen Lizenz.
