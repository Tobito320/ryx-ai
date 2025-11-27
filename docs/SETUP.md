# 🎯 Ryx AI - Complete Setup Guide

Follow these steps **exactly** to install Ryx AI from the artifacts.

## 📦 Prerequisites Check

```bash
# Check Python
python3 --version  # Should be 3.11+

# Check Docker
docker --version

# Check Ollama
ollama --version

# If missing, install:
sudo pacman -S python python-pip docker
curl https://ollama.ai/install.sh | sh
```

## 📥 Step 1: Organize Downloaded Files

You've downloaded all artifacts to `~/Downloads`. Let's organize them:

```bash
# Go to Downloads
cd ~/Downloads

# Create project directory
mkdir -p ~/ryx-ai
cd ~/ryx-ai

# Create subdirectories
mkdir -p core tools modes configs data/cache data/history docker docs
```

## 📋 Step 2: Place Files in Correct Locations

### Core Files (Python modules)

```bash
# Move to ~/ryx-ai/core/
mv ~/Downloads/ryx_core_ai.py ~/ryx-ai/core/ai_engine.py
mv ~/Downloads/ryx_rag.py ~/ryx-ai/core/rag_system.py
mv ~/Downloads/ryx_permissions.py ~/ryx-ai/core/permissions.py
mv ~/Downloads/ryx_self_improve.py ~/ryx-ai/core/self_improve.py

# Create __init__.py
touch ~/ryx-ai/core/__init__.py
```

### Tools (Advanced features)

```bash
# Move to ~/ryx-ai/tools/
mv ~/Downloads/ryx_tools.py ~/ryx-ai/tools/

# Split tools.py into separate files
cd ~/ryx-ai/tools

# Create scraper.py
cat > scraper.py << 'EOF'
# Extract WebScraper class from ryx_tools.py
# (You'll copy this section manually)
EOF

# Create browser.py
cat > browser.py << 'EOF'
# Extract WebBrowser class from ryx_tools.py
EOF

# Create council.py
cat > council.py << 'EOF'
# Extract Council class from ryx_tools.py
EOF

# Create __init__.py
touch __init__.py

cd ~/ryx-ai
```

**Note**: You'll need to split `ryx_tools.py` manually. Each file should contain its respective class (WebScraper, WebBrowser, Council). I'll provide the exact split in the next artifact.

### Modes (CLI and Session)

```bash
# Move to ~/ryx-ai/modes/
mv ~/Downloads/ryx_cli_mode.py ~/ryx-ai/modes/cli_mode.py
mv ~/Downloads/ryx_session_mode.py ~/ryx-ai/modes/session_mode.py

# Create __init__.py
touch ~/ryx-ai/modes/__init__.py
```

### Docker Configuration

```bash
# Move to ~/ryx-ai/docker/
mv ~/Downloads/ryx_docker_setup.py ~/ryx-ai/docker/docker-compose.yml
mv ~/Downloads/ryx_dockerfile.txt ~/ryx-ai/Dockerfile
mv ~/Downloads/ryx_cleanup_script.sh ~/ryx-ai/docker/cleanup.sh

# Make cleanup script executable
chmod +x ~/ryx-ai/docker/cleanup.sh
```

### Requirements and Config

```bash
# Requirements
mv ~/Downloads/ryx_requirements.txt ~/ryx-ai/requirements.txt

# Documentation
mv ~/Downloads/ryx_main_readme.md ~/ryx-ai/README.md
mv ~/Downloads/ryx_setup_guide.md ~/ryx-ai/docs/SETUP.md
```

### Main Entry Point

```bash
# Create main ryx executable
cat > ~/ryx-ai/ryx << 'EOF'
#!/usr/bin/env python3
"""
Ryx AI - Main Entry Point
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.home() / "ryx-ai"))

def main():
    args = sys.argv[1:]
    
    if not args:
        # Show status/help
        from modes.cli_mode import show_status
        show_status()
    elif args[0].startswith("::"):
        # Command mode
        from modes.cli_mode import handle_command
        handle_command(args[0], args[1:])
    else:
        # Direct prompt mode
        from modes.cli_mode import handle_prompt
        prompt = " ".join(args)
        handle_prompt(prompt)

if __name__ == "__main__":
    main()
EOF

# Make executable
chmod +x ~/ryx-ai/ryx
```

## 🔧 Step 3: Fix Import Statements

Some files need import fixes. Let's update them:

### Fix modes/cli_mode.py

```bash
nvim ~/ryx-ai/modes/cli_mode.py
```

At the top, change imports to:

```python
from core.ai_engine import AIEngine, ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm
```

Save and exit (`:wq`)

### Fix modes/session_mode.py

```bash
nvim ~/ryx-ai/modes/session_mode.py
```

Same import fix as above.

### Fix core files if needed

Most core files are self-contained, but check for any relative imports.

## 🐍 Step 4: Install Python Dependencies

