# RyxHub UI

Web-basiertes Control Center für das Ryx AI Ökosystem.

**Standort**: Integriert im Hauptrepo unter `/ryxhub/`

## 🚀 Quick Start

```bash
# Via Ryx CLI (empfohlen)
ryx starte ryxhub

# Oder manuell
cd ryxhub
npm install
npm run dev

# Öffne http://localhost:5173
```

## 📁 Projektstruktur

```
src/
├── components/
│   ├── ryxhub/           # Haupt-UI Komponenten
│   │   ├── ChatView.tsx       # Chat-Interface mit Sessions
│   │   ├── DashboardView.tsx  # Übersichts-Dashboard
│   │   ├── WorkflowCanvas.tsx # Workflow-Editor (Nodes + Connections)
│   │   ├── LeftSidebar.tsx    # Sessions, Models, RAG, Actions
│   │   ├── RightInspector.tsx # Node-Details (Params/Logs/Runs)
│   │   └── ViewToggle.tsx     # Tab-Navigation
│   └── ui/               # shadcn/ui Komponenten
├── context/
│   └── RyxHubContext.tsx # Globaler State (Sessions, Models, Workflows)
├── data/
│   └── mockData.ts       # Realistische Dummy-Daten
├── hooks/
│   ├── index.ts
│   └── useRyxApi.ts      # React Query Hooks für alle API-Calls
├── lib/
│   └── api/
│       ├── client.ts     # HTTP-Client für Ryx-Backend
│       ├── mock.ts       # Mock-Implementierung
│       └── index.ts
├── services/
│   └── ryxService.ts     # Unified Service (Mock ↔ Live)
├── types/
│   └── ryxhub.ts         # TypeScript Interfaces
└── pages/
    ├── Index.tsx         # Haupt-Layout
    └── NotFound.tsx
```

## 🎯 Features

### Dashboard
- **Stats Cards**: Active Agents, Workflows Running, RAG Docs, API Calls
- **Recent Activity**: Echtzeit-Feed der letzten Aktionen
- **Top Workflows**: Performance-Übersicht mit Success-Rates

### Chat
- **Multi-Session**: Mehrere Chat-Sessions gleichzeitig
- **Message History**: Vollständiger Chat-Verlauf pro Session
- **Copy/Clear**: Nachrichten kopieren, Chat löschen
- **Model Info**: Aktuelles Modell pro Session sichtbar

### Workflow Canvas
- **Visual Editor**: Drag & Drop Node-Canvas
- **Node Types**: Trigger, Agent, Tool, Output
- **Connections**: SVG-basierte Verbindungen mit Pfeilen
- **Inspector Panel**: Details zu jedem Node (Params, Logs, Runs)
- **Run/Pause**: Workflow starten/stoppen

### Left Sidebar
- **Sessions**: Alle Chat-Sessions mit Quick-Switch
- **Active Models**: Ollama/vLLM Status
- **RAG Index**: Sync-Status und Dokument-Count
- **Quick Actions**: Agents, Tools, Sources, Triggers

## 🔌 Backend-Integration

### Environment Variables

```bash
# .env.local
VITE_RYX_API_URL=http://localhost:8420   # Ryx Backend URL
VITE_USE_MOCK_API=false                   # true = Mock, false = Live
```

### API Endpoints (erwartet)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/health` | GET | Health Check |
| `/api/status` | GET | System Status |
| `/api/models` | GET | Liste aller Modelle |
| `/api/models/load` | POST | Modell laden |
| `/api/sessions` | GET/POST | Sessions verwalten |
| `/api/sessions/:id/messages` | POST | Nachricht senden |
| `/api/rag/status` | GET | RAG Index Status |
| `/api/rag/sync` | POST | RAG Sync starten |
| `/api/workflows` | GET | Workflows auflisten |
| `/api/workflows/:id/run` | POST | Workflow starten |
| `/api/agents` | GET | Agents auflisten |
| `/api/tools` | GET | Tools auflisten |

### Service Usage

```typescript
import { ryxService } from '@/services/ryxService';

// Automatisch Mock oder Live je nach Config
const models = await ryxService.listModels();
const status = await ryxService.getRagStatus();
```

### React Query Hooks

```typescript
import { useModels, useSessions, useRagStatus } from '@/hooks';

function MyComponent() {
  const { data: models, isLoading } = useModels();
  const { data: sessions } = useSessions();
  const { data: ragStatus } = useRagStatus();
  
  // ...
}
```

## 🎨 Styling

- **Framework**: Tailwind CSS
- **Components**: shadcn/ui (Radix-based)
- **Theme**: Dark Mode by default
- **Colors**: Primary (Purple), Accent (Cyan), Success (Green), Warning (Orange)

## 🛠 Development

```bash
# Lint
npm run lint

# Build
npm run build

# Preview Production Build
npm run preview
```

## 📝 TODO

- [ ] WebSocket für Echtzeit-Updates
- [ ] Streaming Chat Responses
- [ ] Workflow Node Drag & Drop
- [ ] Settings/Config Page
- [ ] User Authentication
- [ ] RyxSurf Browser Integration

## 🔗 Teil des Ryx Ökosystems

- **Ryx CLI** - Terminal AI Assistant
- **RyxHub** - Web Control Center (dieses Projekt)
- **RyxSurf** - Browser Automation (geplant)
