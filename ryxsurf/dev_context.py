#!/usr/bin/env python3
"""
Ryx Self-Prompting for RyxSurf Development

This module helps Ryx maintain context when coding RyxSurf.
It provides:
- Codebase summaries
- File context loading
- Task tracking
- Self-correction patterns
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


RYXSURF_ROOT = Path(__file__).parent


@dataclass
class FileContext:
    """Context about a file for the AI"""
    path: str
    purpose: str
    key_classes: List[str] = field(default_factory=list)
    key_functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    line_count: int = 0


# File purposes for context
FILE_PURPOSES = {
    "main.py": "Entry point - starts the browser",
    "keybinds.py": "All keybind definitions and categories",
    "src/core/browser.py": "Main Browser class with WebKitGTK integration",
    "src/core/memory.py": "Tab memory manager - unloads inactive tabs",
    "src/core/config.py": "Configuration loading",
    "src/ai/agent.py": "AI browser control agent - processes commands",
    "src/ai/vision.py": "Page analysis and understanding",
    "src/ai/actions.py": "JavaScript action generators",
    "src/ui/bar.py": "URL/command input overlay",
    "src/ui/tabs.py": "Tab sidebar component",
    "src/ui/hints.py": "Keyboard hint mode (vimium-style)",
    "src/sessions/manager.py": "Session save/load/switch",
    "src/extensions/loader.py": "Firefox extension support",
}


def get_file_context(filepath: str) -> Optional[FileContext]:
    """Get context about a specific file"""
    full_path = RYXSURF_ROOT / filepath
    
    if not full_path.exists():
        return None
        
    content = full_path.read_text()
    lines = content.split('\n')
    
    # Extract key info
    imports = [l for l in lines if l.startswith('import ') or l.startswith('from ')]
    classes = [l.split('class ')[1].split('(')[0].split(':')[0] 
               for l in lines if l.startswith('class ')]
    functions = [l.split('def ')[1].split('(')[0] 
                 for l in lines if l.strip().startswith('def ') and not l.strip().startswith('def _')]
    
    return FileContext(
        path=filepath,
        purpose=FILE_PURPOSES.get(filepath, ""),
        key_classes=classes[:10],
        key_functions=functions[:15],
        imports=imports[:10],
        line_count=len(lines)
    )


def get_codebase_summary() -> str:
    """Get a summary of the RyxSurf codebase for AI context"""
    summary = ["# RyxSurf Codebase Summary\n"]
    
    for filepath, purpose in FILE_PURPOSES.items():
        ctx = get_file_context(filepath)
        if ctx:
            summary.append(f"## {filepath}")
            summary.append(f"Purpose: {purpose}")
            summary.append(f"Lines: {ctx.line_count}")
            if ctx.key_classes:
                summary.append(f"Classes: {', '.join(ctx.key_classes)}")
            if ctx.key_functions:
                summary.append(f"Functions: {', '.join(ctx.key_functions[:8])}")
            summary.append("")
            
    return "\n".join(summary)


def get_task_context(task: str) -> str:
    """Get relevant file context for a specific task"""
    task_lower = task.lower()
    
    relevant_files = []
    
    # Map keywords to relevant files
    if any(k in task_lower for k in ['keybind', 'keyboard', 'shortcut', 'key']):
        relevant_files.extend(['keybinds.py', 'src/core/browser.py'])
        
    if any(k in task_lower for k in ['ai', 'summarize', 'dismiss', 'popup', 'command']):
        relevant_files.extend(['src/ai/agent.py', 'src/ai/vision.py', 'src/ai/actions.py'])
        
    if any(k in task_lower for k in ['tab', 'session', 'group']):
        relevant_files.extend(['src/sessions/manager.py', 'src/ui/tabs.py', 'src/core/memory.py'])
        
    if any(k in task_lower for k in ['ui', 'sidebar', 'bar', 'url', 'input']):
        relevant_files.extend(['src/ui/bar.py', 'src/ui/tabs.py', 'src/ui/hints.py'])
        
    if any(k in task_lower for k in ['extension', 'addon', 'firefox']):
        relevant_files.extend(['src/extensions/loader.py'])
        
    if any(k in task_lower for k in ['hint', 'click', 'vimium', 'link']):
        relevant_files.extend(['src/ui/hints.py', 'src/ai/actions.py'])
        
    # Always include browser.py for context
    if 'src/core/browser.py' not in relevant_files:
        relevant_files.append('src/core/browser.py')
        
    # Build context
    context_parts = [f"# Task: {task}\n", "## Relevant Files:\n"]
    
    for filepath in relevant_files:
        ctx = get_file_context(filepath)
        if ctx:
            full_path = RYXSURF_ROOT / filepath
            content = full_path.read_text()
            
            # Truncate if too long
            if len(content) > 3000:
                content = content[:3000] + "\n... (truncated)"
                
            context_parts.append(f"### {filepath}")
            context_parts.append(f"Purpose: {ctx.purpose}")
            context_parts.append("```python")
            context_parts.append(content)
            context_parts.append("```\n")
            
    return "\n".join(context_parts)


# Common issues and fixes for self-correction
SELF_CORRECTION_PATTERNS = {
    "gtk version": {
        "issue": "Using GTK3 instead of GTK4",
        "fix": "Replace Gtk.main() with app.run(), use Gtk.Application pattern"
    },
    "webkit version": {
        "issue": "Using WebKit2 (GTK3) instead of WebKit 6.0",
        "fix": "Use gi.require_version('WebKit', '6.0') and update API calls"
    },
    "async in gtk": {
        "issue": "Blocking async in GTK main thread",
        "fix": "Use GLib.idle_add() or asyncio integration"
    },
    "signal connection": {
        "issue": "GTK4 signal connection syntax",
        "fix": "Use widget.connect('signal-name', callback) pattern"
    },
}


def get_self_correction_hints() -> str:
    """Get common issues and fixes"""
    hints = ["# Common Issues & Fixes\n"]
    
    for pattern, info in SELF_CORRECTION_PATTERNS.items():
        hints.append(f"## {pattern}")
        hints.append(f"Issue: {info['issue']}")
        hints.append(f"Fix: {info['fix']}\n")
        
    return "\n".join(hints)


if __name__ == "__main__":
    # Print codebase summary for testing
    print(get_codebase_summary())
