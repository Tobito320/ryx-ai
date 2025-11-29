# RAG Documentation System - Quick Start Guide

## 🚀 Complete Workflow

### 1. Scrape Documentation
```bash
ryx ::scrape https://wiki.archlinux.org/title/Hyprland
ryx ::scrape https://wiki.archlinux.org/title/Waybar
ryx ::scrape https://wiki.archlinux.org/title/Kitty
```

### 2. Ingest into RAG
```bash
python3 ~/ryx-ai/tools/rag_ingest.py
```

### 3. Query via AI
```bash
ryx "how do I configure hyprland according to arch wiki?"
```

---

## 📂 Folder Structure

```
~/ryx-ai/data/
├── scrape/           # Raw scraped content
│   ├── arch-wiki/
│   ├── documentation/
│   └── tutorials/
└── rag/              # Processed & ready
    ├── arch-wiki/
    ├── documentation/
    └── tutorials/
```

---

## 🛠 Commands

```bash
# Scrape a URL
ryx ::scrape <url>

# Ingest all docs
python3 ~/ryx-ai/tools/rag_ingest.py

# Ingest specific category
python3 ~/ryx-ai/tools/rag_ingest.py --category arch-wiki

# List categories
python3 ~/ryx-ai/tools/rag_ingest.py --list
```

---

## ✅ What's Working

- ✅ Web scraping with robots.txt respect
- ✅ Auto-categorization by URL
- ✅ Human-readable text storage
- ✅ RAG database ingestion
- ✅ Knowledge retrieval
- ✅ Instant greetings (200ms → 110ms)
- ✅ Fixed intent parser bugs

---

## 🎯 Next: Scrape Your Favorite Docs!

Try these:
- https://wiki.archlinux.org/title/Neovim
- https://wiki.archlinux.org/title/Bash
- https://wiki.archlinux.org/title/Git
- https://wiki.archlinux.org/title/Docker
