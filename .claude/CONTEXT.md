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

### P0 - BROKEN / NICHT FUNKTIONAL

1. **❌ Search kaputt** - SearXNG antwortet nicht, API Fehler
2. **❌ Gmail Button tut nichts** - Kein OAuth Flow implementiert
3. **❌ Dokumente klicken tut nichts** - Preview fehlt
4. **❌ Falsches Default Model** - 3B statt 14B wird geladen
5. **❌ AI kennt Datum nicht** - Sagt "April 2023" statt aktuelles Datum

### P1 - UI/UX PROBLEME

1. **❌ AI Sidebar nicht resizable** - Muss drag-to-resize haben
2. **❌ Design zu "fettig"** - Muss COMPACT und MINIMAL wie n8n
3. **❌ Dokument-Namen overflow** - Gehen aus den Boxen raus
4. **❌ Angeklickte Docs gehen aus Layout** - Positioning broken
5. **❌ Kein Drag & Drop** - Dokumente hochladen fehlt
6. **❌ Kein visueller File-Type** - PDF/Word/etc Icons fehlen
7. **❌ Keine Tool Toggles** - Memory/Search/Gmail toggles fehlen

### P2 - FEATURES FEHLEN

1. **❌ Müllkalender Integration** - ICS parsen, Reminder zeigen
2. **❌ Memory System** - Langzeit-Gedächtnis für User-Infos
3. **❌ Termine/Reminders** - Aus Emails extrahieren
4. **❌ PDF Preview/Edit** - Formulare ausfüllen mit AI
5. **❌ Email Composer** - AI-assistiertes Email schreiben
6. **❌ Web Scraping** - Öffnungszeiten, Termine etc.

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
