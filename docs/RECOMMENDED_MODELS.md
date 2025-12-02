# RYX AI - Empfohlene Modelle

## Übersicht: Multi-Modell-Strategie

Ryx braucht verschiedene Modelle für verschiedene Aufgaben.
Jedes Modell hat seinen optimalen Einsatzzweck.

---

## 🚀 FAST (< 3B Parameter) - Instant Response

### **Qwen2.5:1.5b** ⭐ EMPFOHLEN
```bash
ollama pull qwen2.5:1.5b
```
- **Stärke**: Extrem schnell, gutes Deutsch, überraschend intelligent
- **Nutzen**: Intent-Erkennung, einfache Fragen, Typo-Korrektur
- **VRAM**: ~2GB
- **Speed**: <100ms pro Token

### **Phi-3-mini (3.8B)** 
```bash
ollama pull phi3:mini
```
- **Stärke**: Beste Qualität unter 4B, sehr kohärent
- **Nutzen**: Schnelle Chat-Antworten, Zusammenfassungen
- **VRAM**: ~4GB

### **Gemma2:2b**
```bash
ollama pull gemma2:2b
```
- **Stärke**: Google-Qualität, gute Allgemeinbildung
- **Nutzen**: Schnelle Faktenfragen, Definitionen
- **VRAM**: ~3GB

---

## ⚖️ BALANCED (7-14B Parameter) - Allround

### **Qwen2.5:7b** ⭐ EMPFOHLEN
```bash
ollama pull qwen2.5:7b
```
- **Stärke**: Bestes Preis-Leistungs-Verhältnis, 88% HumanEval!
- **Nutzen**: Default für alles - Chat, Planung, einfaches Coding
- **VRAM**: ~8GB
- **Kontext**: 32K Tokens

### **Llama3.1:8b**
```bash
ollama pull llama3.1:8b
```
- **Stärke**: Gute Code-Generierung, natürliche Konversation
- **Nutzen**: Alternative zu Qwen, gut für englische Tasks
- **VRAM**: ~8GB
- **Kontext**: 128K Tokens!

### **Mistral:7b**
```bash
ollama pull mistral:7b
```
- **Stärke**: Schnell, effizient, 32K Kontext
- **Nutzen**: Wenn längerer Kontext wichtiger ist als max. Qualität
- **VRAM**: ~6GB

---

## 🧠 SMART (14-32B Parameter) - Komplexe Aufgaben

### **Qwen2.5-Coder:14b** ⭐ EMPFOHLEN FÜR CODING
```bash
ollama pull qwen2.5-coder:14b
```
- **Stärke**: Speziell für Code trainiert, versteht Repos
- **Nutzen**: Code-Tasks, Refactoring, Bug-Fixes, PLAN-Phase
- **VRAM**: ~12GB
- **HumanEval**: 88%+

### **DeepSeek-Coder-V2:16b**
```bash
ollama pull deepseek-coder-v2:16b
```
- **Stärke**: Sehr gut für Debugging, Fill-in-the-middle
- **Nutzen**: Code-Analyse, Erklärungen, Fehlersuche
- **VRAM**: ~14GB

### **Codestral:22b** (von Mistral)
```bash
ollama pull codestral:22b
```
- **Stärke**: 80+ Sprachen, exzellente Code-Completion
- **Nutzen**: Polyglot-Coding, wenn viele Sprachen gebraucht werden
- **VRAM**: ~16GB

---

## 🎯 PRECISION (20B+ Parameter) - Maximum Qualität

### **Qwen2.5:32b** ⭐ EMPFOHLEN
```bash
ollama pull qwen2.5:32b
```
- **Stärke**: Beste lokale Allround-Qualität, GPT-4 Level für viele Tasks
- **Nutzen**: Komplexe Planung, kritische Code-Änderungen, VERIFY-Phase
- **VRAM**: ~24GB
- **Kontext**: 128K Tokens