```bash
cd ~/ryx-ai

# Install dependencies
pip3 install --user -r requirements.txt

# Verify installation
python3 -c "import rich, requests, bs4; print('✓ Dependencies OK')"
```

## 🗄️ Step 5: Initialize Database

```bash
# Run the initialization from install.sh manually
python3 << 'PYTHON'
import sqlite3
from pathlib import Path

db_path = Path.home() / "ryx-ai" / "data" / "rag_knowledge.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Knowledge table
cursor.execute("""
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    file_type TEXT,
    file_path TEXT NOT NULL,
    content_preview TEXT,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    confidence REAL DEFAULT 1.0
)
""")

# Quick responses cache
cursor.execute("""
CREATE TABLE IF NOT EXISTS quick_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash TEXT UNIQUE NOT NULL,
    response TEXT NOT NULL,
    model_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 1,
    ttl_seconds INTEGER DEFAULT 86400
)
""")

# Command history
cursor.execute("""
CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    result TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Indexes
cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_hash ON knowledge(query_hash)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompt_hash ON quick_responses(prompt_hash)")

conn.commit()
conn.close()

print("✓ Database initialized")
PYTHON
```

## ⚙️ Step 6: Install Configuration Files

The install.sh creates these automatically. Run it now:

```bash
cd ~/ryx-ai

# Copy install.sh from artifacts
mv ~/Downloads/ryx_install.sh ~/ryx-ai/install.sh

# Make executable
chmod +x install.sh

# Run installer
./install.sh
```

This will:
- Create all config files
- Initialize database
- Download AI models
- Set up symlinks

## 🔗 Step 7: Create System-Wide Command

```bash
# Create symlink
sudo ln -sf ~/ryx-ai/ryx /usr/local/bin/ryx

# Verify
which ryx
# Should output: /usr/local/bin/ryx

# Test
ryx
# Should show status screen
```

## 🤖 Step 8: Download AI Models

```bash
# Start Ollama if not running
ollama serve &

# Download recommended models
ollama pull deepseek-coder:6.7b     # Fast (3.8GB)
ollama pull qwen2.5-coder:14b       # Balanced (8GB)

# Verify
ollama list
```

## ✅ Step 9: Test Installation

### Test 1: Basic Command

```bash
ryx "hello world"
```

Expected: AI responds with greeting

### Test 2: File Finding

```bash
ryx "find hyprland config"
```

Expected: Searches for and displays config location

### Test 3: Session Mode

```bash
ryx ::session
```

Type some prompts, then `/quit` to exit

### Test 4: Status Check

```bash
ryx ::status
```

Expected: Shows system status, cache stats

## 🐛 Common Issues & Fixes

### Issue: "Command not found: ryx"

```bash
# Recreate symlink
sudo ln -sf ~/ryx-ai/ryx /usr/local/bin/ryx

# Make sure it's executable
chmod +x ~/ryx-ai/ryx
```

### Issue: "ModuleNotFoundError"

```bash
# Check imports
cd ~/ryx-ai
python3 ryx
# Look at error message

# Reinstall dependencies
pip3 install --user -r requirements.txt
```

### Issue: "Cannot connect to Ollama"

```bash
# Start Ollama
ollama serve &

# Check status
curl http://localhost:11434/api/tags
```

### Issue: Import errors in tools

```bash
# Make sure tools are split correctly
ls -la ~/ryx-ai/tools/

# Should have:
# scraper.py
# browser.py
# council.py
# __init__.py
```

## 🎨 Step 10: Customize (Optional)

### Configure AI Settings

```bash
nvim ~/ryx-ai/configs/settings.json
```

Change:
- Default model
- Temperature
- Cache settings

### Configure Permissions

```bash
nvim ~/ryx-ai/configs/permissions.json
```

Add/remove allowed commands

### Add Hyprland Autostart

```bash
# Edit hyprland.conf
nvim ~/.config/hyprland/hyprland.conf

# Add at the end:
exec-once = ollama serve
```

## 🎉 Step 11: Final Verification

Run the complete test suite:

```bash
# 1. Status
ryx ::status

# 2. Simple query
ryx "test prompt"

# 3. File operation
ryx "open ~/.bashrc"

# 4. Session mode
ryx ::session
# Type: hello
# Type: /quit

# 5. Help
ryx ::help

# 6. Self-improve
ryx ::improve analyze
```

If all tests pass, you're ready to go! 🚀

## 📚 Next Steps

1. Read the full README: `cat ~/ryx-ai/README.md`
2. Try different commands
3. Let it learn your system
4. Schedule auto-cleanup
5. Customize to your workflow

## 🆘 Need Help?

If stuck:
1. Check logs: `~/ryx-ai/data/history/commands.log`
2. Run diagnostics: `ryx ::status`
3. Check database: `sqlite3 ~/ryx-ai/data/rag_knowledge.db "SELECT * FROM quick_responses;"`
4. Review error messages carefully
5. Make sure all files are in correct locations

---

**Installation complete! Enjoy Ryx AI! 🎉**