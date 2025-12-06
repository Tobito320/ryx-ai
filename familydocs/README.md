# 🏠 FamilyDocs Intelligence Hub

**Ein neuer Ansatz für Familiendokumente: Board + Chat Hybrid mit KI**

FamilyDocs ist ein intelligentes Dokumentenmanagementsystem, das ein flexibles Board-System (wie Figma/Miro) mit einem kontextbewussten Chat kombiniert.

---

## 🎯 Vision

Statt klassischer Ordnerstrukturen und starrer Workflows bietet FamilyDocs:

- **Flex Board System** – Infinite Canvas für visuelle Organisation (Police/Vision-Board Style)
- **Intelligent Chat Mode** – 100% RAG-integriert mit Multi-Agent-System
- **Smart Modules** – Müllabfuhr-Widgets, Gmail-Reader, Brief-Generator
- **Kontextuelle KI** – Qwen 2.5 32B für intelligente Dokumentenanalyse

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAMILYDOCS INTELLIGENCE HUB                  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  FLEX BOARD  │  │ CHAT ENGINE  │  │  MODULE SYSTEM      │  │
│  │  (React Flow)│  │  (Multi-Agent)│  │  (Integrations)     │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
│        ↓                   ↓                    ↓              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  FASTAPI BACKEND (Async + WebSockets)                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│        ↓                                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  RAG LAYER (LanceDB + Qwen 2.5 Embeddings)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│        ↓                                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  vLLM ENGINE (Qwen 2.5 32B via OpenAI API)              │  │
│  └─────────────────────────────────────────────────────────┘  │
│        ↓                                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  STORAGE: PostgreSQL + Redis + File System              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React + Vite + TypeScript | UI Framework |
| **Canvas** | React Flow | Infinite Board System |
| **UI Components** | shadcn/ui (Radix) | Beautiful UI |
| **State** | TanStack React Query | API State Management |
| **Backend** | FastAPI (Python 3.11) | API Server |
| **Database** | PostgreSQL 16 | Relational Data |
| **Cache** | Redis 7 | Session & API Cache |
| **LLM** | vLLM + Qwen 2.5 32B | AI Engine |
| **RAG** | LanceDB | Vector Search |
| **OCR** | Tesseract | Document Extraction |
| **PC Sync** | Watchdog | Folder Synchronization |

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose**
- **AMD GPU** with ROCm (RX 7800 XT recommended)
- **16GB VRAM** for Qwen 2.5 32B
- **32GB RAM** recommended

### 1. Clone Repository

```bash
cd /home/user/ryx-ai/familydocs
```

### 2. Configure Environment

```bash
# Backend
cp backend/.env.example backend/.env

# Edit backend/.env:
# - Set PC_SYNC_ROOT=C:/FamilyDocs (Windows) or /mnt/familydocs (Linux)
# - Configure vLLM model path
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **vLLM** on port 8002
- **Backend API** on port 8420
- **Frontend** on port 5174

### 4. Access FamilyDocs

```bash
# Frontend
open http://localhost:5174

# API Docs
open http://localhost:8420/docs

# Health Check
curl http://localhost:8420/api/health
```

---

## 📁 Project Structure

```
familydocs/
├── backend/                    # FastAPI Backend
│   ├── api/
│   │   ├── routes/
│   │   │   ├── boards.py      # ✅ Board CRUD + PC Sync
│   │   │   ├── documents.py   # 🔄 Document Upload + OCR
│   │   │   ├── chat.py        # 🔄 Multi-Agent Chat
│   │   │   ├── modules.py     # 🔄 Smart Modules
│   │   │   └── rag.py         # 🔄 Vector Search
│   │   └── services/
│   │       ├── board_service.py      # ✅ Board Business Logic
│   │       ├── pc_sync_service.py    # ✅ PC Folder Sync
│   │       ├── chat_service.py       # 🔄 Multi-Agent System
│   │       └── rag_service.py        # 🔄 RAG Integration
│   ├── database/
│   │   ├── connection.py      # ✅ Async SQLAlchemy
│   │   └── models.py          # ✅ Database Models
│   ├── config.py              # ✅ Configuration
│   ├── main.py                # ✅ FastAPI App
│   └── requirements.txt       # ✅ Python Dependencies
│
├── frontend/                   # React Frontend (TODO)
│   ├── src/
│   │   ├── components/
│   │   │   ├── board/         # 🔄 Infinite Canvas
│   │   │   ├── chat/          # 🔄 Chat Sidebar
│   │   │   └── modules/       # 🔄 Widget System
│   │   ├── hooks/
│   │   │   ├── useBoards.ts   # 🔄 Board API Hooks
│   │   │   └── useChat.ts     # 🔄 Chat API Hooks
│   │   └── types/
│   │       └── familydocs.ts  # 🔄 TypeScript Types
│   └── package.json
│
├── database/
│   ├── schema.sql             # ✅ PostgreSQL Schema
│   └── seed.sql               # ✅ Test Data
│
├── docker-compose.yml         # ✅ Infrastructure Setup
└── README.md                  # ✅ This file
```

**Legend:**
- ✅ Implemented
- 🔄 Placeholder / TODO

---

## 🎯 Phase 1: Foundation (COMPLETED ✅)

### Database
- ✅ PostgreSQL schema with UUID, JSONB, arrays
- ✅ Tables: boards, documents, board_documents, board_links, chat_sessions, chat_messages, modules
- ✅ Triggers for auto-update timestamps
- ✅ Views for stats (board_stats, active_sessions)
- ✅ Seed data for testing

### Backend API
- ✅ FastAPI with async SQLAlchemy
- ✅ Board CRUD endpoints
- ✅ Board hierarchy (parent-child)
- ✅ Board links (relationships)
- ✅ PC folder sync (create, archive, rename)
- ✅ Document-to-board linking
- ✅ Health check & status endpoints

### Docker Infrastructure
- ✅ PostgreSQL 16
- ✅ Redis 7
- ✅ vLLM with Qwen 2.5 32B (GPTQ quantized)
- ✅ FastAPI backend
- ✅ React frontend (placeholder)

---

## 🔄 Phase 2: Frontend & Chat (NEXT)

### Extend RyxHub Frontend
- 🔄 Adapt ryxhub components for FamilyDocs
- 🔄 Infinite Canvas with React Flow
- 🔄 Board Cards (nodes) with drag & drop
- 🔄 Board links (edges) visualization
- 🔄 Drill-down navigation (parent → children)
- 🔄 Canvas ↔ Folder View toggle

### Chat Integration
- 🔄 Flexible Chat Sidebar (resizable, floating)
- 🔄 Multi-Agent System (Document Analyst, Board Planner, Brief Generator)
- 🔄 RAG integration for context-aware responses
- 🔄 Chat session management
- 🔄 Message history with tool calls

---

## 🔄 Phase 3: Smart Modules (FUTURE)

- 🔄 Müllabfuhr Widget (HEB Hagen API)
- 🔄 Gmail Reader (OAuth + read-only)
- 🔄 Brief Generator (AI-powered letter writing)
- 🔄 Document Writer (Emails, Anfragen)

---

## 🔧 Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run locally (without Docker)
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8420
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build
```