### **DeepSeek-R1:32b** (Distilled)
```bash
ollama pull deepseek-r1:32b
```
- **Stärke**: Chain-of-Thought Reasoning, Mathe, Logik
- **Nutzen**: Komplexe Problemlösung, mehrstufige Analysen
- **VRAM**: ~24GB
- **MMLU**: 90%+

### **Llama3.3:70b** (Quantized Q4)
```bash
ollama pull llama3.3:70b-instruct-q4_K_M
```
- **Stärke**: Größtes praktisch nutzbares Modell
- **Nutzen**: Wenn absolute Qualität wichtiger ist als Speed
- **VRAM**: ~40GB (Q4 quantized)

---

## 🔧 SPECIALIZED - Spezialaufgaben

### **Für SQL/Datenbank**
```bash
ollama pull sqlcoder:15b
```
- Speziell für SQL-Generierung trainiert

### **Für Embeddings/RAG**
```bash
ollama pull nomic-embed-text
```
- Schnelle Vektor-Embeddings für Semantic Search

### **Für Vision (Bilder)**
```bash
ollama pull llava:13b
```
- Kann Bilder analysieren (Screenshots, Diagramme)

---

## 📊 Empfohlene Ryx-Konfiguration

```yaml
# configs/models.yaml

models:
  # Blitzschnell - für Intent-Erkennung
  fast:
    default: "qwen2.5:1.5b"
    alternatives:
      - "phi3:mini"
      - "gemma2:2b"
  
  # Ausgewogen - für normalen Chat
  balanced:
    default: "qwen2.5:7b"
    alternatives:
      - "llama3.1:8b"
      - "mistral:7b"
  
  # Code-Spezialist - für PLAN/APPLY Phasen
  coding:
    default: "qwen2.5-coder:14b"
    alternatives:
      - "deepseek-coder-v2:16b"
      - "codestral:22b"
  
  # Maximum Qualität - für kritische Entscheidungen
  precision:
    default: "qwen2.5:32b"
    alternatives:
      - "deepseek-r1:32b"
      - "llama3.3:70b-instruct-q4_K_M"
  
  # Für Embeddings
  embedding: "nomic-embed-text"

# Automatische Modellauswahl
routing:
  intent_detection: "fast"
  simple_chat: "balanced"
  code_explore: "balanced"
  code_plan: "coding"
  code_apply: "coding"
  code_verify: "precision"
  web_search_synthesis: "balanced"
  complex_reasoning: "precision"
```

---

## 🏆 Top-Empfehlung für Ryx

**Minimum Setup (8GB VRAM):**
```bash
ollama pull qwen2.5:1.5b    # Fast
ollama pull qwen2.5:7b      # Balanced
```

**Optimal Setup (16GB VRAM):**
```bash
ollama pull qwen2.5:1.5b         # Fast
ollama pull qwen2.5:7b           # Balanced  
ollama pull qwen2.5-coder:14b    # Coding
```

**Power Setup (24GB+ VRAM):**
```bash
ollama pull qwen2.5:1.5b         # Fast
ollama pull qwen2.5:7b           # Balanced
ollama pull qwen2.5-coder:14b    # Coding
ollama pull qwen2.5:32b          # Precision
ollama pull deepseek-r1:32b      # Reasoning
```

---

## Warum Qwen dominiert (2024/2025)

1. **HumanEval 88%** - Schlägt sogar manche GPT-4 Versionen im Coding
2. **Multi-language** - 92+ Sprachen, exzellentes Deutsch
3. **Agentic-ready** - Trainiert für Tool-Use und Function-Calling  
4. **Große Kontext-Fenster** - Bis zu 128K Tokens
5. **Aktiv entwickelt** - Alibaba released regelmäßig Updates
6. **Effizient** - Gute Performance auch mit Quantisierung

DeepSeek ist die beste Alternative für:
- Chain-of-Thought Reasoning (R1)
- Budget-Setup (V2 Lite)
- Debugging-Tasks
