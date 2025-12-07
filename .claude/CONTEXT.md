# 🎯 RYXHUB BOARD MODE - VOLLSTÄNDIGER KONTEXT

> **Für neue Chat-Sessions:** Sage einfach "starte improvement" und arbeite diese TODOs ab.

---

## 👤 USER PROFIL

```yaml
Name: Tobi
Adresse: Alleestraße 58, 58097 Hagen
Situation: Azubi, will Erwachsenenleben einfacher machen
Hardware: AMD RX 7800 XT (16GB VRAM)
OS: Arch Linux mit Hyprland
```

---

## 🎯 VISION

**Tony Stark Holographic Desk** - Ein digitaler Schreibtisch für Dokumente:
- Dokumente als Karten/Stacks auf einem Board
- AI Sidebar rechts (resizable)
- Gmail Multi-Account Integration
- Memory System (lernt über User)
- Müllabfuhr-Kalender Integration
- Web Search für Öffnungszeiten etc.
- **ULTRA MINIMAL** wie n8n Design

---

## 📁 WICHTIGE PFADE

```
/home/tobi/ryx-ai/                    # Hauptprojekt
/home/tobi/ryx-ai/ryxhub/             # Frontend + Backend
/home/tobi/ryx-ai/ryxhub/frontend/    # React/Vite
/home/tobi/ryx-ai/ryxhub/backend/     # Python FastAPI
/home/tobi/ryx-ai/configs/            # vLLM, Hyprland configs
/home/tobi/documents/                 # Dokumente (AUTO-SYNC!)
/home/tobi/Downloads/alleestrassehagen.ics  # Müllkalender
```

---

## 🔧 TECH STACK

```yaml
Frontend: React + Vite + TypeScript
UI: Tailwind CSS (n8n-style minimal)
Backend: Python FastAPI
LLM: vLLM (lokal)
Search: SearXNG (Docker)
Database: SQLite
```

---

## 🤖 MODELS

**Empfohlen für Board Mode:**
- **Qwen2.5-14B-Instruct-GPTQ** - Hauptmodel (Deutsch, Dokumente)
- **Qwen2.5-3B** - Schnelle Tasks (Klassifizierung)

**Aktuell installiert:**
```
/home/tobi/models/qwen2.5-14b-instruct-gptq-int4/
/home/tobi/models/qwen2.5-3b/
/home/tobi/models/qwen2.5-coder-14b-instruct-gptq-int4/  # NICHT LÖSCHEN aber nicht nötig
```

**vLLM Config:** `/home/tobi/ryx-ai/configs/vllm_config.yaml`
- GPU Utilization: 100%
- Default Model: qwen2.5-14b (NICHT 3b!)

---

## 🚨 KRITISCHE TODOS (PRIORITÄT)

### P0 - BROKEN / NICHT FUNKTIONAL - ✅ ALL FIXED

1. **✅ Search kaputt** - FIXED: SearXNG funktioniert, in Smart Chat integriert
2. **✅ Gmail Button tut nichts** - FIXED: App-Password Authentifizierung implementiert
3. **✅ Dokumente klicken tut nichts** - FIXED: Preview + Doppelklick zum Öffnen
4. **✅ Falsches Default Model** - FIXED: 14B Model läuft (qwen2.5-14b-gptq)
5. **✅ AI kennt Datum nicht** - FIXED: System prompt enthält aktuelles Datum

### P1 - UI/UX PROBLEME

1. **✅ AI Sidebar nicht resizable** - FIXED: Bereits implementiert mit GripVertical
2. **✅ Design zu "fettig"** - FIXED: Cleaner overview dashboard
3. **✅ Dokument-Namen overflow** - FIXED: CSS truncate + break-words
4. **✅ Button nesting warning** - FIXED: Replaced nested buttons with divs
5. **✅ Kein Drag & Drop** - FIXED: Bereits implementiert (TODO: Upload API)
6. **✅ Kein visueller File-Type** - FIXED: PDF/Word/etc Icons vorhanden
7. **✅ Keine Tool Toggles** - FIXED: Memory/Search/Scrape toggles + localStorage persist

