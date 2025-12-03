# -*- coding: utf-8 -*-
"""
File Watcher - Watch mode für automatische Reaktion auf Dateiänderungen
Inspiriert von Aider's watch.py
"""

import re
import threading
import asyncio
from pathlib import Path
from typing import Optional, Callable, List, Set
from dataclasses import dataclass, field
import logging
import fnmatch
import time

logger = logging.getLogger(__name__)


@dataclass
class WatchConfig:
    """Konfiguration für File Watcher"""
    watch_patterns: List[str] = field(default_factory=lambda: ["*.py", "*.ts", "*.js", "*.go"])
    ignore_patterns: List[str] = field(default_factory=lambda: [
        ".git/*", "__pycache__/*", "*.pyc", "node_modules/*",
        ".venv/*", "venv/*", "*.swp", "*.swo", "*~", "*.bak",
        ".aider*", ".ryx*", "*.log", ".cache/*"
    ])
    debounce_seconds: float = 1.0  # Verzögerung bevor Reaktion
    ai_comment_enabled: bool = True  # Reagiere auf "# AI: ..." Kommentare


@dataclass
class FileChange:
    """Beschreibt eine Dateiänderung"""
    path: Path
    change_type: str  # "modified", "created", "deleted"
    timestamp: float
    ai_comment: Optional[str] = None  # Enthaltener AI-Kommentar


class FileWatcher:
    """
    Überwacht Dateien auf Änderungen für Watch-Mode
    
    Features:
    - Überwacht Dateien basierend auf Patterns
    - Erkennt AI-Kommentare (# AI: ..., // AI: ...)
    - Debouncing um doppelte Events zu vermeiden
    - Async-kompatibel
    
    Usage:
        watcher = FileWatcher("/path/to/repo")
        watcher.on_change(handle_change)
        await watcher.start()
        
        # ... watcher läuft im Hintergrund
        
        watcher.stop()
    """
    
    # Regex für AI-Kommentare
    AI_COMMENT_PATTERNS = [
        re.compile(r"#\s*AI[:\s](.+)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"//\s*AI[:\s](.+)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"--\s*AI[:\s](.+)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"/\*\s*AI[:\s](.+?)\*/", re.IGNORECASE | re.DOTALL),
    ]
    
    def __init__(self, root: str, config: Optional[WatchConfig] = None):
        self.root = Path(root).resolve()
        self.config = config or WatchConfig()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[FileChange], None]] = []
        self._last_changes: dict = {}  # path -> timestamp für debouncing
        self._file_hashes: dict = {}  # path -> hash für echte Änderungen
        
    def on_change(self, callback: Callable[[FileChange], None]):
        """Registriere Callback für Dateiänderungen"""
        self._callbacks.append(callback)
        
    async def start(self):
        """Starte Überwachung"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"FileWatcher started for {self.root}")
        
    def stop(self):
        """Stoppe Überwachung"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("FileWatcher stopped")
        
    def _watch_loop(self):
        """Haupt-Überwachungsloop"""
        try:
            # Versuche watchfiles zu nutzen (schneller)
            self._watch_with_watchfiles()
        except ImportError:
            logger.info("watchfiles not installed, using polling")
            self._watch_with_polling()
        except Exception as e:
            logger.error(f"Watch error: {e}")
            self._watch_with_polling()
            
    def _watch_with_watchfiles(self):
        """Überwachung mit watchfiles Library"""
        from watchfiles import watch, Change
        
        for changes in watch(
            self.root,
            stop_event=threading.Event() if not self._running else None,
            recursive=True
        ):
            if not self._running:
                break
                
            for change_type, path_str in changes:
                path = Path(path_str)
                
                if not self._should_watch(path):
                    continue
                    
                # Debouncing
                now = time.time()
                last = self._last_changes.get(str(path), 0)
                if now - last < self.config.debounce_seconds:
                    continue
                self._last_changes[str(path)] = now
                
                # Erstelle FileChange
                change = FileChange(
                    path=path,
                    change_type=self._map_change_type(change_type),
                    timestamp=now
                )
                
                # Prüfe auf AI-Kommentare
                if self.config.ai_comment_enabled and path.exists():
                    change.ai_comment = self._extract_ai_comment(path)
                    
                self._trigger_callbacks(change)
                
    def _watch_with_polling(self):
        """Fallback: Polling-basierte Überwachung"""
        # Initialer Scan
        self._scan_files()
        
        while self._running:
            time.sleep(1.0)  # Poll every second
            
            for file_path in self._get_watchable_files():
                try:
                    stat = file_path.stat()
                    mtime = stat.st_mtime
                    
                    old_mtime = self._file_hashes.get(str(file_path))
                    
                    if old_mtime is None:
                        # Neue Datei
                        self._file_hashes[str(file_path)] = mtime
                        change = FileChange(
                            path=file_path,
                            change_type="created",
                            timestamp=time.time()
                        )
                        if self.config.ai_comment_enabled:
                            change.ai_comment = self._extract_ai_comment(file_path)
                        self._trigger_callbacks(change)
                        
                    elif mtime > old_mtime:
                        # Geänderte Datei
                        self._file_hashes[str(file_path)] = mtime
                        change = FileChange(
                            path=file_path,
                            change_type="modified",
                            timestamp=time.time()
                        )
                        if self.config.ai_comment_enabled:
                            change.ai_comment = self._extract_ai_comment(file_path)
                        self._trigger_callbacks(change)
                        
                except FileNotFoundError:
                    # Gelöschte Datei
                    if str(file_path) in self._file_hashes:
                        del self._file_hashes[str(file_path)]
                        change = FileChange(
                            path=file_path,
                            change_type="deleted",
                            timestamp=time.time()
                        )
                        self._trigger_callbacks(change)
                        
    def _scan_files(self):
        """Initialer Scan aller Dateien"""
        for file_path in self._get_watchable_files():
            try:
                self._file_hashes[str(file_path)] = file_path.stat().st_mtime
            except FileNotFoundError:
                pass
                
    def _get_watchable_files(self) -> List[Path]:
        """Liste aller zu überwachenden Dateien"""
        files = []
        for pattern in self.config.watch_patterns:
            files.extend(self.root.rglob(pattern))
        return [f for f in files if self._should_watch(f)]
        
    def _should_watch(self, path: Path) -> bool:
        """Prüfe ob Datei überwacht werden soll"""
        try:
            rel_path = path.relative_to(self.root)
        except ValueError:
            return False
            
        rel_str = str(rel_path)
        
        # Check ignore patterns
        for pattern in self.config.ignore_patterns:
            if fnmatch.fnmatch(rel_str, pattern):
                return False
                
        # Check watch patterns
        for pattern in self.config.watch_patterns:
            if fnmatch.fnmatch(rel_str, pattern):
                return True
                
        return False
        
    def _map_change_type(self, change) -> str:
        """Mappe watchfiles Change zu String"""
        try:
            from watchfiles import Change
            mapping = {
                Change.added: "created",
                Change.modified: "modified",
                Change.deleted: "deleted"
            }
            return mapping.get(change, "modified")
        except ImportError:
            return "modified"
            
    def _extract_ai_comment(self, path: Path) -> Optional[str]:
        """Extrahiere AI-Kommentar aus Datei"""
        try:
            content = path.read_text(errors='ignore')
            
            for pattern in self.AI_COMMENT_PATTERNS:
                match = pattern.search(content)
                if match:
                    return match.group(1).strip()
                    
        except Exception as e:
            logger.debug(f"Error reading file {path}: {e}")
            
        return None
        
    def _trigger_callbacks(self, change: FileChange):
        """Rufe alle Callbacks auf"""
        for callback in self._callbacks:
            try:
                callback(change)
            except Exception as e:
                logger.error(f"Callback error: {e}")
                
    def get_watched_files(self) -> List[Path]:
        """Liste aktuell überwachter Dateien"""
        return list(self._file_hashes.keys())


