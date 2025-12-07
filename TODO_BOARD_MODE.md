# RyxHub Board Mode - TODO

**Erstellt:** 2025-12-07
**Priorität:** HÖCHSTE - Persönliche Dokumentenverwaltung + AI Assistant

---

## 🚨 KRITISCHE BUGS (sofort fixen)

### UI/UX Bugs
- [x] **Dokumente Namen gehen aus den Boxen raus** - Text overflow gefixt mit truncate + tooltip
- [x] **Design zu "fettig"** - Kompakter gemacht (padding, spacing reduziert)
- [ ] **Gmail verbinden passiert nichts** - Button funktioniert, aber OAuth fehlt
- [x] **Keine visuelle Unterscheidung PDF vs andere** - Farbige Icons nach Typ

### Funktionalität Bugs
- [x] **SearXNG verbunden** - Port 8888 funktioniert
- [x] **LLM richtiges Datum** - System Prompt enthält aktuelles Datum/Uhrzeit
- [x] **Müllabfuhr Datum richtig** - ICS wird beim Start geladen, in AI Kontext
- [ ] **Drag & Drop nicht implementiert** - Nur Toast, Backend fehlt
- [ ] **File Upload nicht implementiert** - Nur UI, keine Backend-Integration

---

## 🎨 DESIGN FIXES (n8n-style clean)

### Compact Layout
- [ ] Reduce all padding from `p-4` to `p-2` or `p-3`
- [ ] Reduce gaps from `gap-4` to `gap-2`
- [ ] Smaller font sizes: base `text-sm`, headings `text-base`
- [ ] Thinner borders: `border` statt visual heavy elements
- [ ] Remove excessive rounded corners - use `rounded` statt `rounded-lg`

### Document Cards
- [ ] **Datei Icons nach Typ:**
  - PDF → Roter PDF-Icon
  - DOC/DOCX → Blauer Word-Icon
  - PNG/JPG → Grüner Bild-Icon
  - TXT → Grauer Text-Icon
- [ ] **Text truncation:** `truncate` class + tooltip on hover
- [ ] **Fixed card sizes:** Keine variablen Größen
- [ ] **Hover state:** Subtle border color change, nicht shadow

### AI Sidebar
- [x] Resizable ✓ (bereits implementiert)
- [ ] **Memory/Search/Scrape toggles** - Tooltips hinzufügen
- [ ] **Compact messages** - Weniger padding in chat bubbles
- [ ] **Quick actions** - Mehr relevante Vorschläge

---

## 🔧 BACKEND FIXES

### API Endpoints zu fixen
- [ ] `POST /api/logs/frontend` - Logs richtig speichern
- [ ] `GET /api/gmail/accounts` - Funktioniert, aber OAuth fehlt
- [ ] `POST /api/gmail/accounts` - Account speichern ohne OAuth
- [ ] `GET /api/documents/scan` - Kategorien richtig erkennen
- [ ] `GET /api/trash/schedule` - ICS korrekt parsen

### vLLM Integration
- [x] **Richtiges Model** - Qwen2.5-14B-GPTQ läuft auf Port 8001
- [x] **System Prompt mit aktuellem Datum** - datetime.now() eingebaut
- [x] **Müllabfuhr im Kontext** - Automatisch in AI Kontext geladen
- [x] **Reminders im Kontext** - Heute's Termine im AI Kontext
- [ ] **Memory in System Prompt** - User-Profil automatisch laden
- [ ] **Concise responses** - Funktioniert, könnte noch kürzer sein

### Gmail Integration (Simplified)
- [ ] Accounts in JSON speichern (kein OAuth erstmal)
- [ ] Default Account setzen
- [ ] Später: App-Password Support für IMAP/SMTP
- [ ] Noch später: Volle OAuth Integration

---

## ✨ NEUE FEATURES

### Dokumente Sync
- [ ] **FileSystem Watcher** - `/home/tobi/documents/` auto-sync
- [ ] **Kategorien auto-detect:**
  - Dateiname enthält "AOK" → Kategorie AOK
  - Dateiname enthält "Sparkasse" → Kategorie Sparkasse
  - Ordnername als Kategorie
- [ ] **Neue Dokumente Notification** - Toast wenn neue Datei

### AI Tools
- [ ] **Tool: Email schreiben** - Mit Template + Memory
- [ ] **Tool: Brief antworten** - Dokument lesen → Antwort generieren
- [ ] **Tool: Formular ausfüllen** - PDF-Formular mit AI Hilfe
- [ ] **Tool: Termin extrahieren** - Aus Brief/Email → Reminder
- [ ] **Tool: Web Search** - Öffnungszeiten, Termine, etc.

### Müllabfuhr System
- [x] ICS File richtig parsen (`/home/tobi/Downloads/alleestrassehagen.ics`)
- [x] Automatisch beim Start laden
- [x] In AI Kontext integriert
- [ ] Nächste 7 Tage visuell anzeigen
- [ ] Reminder am Vortag
- [ ] In AI Sidebar anzeigen