### P2 - FEATURES FEHLEN

1. **✅ Müllkalender Integration** - FIXED: ICS parsing in /api/trash/schedule
2. **✅ Memory System** - FIXED: /api/memory + /api/memory/fact endpoints
3. **✅ Termine/Reminders** - FIXED: /api/reminders CRUD endpoints
4. **❌ PDF Preview/Edit** - Formulare ausfüllen mit AI
5. **✅ Email Composer** - FIXED: /api/gmail/compose mit AI
6. **✅ Web Scraping** - FIXED: /api/scrape für Öffnungszeiten etc.

### P3 - NEW FEATURES ADDED

1. **✅ Overview Dashboard** - Personal desktop with trash schedule, reminders, recent docs
2. **✅ Streaming Chat** - SSE streaming with abort capability
3. **✅ Better AI Context** - Improved system prompts for document understanding
4. **✅ Quick Actions** - Buttons for Dokumente, AI Chat, WebUntis, Gmail
5. **❌ WebUntis Integration** - Berufsschule schedule (needs API)
6. **❌ Holiday Calendar** - NRW Feiertage
7. **❌ Drag & Drop Widgets** - Movable dashboard widgets

---

## 📋 DESIGN REQUIREMENTS

```yaml
Style: n8n-inspired, minimal, clean
Colors: Dark theme, subtle grays, accent color for actions
Spacing: Compact, nicht zu viel padding
Typography: Clean, readable, nicht zu groß
Cards: Kleine Document-Karten mit Icon + Name
Sidebar: Sticky rechts, resizable (min 300px, max 50%)
```

---

## 🔌 API ENDPOINTS (Backend)

```
GET  /api/documents          # Liste Dokumente
POST /api/documents/upload   # Upload
GET  /api/documents/{id}     # Details
POST /api/chat               # AI Chat
GET  /api/memory             # User Memory
POST /api/memory             # Memory speichern
GET  /api/trash-schedule     # Müllkalender
GET  /api/gmail/accounts     # Gmail Accounts
POST /api/gmail/connect      # OAuth starten
GET  /api/search             # Web Search
```

---

## 🚀 COMMANDS

```bash
ryx start           # Startet vLLM + SearXNG
ryx ryxhub          # Startet RyxHub (Frontend + Backend)
ryx restart all     # Neustart alles
ryx stop            # Stoppt alles
```

---

## 📝 NÄCHSTE SCHRITTE

1. **FIX: vLLM Default Model auf 14B setzen**
2. **FIX: SearXNG Connection prüfen**
3. **FIX: Document-Karten overflow/positioning**
4. **ADD: Resizable AI Sidebar**
5. **ADD: Drag & Drop Upload**
6. **ADD: File-Type Icons**
7. **ADD: Gmail OAuth Flow**
8. **REDESIGN: Compact n8n-style**

---

## 💡 WICHTIGE HINWEISE

- **KEIN tldraw** - War zu kompliziert, einfaches Grid-Layout besser
- **100% GPU** - RX 7800 XT kann das
- **Mobile Support** - Muss vom Handy im Netzwerk nutzbar sein
- **Deutsch bevorzugt** - User spricht Deutsch
- **Concise AI** - Kurze Antworten, kein Gelaber

---

## 🔗 EXTERNE RESSOURCEN

- Müllabfuhr: https://www.heb-hagen.de/rund-um-den-muell/termine/abfuhrkalender-wann-kommt-die-muellabfuhr.html
- Termine Hagen: https://terminvergabe.hagen.de/
- ICS Datei: /home/tobi/Downloads/alleestrassehagen.ics

---

**Letztes Update:** 2025-12-07
