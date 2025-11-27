# 🎯 Ryx AI - Quick Reference Card

## Installation (One-Time)

```bash
# 1. Download all artifacts to ~/Downloads
# 2. Create project
mkdir -p ~/ryx-ai && cd ~/ryx-ai

# 3. Run setup (see SETUP.md for detailed steps)
./install.sh

# 4. Test
ryx "hello"
```

## Daily Usage

### Basic Commands

```bash
# Simple query
ryx "how do i reload hyprland?"

# File operations
ryx "open waybar config"
ryx "find all themes"
ryx "show my keybinds"

# System info
ryx "disk usage"
ryx "running processes"
```

### Session Mode

```bash
# Start interactive session
ryx ::session

# Inside session:
You: show me my config
Ryx: [shows config]
You: /exec          # Execute pending commands
You: /quit          # Exit session
```

### Special Commands

```bash
ryx ::help          # Show all commands
ryx ::status        # System status
ryx ::config        # View settings
ryx ::models        # List AI models
ryx ::clean         # Run cleanup
```

### Advanced Tools

```bash
# Web scraping (legal/educational)
ryx ::scrape https://docs.example.com

# Web search
ryx ::browse "arch linux networking"

# Multi-model review
ryx ::council "review my code: <code>"

# Self-improvement
ryx ::improve analyze
```

## Keyboard Shortcuts

### In Session Mode

```
Ctrl+C          Interrupt (doesn't exit)
Ctrl+D          Exit session
Tab             (Future: autocomplete)
↑/↓             (Future: command history)
```

## Common Patterns

### Configuration Files

```bash
# Find config
ryx "where is my X config?"

# Open config
ryx "open X config"

# Backup config
ryx "backup my X config"

# Compare configs
ryx "diff between X and Y config"
```

### System Administration

```bash
# Safe operations (auto-approved)
ryx "show disk usage"
ryx "list running services"
ryx "check system logs"

# Modify operations (auto-approved in ~/.config)
ryx "add keybind to hyprland"
ryx "change waybar theme"

# Dangerous operations (asks confirmation)
ryx "delete old backups"
ryx "remove unused packages"
```

### Development

```bash
# Code generation
ryx "create a bash script to backup dotfiles"

# Code review
ryx ::council "rate this function: <code>"

# Documentation
ryx "explain this command: <command>"

# Debugging
ryx "why isn't X working?"
```

## File Locations

```
~/ryx-ai/                    Main directory
├── ryx                      Main executable
├── configs/                 Configuration
│   ├── settings.json       User preferences
│   ├── permissions.json    Safety rules
│   ├── models.json         AI models
│   └── commands.json       Custom commands
├── data/                    Data & cache
│   ├── rag_knowledge.db    Knowledge base
│   ├── cache/              Scraped content
│   └── history/            Command logs
└── docs/                    Documentation

/usr/local/bin/ryx           System-wide link
```

## Configuration

### Change Default Model

```bash
nvim ~/ryx-ai/configs/settings.json
# Change "default_model": "fast" to "balanced" or "powerful"
```

### Customize Permissions

```bash
nvim ~/ryx-ai/configs/permissions.json
# Add/remove commands from permission levels
```

### Add Auto-Cleanup

```bash
# Already scheduled if you answered 'y' during install
# Or manually:
crontab -e
# Add: 0 3 * * * ~/ryx-ai/docker/cleanup.sh
```

## Troubleshooting

### Ryx not responding

```bash
# Check Ollama
ollama serve

# Check status
ryx ::status

# View logs
tail -f ~/ryx-ai/data/history/commands.log
```

### Slow responses

```bash
# Check which model is used
ryx ::models

# Switch to faster model
nvim ~/ryx-ai/configs/settings.json
# Set "default_model": "fast"
```

### Cache not working

```bash
# View cache stats
ryx ::status

# Clear cache
rm ~/ryx-ai/data/rag_knowledge.db
# Will rebuild on next use
```

### Command failed

```bash
# Check error message
# Most common: permission denied

# Fix permissions
chmod +x ~/ryx-ai/ryx
sudo ln -sf ~/ryx-ai/ryx /usr/local/bin/ryx
```

## Performance Tips

### Speed Up Responses

1. Let Ryx learn (first queries are slower)
2. Use similar phrasings (better cache hits)
3. Use fast model for simple tasks
4. Keep database optimized (run ::clean weekly)

### Reduce Memory Usage

1. Use Docker mode (resource limits)
2. Set shorter model timeout
3. Limit cache size in settings
4. Unload unused models

## Best Practices

### Prompt Writing

✅ Good:
```bash
ryx "open hyprland config"
ryx "show waybar settings"
ryx "backup dotfiles"
```

❌ Avoid:
```bash
ryx "i need help with my configuration file for hyprland can you please open it?"
# Too verbose - Ryx is optimized for concise prompts
```

### Safety

✅ Always review commands before executing
✅ Use session mode for multi-step tasks
✅ Keep backups of important configs
✅ Test changes in safe environments

❌ Don't blindly execute suggested commands
❌ Don't disable permission system
❌ Don't run as root

### Learning

The more you use Ryx, the faster it gets:
- File locations are cached
- Common queries are instant
- Patterns are learned
- Context improves

## Update & Maintenance

### Check for Issues

```bash
ryx ::improve analyze
cat ~/ryx-ai/data/improvement_plan.md
```

### Manual Cleanup

```bash
ryx ::clean
```

### Backup

```bash
# Backup configs
cp -r ~/ryx-ai/configs ~/ryx-ai-configs-backup

# Backup database
cp ~/ryx-ai/data/rag_knowledge.db ~/ryx-ai/data/rag_knowledge.db.backup
```

### Reset

```bash
# Remove cache only
rm -rf ~/ryx-ai/data/cache/*

# Remove everything (fresh start)
rm ~/ryx-ai/data/rag_knowledge.db
rm -rf ~/ryx-ai/data/cache/*
rm -rf ~/ryx-ai/data/history/*
```

## Session Mode Commands

```
/quit, /exit, /q    Exit session
/clear              Clear conversation
/exec [num]         Execute commands
/undo               Undo last exchange
/save [file]        Save conversation
/status             Show session stats
/help               Show session help
```

## Exit Codes

```
0    Success
1    General error
2    Permission denied
3    Command not found
4    AI service unavailable
5    Invalid arguments
```

## Environment Variables

```bash
# Set custom Ollama URL
export OLLAMA_HOST=http://custom:11434

# Enable debug mode
export RYX_DEBUG=1

# Custom config dir
export RYX_CONFIG_DIR=/path/to/configs
```

---

## Most Useful Commands (Top 10)

1. `ryx "open X config"` - Open any config file
2. `ryx ::session` - Start interactive mode
3. `ryx ::status` - Check system status
4. `ryx ::help` - Get help
5. `ryx "backup X"` - Backup files
6. `ryx ::browse "topic"` - Research online
7. `ryx ::council "code"` - Code review
8. `ryx ::improve analyze` - Self-check
9. `ryx ::clean` - Cleanup
10. `ryx "find X"` - Find anything

---

**Print this card and keep it handy!**

*Last updated: 2025*