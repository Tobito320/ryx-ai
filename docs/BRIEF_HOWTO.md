# 📄 Briefe & Dokumente - So machst du es richtig einfach

## 🎯 Was kann das System?

### 1. **Automatische Dokument-Analyse**
- PDF-Briefe automatisch lesen
- Typ erkennen (Rechnung, Mahnung, Bescheid, etc.)
- Fristen und Deadlines finden
- Priorität bewerten (HOCH/MITTEL/NIEDRIG)
- Zusammenfassung erstellen

### 2. **Brief-Vorlagen (Templates)**
Fertige Vorlagen für:
- ✅ Widerspruch gegen Bescheid
- ✅ Kündigung eines Vertrags
- ✅ Beschwerde über Dienstleistung
- ✅ Fristverlängerung beantragen

### 3. **AI-Antworten generieren**
- Brief analysieren lassen
- Automatisch passende Antwort vorschlagen
- Du musst nur noch deine Daten eintragen

---

## 📂 Deine Dokumente Ordner-Struktur

```
/home/tobi/documents/
├── azubi/          # Ausbildung, Berufsschule
├── arbeit/         # Job-Dokumente
├── aok/            # Krankenkasse
├── sparkasse/      # Bank
├── auto/           # KFZ, TÜV
└── familie/        # Wohnung, Miete
```

**Wichtig:** Dokumente immer in die richtigen Ordner legen!

---

## 🚀 SCHNELLSTART - Board Mode

### Schritt 1: Board öffnen
```
http://localhost:8080 → "Board" Tab klicken
```

### Schritt 2: Dokumente automatisch organisieren
1. Klicke auf **"🤖 AI Organisieren"**
2. System lädt alle PDFs aus `/home/tobi/documents/`
3. Analysiert jeden Brief automatisch
4. Zeigt auf dem Board:
   - 📄 Dateiname
   - 📋 Typ (Rechnung, Mahnung, etc.)
   - ⏰ Priorität
   - ⚠️ Fristen (wenn vorhanden)
   - 📝 Kurzzusammenfassung

### Schritt 3: Brief-Vorlage verwenden
1. Öffne: `http://localhost:8420/api/templates`
2. Wähle Template (z.B. `widerspruch_bescheid`)
3. Kopiere Text
4. Fülle deine Daten ein
5. Fertig!

---

## 📋 Brief-Vorlagen nutzen

### Vorlage ansehen:
```bash
curl http://localhost:8420/api/templates/widerspruch_bescheid
```

### Alle Vorlagen:
```bash
curl http://localhost:8420/api/templates
```

### Eigene Vorlage erstellen:
1. Erstelle Datei: `/home/tobi/.ryx/brief_templates/mein_template.txt`
2. Schreibe Template-Text
3. Sofort verfügbar über API

---

## 🤖 API - Für Entwickler

### Dokument analysieren:
```bash
curl -X POST http://localhost:8420/api/documents/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/tobi/documents/familie/Anklage.pdf"}'
```

**Antwort:**
```json
{
  "type": "Brief",
  "sender": "Wohnungsverwaltung XY",
  "date": "03.12.2025",
  "subject": "Anklage bezüglich Heizung",
  "deadlines": [
    {
      "date": "15.12.2025",
      "days_left": 8,
      "urgent": true
    }
  ],
  "requires_response": true,
  "priority": "HOCH",
  "summary": "..."
}
```

### Antwort-Brief generieren:
```bash
curl -X POST http://localhost:8420/api/documents/generate-response \
  -H "Content-Type: application/json" \
  -d '{"document_path": "/home/tobi/documents/familie/Anklage.pdf", "response_type": "standard"}'
```

---

## 💡 PRO TIPPS

### 1. **Fristen im Blick**
- Rote Notizen auf Board = DRINGEND (< 14 Tage)
- System zeigt automatisch "Tage verbleibend"

### 2. **Kategorien nutzen**
- Jeder Ordner = eigene Farbe
- Familie = grau
- AOK = grün
- Sparkasse = blau
- Auto = rot
- Azubi = orange
- Arbeit = violett

### 3. **Templates anpassen**
- Kopiere Template aus `/home/tobi/.ryx/brief_templates/`
- Passe an deine Bedürfnisse an
- Speichere mit neuem Namen
- Sofort verfügbar!

### 4. **Batch-Verarbeitung**
- Lege alle neuen Briefe in Ordner
- Klick "🤖 AI Organisieren"
- System verarbeitet ALLE automatisch

---

## 🔮 ZUKÜNFTIGE FEATURES (Coming Soon)

- [ ] **OCR für gescannte Briefe** - Auch Scans lesbar machen
- [ ] **Deadline-Reminder** - Email/Notification bei Fristen
- [ ] **AI Brief schreiben** - "Schreib Antwort auf diesen Brief"
- [ ] **Versionshistorie** - Alte Versionen von Briefen speichern
- [ ] **Gmail Integration** - Direkt aus Board versenden
- [ ] **Unterschrift einfügen** - PDF mit digitaler Signatur

---

## 🆘 PROBLEM? 

### PDF wird nicht analysiert?
```bash
# Check ob pdfplumber installiert ist:
source /home/tobi/ryx-ai/venv/bin/activate
pip list | grep pdfplumber

# Falls nicht:
pip install pdfplumber pypdf
```

### API antwortet nicht?
```bash
# Backend neu starten:
pkill -f uvicorn
cd /home/tobi/ryx-ai
source venv/bin/activate
uvicorn ryx_core.api:app --host 0.0.0.0 --port 8420
```

### Board zeigt keine Dokumente?
- Prüfe ob Dateien in `/home/tobi/documents/` liegen
- Müssen PDFs sein
- Klick "Refresh" Button

---

## 📞 Support

Bei Problemen: Schreib einfach im Chat!

**Beispiele:**
- "Analysiere mein AOK Dokument"
- "Erstelle eine Kündigungsvorlage"
- "Zeig mir alle Briefe mit Fristen"
- "Schreib Antwort auf den Brief von gestern"

---

*Erstellt: 2025-12-07*  
*Version: 1.0 - Document Intelligence System*
