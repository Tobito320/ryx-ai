# Ryx AI - Quick Start Guide

## ✅ Basic Setup Complete!

All critical issues have been fixed:
- ✅ Database permission errors resolved
- ✅ Natural language interface working
- ✅ Ollama conflict handling added
- ✅ Help menu clarified

## 🚀 Test Your Installation

### 1. Test Basic Query

```bash
ryx "hello"
```

**Expected:** AI responds with a greeting.

If you see database errors, run:
```bash
chmod -R 777 ~/ryx-ai/data ~/ryx-ai/logs
```

### 2. Test Natural Language

```bash
ryx "what is my username?"
ryx "what's the date today?"
ryx "show me disk usage"
```

**Expected:** AI interprets your request and provides an answer.

### 3. Test Help Menu

```bash
ryx ::help
```

**Expected:** Shows help with natural language examples like:
- `ryx "open my hyprland config"`
- `ryx "find waybar themes"`

### 4. Check System Status

```bash
ryx ::status
```

**Expected:** Shows system status, databases, metrics.

### 5. Test Ollama Handling

If Ollama is not running or is busy:

```bash
ryx "test query"
```

**Expected:** Helpful error message like:
```
❌ Cannot connect to Ollama service

Possible fixes:
  1. Start Ollama: ollama serve
  2. Check if another application is using Ollama
  3. Wait if Ollama is busy with another request
```

## 📝 How to Use Ryx

### Natural Language Prompts

Ryx understands natural language. Just describe what you want:

```bash
# Ask questions
ryx "how do I reload hyprland?"
ryx "what's using my CPU?"
ryx "find large files in my home directory"

# Request actions
ryx "open my hyprland config"
ryx "edit waybar config in new terminal"
ryx "show me my keybinds"

# Get help
ryx "help me fix my wifi"
ryx "what's taking up disk space?"
ryx "how do I change my wallpaper?"
```

### Session Mode (Interactive)

For back-and-forth conversations:

```bash
ryx ::session
```

Then have a conversation:
```
You: show me my hyprland keybinds
Ryx: [shows keybinds]
You: add a keybind for opening firefox
Ryx: [suggests command]
```

Press `Ctrl+C` to save and exit. Resume with `ryx ::resume`.

## ⚠️ Common Issues

### "unable to open database file"

**Fix:**
```bash
chmod -R 777 ~/ryx-ai/data ~/ryx-ai/logs
```

### "Cannot connect to Ollama"

**Fixes:**
1. Start Ollama: `ollama serve`
2. If another app is using Ollama, wait for it to finish
3. Check Ollama status: `ps aux | grep ollama`

### Permission denied on /usr/local/bin/ryx

**Fix:**
```bash
sudo chmod +x ~/ryx-ai/ryx
sudo ln -sf ~/ryx-ai/ryx /usr/local/bin/ryx
```

## 🎯 Next Steps

Once basic functionality works:

1. **Download a model** (if not already done):
   ```bash
   ollama pull qwen2.5:1.5b
   ```

2. **Test file finding:**
   ```bash
   ryx "find my hyprland config"
   ryx "open my waybar config"
   ```

3. **Try the interactive session:**
   ```bash
   ryx ::session
   ```

4. **Check system health:**
   ```bash
   ryx ::health
   ryx ::metrics
   ```

## 📊 Verify Everything Works

Run all basic checks:

```bash
# 1. Basic query
ryx "hello"

# 2. System command
ryx ::help

# 3. Status check
ryx ::status

# 4. Natural language
ryx "what's the current time?"
```

If all 4 work, **Ryx is ready to use!** 🎉

## 🆘 Still Having Issues?

Check the diagnostics:
```bash
python scripts/system_diagnostics.py
```

This will show exactly what's wrong and how to fix it.

---

**Remember:**
- Use **quotes** for natural language: `ryx "open my config"`
- Use **::commands** for system: `ryx ::help`, `ryx ::status`
- Use **::session** for interactive mode