### Database Migrations

```bash
# Connect to PostgreSQL
docker exec -it familydocs-postgres psql -U familydocs -d familydocs

# Run schema manually
\i /docker-entrypoint-initdb.d/01-schema.sql

# Run seed data
\i /docker-entrypoint-initdb.d/02-seed.sql
```

---

## 📊 API Endpoints

### Boards

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/boards/` | Create board |
| GET | `/api/boards/` | List boards |
| GET | `/api/boards/{id}` | Get board |
| PATCH | `/api/boards/{id}` | Update board |
| DELETE | `/api/boards/{id}` | Delete board |
| POST | `/api/boards/{id}/sync` | Sync to PC |
| POST | `/api/boards/{id}/links` | Create link |
| GET | `/api/boards/{id}/links` | Get links |
| POST | `/api/boards/{id}/documents/{doc_id}` | Add document |
| DELETE | `/api/boards/{id}/documents/{doc_id}` | Remove document |
| GET | `/api/boards/{id}/children` | Get children |
| GET | `/api/boards/{id}/ancestors` | Get breadcrumb |
| GET | `/api/boards/stats/overview` | Get statistics |

### Documents (TODO)
- POST `/api/documents/upload` – Upload & analyze document
- GET `/api/documents/` – List documents
- GET `/api/documents/{id}` – Get document
- DELETE `/api/documents/{id}` – Delete document

### Chat (TODO)
- POST `/api/chat/sessions` – Create chat session
- GET `/api/chat/sessions` – List sessions
- POST `/api/chat/sessions/{id}/messages` – Send message
- GET `/api/chat/sessions/{id}/messages` – Get messages

### Modules (TODO)
- POST `/api/modules/` – Create module
- GET `/api/modules/` – List modules
- POST `/api/modules/{id}/refresh` – Refresh module data

### RAG (TODO)
- GET `/api/rag/status` – RAG system status
- POST `/api/rag/search` – Semantic search
- POST `/api/rag/sync` – Sync vector index

---

## 🧪 Testing

```bash
# Test backend health
curl http://localhost:8420/api/health

# Test board creation
curl -X POST http://localhost:8420/api/boards/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Board", "type": "board", "description": "Test"}'

# Test board listing
curl http://localhost:8420/api/boards/

# Test vLLM
curl http://localhost:8002/v1/models
```

---

## 🤝 Integration mit Ryx-AI

FamilyDocs nutzt die bestehende **vLLM-Infrastruktur** von ryx-ai:

- **Shared vLLM Backend** – Beide Systeme können denselben vLLM-Server nutzen
- **Separate Ports** – FamilyDocs (8002) vs. Ryx-AI (8001)
- **Separate Datenbanken** – PostgreSQL für FamilyDocs, SQLite für Ryx-AI
- **Gemeinsame Models** – Qwen 2.5 Modelle werden geteilt

---

## 📝 Next Steps

1. ✅ **Backend Foundation** – DONE!
2. 🔄 **Frontend Infinite Canvas** – Extend ryxhub with React Flow
3. 🔄 **Chat Integration** – Multi-Agent System mit RAG
4. 🔄 **Document Upload** – OCR + AI Analysis
5. 🔄 **Smart Modules** – Müllabfuhr, Gmail, Brief-Generator

---

## 🎓 Hardware Requirements

**Optimal für deine Hardware (AMD 7800 XT + Ryzen 5900X):**

- **GPU**: AMD RX 7800 XT (16 GB VRAM) ✅
- **CPU**: Ryzen 5900X (12 Cores) ✅
- **RAM**: 32 GB ✅
- **Model**: Qwen 2.5 32B GPTQ (int4) ✅
  - Fits in 16 GB VRAM with quantization
  - ~20-40 tokens/sec inference speed
  - Excellent for German + English

---

## 📄 License

MIT License (same as ryx-ai)

---

**Made with 🟣 for smart family document management**