class WatchModeHandler:
    """
    Handler für Watch-Mode Integration mit Ryx Brain
    
    Verarbeitet Dateiänderungen und AI-Kommentare,
    sendet sie an Ryx zur Bearbeitung.
    """
    
    def __init__(self, brain, root: str):
        self.brain = brain
        self.root = Path(root)
        self.watcher = FileWatcher(root)
        self.watcher.on_change(self._handle_change)
        self._pending_changes: List[FileChange] = []
        
    async def start(self):
        """Starte Watch Mode"""
        await self.watcher.start()
        logger.info("Watch mode active. Edit files or add AI comments to trigger actions.")
        
    def stop(self):
        """Stoppe Watch Mode"""
        self.watcher.stop()
        
    def _handle_change(self, change: FileChange):
        """Handle Dateiänderung"""
        logger.debug(f"File changed: {change.path} ({change.change_type})")
        
        # Bei AI-Kommentar: Sofort verarbeiten
        if change.ai_comment:
            logger.info(f"AI comment detected: {change.ai_comment}")
            self._process_ai_comment(change)
        else:
            # Normale Änderung: Sammeln
            self._pending_changes.append(change)
            
    def _process_ai_comment(self, change: FileChange):
        """Verarbeite AI-Kommentar"""
        asyncio.create_task(self._async_process(change))
        
    async def _async_process(self, change: FileChange):
        """Async Verarbeitung"""
        try:
            context = f"File: {change.path}\nComment: {change.ai_comment}"
            # Sende an Brain zur Verarbeitung
            if hasattr(self.brain, 'process'):
                await self.brain.process(change.ai_comment, context=context)
        except Exception as e:
            logger.error(f"Error processing AI comment: {e}")
