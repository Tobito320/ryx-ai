# RYX Plan - Board Mode Implementation

## Überblick

Board Mode ersetzt den alten Workflow-View und bietet einen Infinite Canvas für:
- Dokumente organisieren
- Notizen erstellen
- E-Mails verwalten (Gmail Multi-Account)
- Persönliches Wissen speichern (Memory)

## Implementierte Features

### 1. Board View mit tldraw
- Infinite Canvas mit Touch-Support (Mobile-optimiert)
- Dokumente als Notizen auf dem Board platzieren
- Farbcodierung nach Kategorie (AOK=grün, Sparkasse=blau, etc.)
- E-Mail Entwürfe direkt auf dem Board erstellen

### 2. Document Scanner
- Scannt `/home/tobi/documents/` automatisch
- Unterstützte Ordner:
  - `azubi/` - Berufsschule, Ausbildung
  - `arbeit/` - Arbeit, Job
  - `aok/` - Krankenkasse
  - `sparkasse/` - Bank
  - `auto/` - KFZ, Fahrzeug
- Unterstützte Dateitypen: PDF, PNG, JPG, DOC, DOCX, TXT

### 3. Memory System
- Speichert persönliches Wissen
- Typen: fact, preference, contact, template, routine
- Wird vom AI genutzt um bessere Antworten zu geben
- Daten in `data/user_memory.json`

### 4. Gmail Multi-Account
- Mehrere Gmail-Konten verbinden
- Ein Default-Konto für normale E-Mails
- Im Prompt sagen "nutze Account X" für andere Konten
- Daten in `data/gmail_accounts.json`

## Entfernte Features
- Workflow Canvas (komplett entfernt)
- Council View (entfernt aus Navigation)
- Alle Workflow-bezogenen Komponenten

## API Endpoints

### Documents
- `GET /api/documents/scan` - Scannt Dokumente
  - Query: `path`, `category`, `search`

### Memory
- `GET /api/memory` - Liste aller Erinnerungen
- `POST /api/memory` - Neue Erinnerung erstellen
- `DELETE /api/memory/{id}` - Erinnerung löschen

### Gmail
- `GET /api/gmail/accounts` - Liste aller Konten
- `POST /api/gmail/accounts` - Konto hinzufügen
- `DELETE /api/gmail/accounts/{id}` - Konto entfernen
- `PUT /api/gmail/accounts/{id}/default` - Als Standard setzen

### Boards
- `GET /api/boards` - Liste aller Boards
- `POST /api/boards` - Board erstellen
- `DELETE /api/boards/{id}` - Board löschen

## Nächste Schritte
1. Gmail OAuth Integration
2. RAG-Anbindung für Dokumente
3. Brief-Template System
4. AI Memory Learning (automatisch Fakten lernen)

## Nutzung

```bash
# RyxHub starten
./scripts/start_ryxhub.sh

# Oder einzeln
cd ryxhub && npm run dev  # Frontend
python -m ryx_core.api    # Backend
```

## Mobile Nutzung
- Im gleichen Netzwerk: `http://[PC-IP]:5173`
- tldraw unterstützt Touch und Pinch-to-Zoom
- Optimiert für einhändige Bedienung
