# Ollama Migration - RyxHub

## ✅ Abgeschlossen

RyxHub nutzt jetzt **Ollama** als primäres Inference-Backend (statt vLLM).

## Vorteile

- **Multi-Model**: Mehrere Modelle gleichzeitig verfügbar
- **Auto-Management**: Ollama lädt/entlädt Modelle automatisch
- **Einfacher**: Kein Docker, kein komplexes Setup
- **AMD ROCm**: Perfekte Unterstützung für RX 7800 XT

## Backend-Änderungen

### Neue API Endpoints

```bash
# Health Check
GET /api/health
# Response: { status, ollama_status, searxng_status, models_available }

# List Models
GET /api/models
# Response: { models: [{ id, name, size, modified, status }] }

# Load Model
POST /api/models/{model_name}/load
# Response: { message: "Model loaded successfully" }

# Unload Model
POST /api/models/{model_name}/unload
# Response: { message: "Model unloaded successfully" }

# Chat
POST /api/chat
# Body: { message, model?, stream? }
# Response: { response, model, latency_ms }

# Smart Chat (mit Web-Suche)
POST /api/chat/smart
# Body: { message, model?, use_search? }
# Response: { response, model, latency_ms }

# Search
GET /api/search?q=<query>
# Response: { results: [...], query }
```

## Frontend-Änderungen

### Settings View

- **Ollama Status**: Zeigt ob Ollama läuft (Port 11434)
- **SearXNG Status**: Zeigt ob Suche verfügbar ist (Port 8888)
- **Models**: Liste aller verfügbaren Modelle
  - **Load Button**: Lädt Modell in Speicher
  - **Unload Button**: Gibt Speicher frei
  - **Size Badge**: Zeigt Modellgröße in GB

### Removed

- vLLM Metriken (KV Cache, Tokens, etc.)
- Progress Bars für Cache Usage
- Multi-Instance Router
- vLLM-spezifische Konfiguration

## Verwendung

### 1. Ollama starten

```bash
ollama serve
```

### 2. Modelle pullen (einmalig)

```bash
# Für RyxHub (Standard)
ollama pull qwen2.5-coder:7b

# Für schnelle Aufgaben
ollama pull qwen2.5:1.5b

# Für komplexe Aufgaben
ollama pull qwen2.5-coder:14b
```

### 3. RyxHub starten

```bash
ryx ryxhub
```

Das lädt automatisch `qwen2.5-coder:7b` und startet:
- Backend API auf Port 8420
- Frontend auf Port 8080
- SearXNG auf Port 8888

### 4. Modelle verwalten

Im Browser: `http://localhost:8080` → Settings

- Siehst alle verfügbaren Modelle
- Kannst Modelle laden/entladen
- System Status in Echtzeit

## Test

```bash
# Health Check
curl http://localhost:8420/api/health | jq

# List Models
curl http://localhost:8420/api/models | jq

# Chat
curl -X POST http://localhost:8420/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hallo!","model":"qwen2.5-coder:7b"}' | jq

# Smart Chat mit Web-Suche
curl -X POST http://localhost:8420/api/chat/smart \
  -H "Content-Type: application/json" \
  -d '{"message":"Python 3.13 neue Features?","use_search":true}' | jq

# Load Model
curl -X POST http://localhost:8420/api/models/qwen2.5:1.5b/load

# Unload Model
curl -X POST http://localhost:8420/api/models/qwen2.5:1.5b/unload
```

## Konfiguration

### Environment Variables

```bash
# Backend
OLLAMA_BASE_URL="http://localhost:11434"  # Ollama API
SEARXNG_URL="http://localhost:8888"       # SearXNG Search
RYX_API_PORT="8420"                       # RyxHub API Port

# Frontend
VITE_RYX_API_URL="http://localhost:8420"  # Backend URL
VITE_USE_MOCK_API="false"                 # Use real API
```

### Default Model

In `ryx_pkg/interfaces/web/backend/main.py`:

```python
DEFAULT_MODEL = "qwen2.5-coder:7b"
```

## Nächste Schritte

1. ✅ Ollama Backend funktioniert
2. ✅ Modellverwaltung im Frontend
3. ✅ SearXNG Integration
4. ⏳ vLLM-Code komplett entfernen
5. ⏳ Streaming Chat im Frontend
6. ⏳ Model Performance Metrics (optional)

## Probleme?

### Ollama läuft nicht

```bash
# Check
curl http://localhost:11434/api/tags

# Start
ollama serve
```

### SearXNG läuft nicht

```bash
# Start
cd /home/tobi/ryx-ai
docker compose -f docker/searxng/docker-compose.yml up -d

# Check
curl http://localhost:8888
```

### RyxHub API läuft nicht

```bash
# Check logs
tail -f /home/tobi/ryx-ai/data/ryxhub_api.log

# Restart
./ryx ryxhub restart
```

## Backup

Die alte vLLM-Version ist gesichert:

```
/home/tobi/ryx-ai/ryx_pkg/interfaces/web/backend/main.py.vllm.backup
```