### Memory System
- [ ] **User Profil speichern:**
  - Name: Tobi
  - Adresse: Alleestraße 58, 58097 Hagen
  - Email Accounts
  - Wichtige Kontakte
- [ ] **Konversations-Memory** - Letzte 10 Chats speichern
- [ ] **Dokument-Memory** - Welche Dokumente oft genutzt
- [ ] **Memory in System Prompt** - Automatisch laden

### Reminders
- [ ] **Aus Emails extrahieren** - Termine erkennen
- [ ] **Aus Briefen extrahieren** - Deadlines erkennen
- [ ] **Status-System:** Offen, Erledigt, Verpasst, Abgesagt
- [ ] **Notizen zu Terminen** - Für spätere Referenz
- [ ] **Automatisch löschen** - 1 Woche nach Termin (wenn erledigt)

### Web Tools
- [ ] **Öffnungszeiten suchen** - "Wann hat MediaMarkt auf?"
- [ ] **Termine finden** - terminvergabe.hagen.de scrapen
- [ ] **Allgemeine Suche** - SearXNG Integration fixen

---

## 🏗️ ARCHITEKTUR

### Model Strategie (vLLM)
```
Haupt-Model: Qwen2.5-14B-Instruct-GPTQ (oder besser)
- Dokumente analysieren
- Briefe schreiben
- Emails verfassen
- Allgemeine Fragen

Backup: Qwen2.5-3B-Instruct
- Schnelle Antworten
- Einfache Aufgaben
- Fallback wenn 14B busy
```

### Hyprland Autostart
```bash
# ~/.config/hypr/hyprland.conf
exec-once = docker start ryx-vllm ryx-searxng
```

### File Structure
```
/home/tobi/documents/          # Dokumente (auto-sync)
├── AOK/
├── Sparkasse/
├── Auto/
├── Azubi/
├── Arbeit/
└── Familie/

/home/tobi/ryx-ai/
├── data/
│   ├── memory/                # User Memory
│   │   ├── profile.json       # Name, Adresse, etc.
│   │   └── conversations.json # Chat History
│   ├── gmail/                 # Gmail Accounts
│   │   └── accounts.json
│   └── reminders/             # Termine
│       └── reminders.json
└── logs/
    ├── frontend/
    └── backend/
```

---

## 📋 PRIORITÄTS-REIHENFOLGE

### Phase 1: Grundfunktionen (ERLEDIGT ✅)
1. ✅ Sidebar resizable
2. ✅ Design compact gemacht
3. ✅ Dokument-Icons nach Typ (farbig)
4. ✅ Text overflow gefixt (truncate + tooltip)
5. ✅ vLLM richtiges Model + aktuelles Datum
6. ✅ Müllabfuhr ICS geladen und in AI Kontext

### Phase 2: Kern-Features (Diese Woche)
1. [ ] Memory System
2. [ ] Müllabfuhr ICS richtig parsen
3. [ ] File Upload funktionierend
4. [ ] FileSystem Watcher
5. [ ] SearXNG fixen

### Phase 3: AI Tools (Nächste Woche)
1. [ ] Email schreiben Tool
2. [ ] Brief antworten Tool
3. [ ] Termin extrahieren
4. [ ] Reminders System

### Phase 4: Polish (Später)
1. [ ] Mobile optimieren
2. [ ] Dark/Light Mode
3. [ ] Keyboard shortcuts
4. [ ] PDF Preview

---

## 🧪 TESTS

### Manuelle Tests
- [ ] Dokumente werden geladen
- [ ] Kategorien werden erkannt
- [ ] AI antwortet auf Deutsch
- [ ] AI kennt aktuelles Datum
- [ ] Müllabfuhr Datum korrekt
- [ ] Gmail Account hinzufügen
- [ ] Sidebar resize funktioniert
- [ ] Kein Text overflow

### Automatische Tests
- [ ] API Health Check
- [ ] vLLM Connection
- [ ] SearXNG Connection
- [ ] Document Scan
- [ ] Memory Load/Save

---

## 📝 NOTIZEN

### Tobi's Präferenzen
- Minimalistisches Design (wie n8n)
- Deutsch als Hauptsprache
- Kurze, präzise Antworten
- AI soll Arbeit abnehmen, nicht mehr Arbeit machen
- Einfache Bedienung - so wenig Klicks wie möglich

### Hardware
- AMD RX 7800 XT (16GB VRAM)
- vLLM mit 100% GPU Nutzung OK
- Kann 14B Models problemlos laufen

### Wichtige Pfade
- Dokumente: `/home/tobi/documents/`
- ICS Kalender: `/home/tobi/Downloads/alleestrassehagen.ics`
- Adresse: Alleestraße 58, 58097 Hagen
