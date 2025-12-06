"""
Ryx AI - Visual Step Indicators

Provides Claude/ChatGPT-style visual feedback showing what the AI is doing.
Shows thinking process, tool execution, and progress indicators.
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn


class StepType(Enum):
    """Types of steps in processing"""
    THINKING = "thinking"
    PARSING = "parsing"
    PLANNING = "planning"
    SEARCHING = "searching"
    SCRAPING = "scraping"
    TOOL_EXECUTION = "tool_execution"
    CODE_GENERATION = "code_generation"
    FILE_OPERATION = "file_operation"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Step:
    """A single step in the processing pipeline"""
    type: StepType
    label: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "running"  # running, complete, error
    details: Optional[str] = None
    substeps: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Duration in seconds"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def emoji(self) -> str:
        """Get emoji for step type"""
        if self.status == "error":
            return "❌"
        elif self.status == "complete":
            return "✅"
        
        emojis = {
            StepType.THINKING: "🤔",
            StepType.PARSING: "📝",
            StepType.PLANNING: "📋",
            StepType.SEARCHING: "🔍",
            StepType.SCRAPING: "🌐",
            StepType.TOOL_EXECUTION: "🛠️",
            StepType.CODE_GENERATION: "💻",
            StepType.FILE_OPERATION: "📂",
            StepType.SYNTHESIS: "🔄",
            StepType.COMPLETE: "✅",
            StepType.ERROR: "❌",
        }
        return emojis.get(self.type, "⚙️")


class StepVisualizer:
    """
    Manages and displays visual step indicators during AI processing.
    Provides real-time feedback like Claude and ChatGPT.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.steps: List[Step] = []
        self.current_step: Optional[Step] = None
        self._live: Optional[Live] = None
        self._enabled = True
    
    def start_step(self, step_type: StepType, label: str, details: Optional[str] = None) -> Step:
        """Start a new step and display it"""
        # Complete previous step if exists
        if self.current_step and self.current_step.status == "running":
            self.complete_step()
        
        step = Step(type=step_type, label=label, details=details)
        self.steps.append(step)
        self.current_step = step
        
        if self._enabled:
            self._display_step(step)
        
        return step
    
    def update_step(self, details: str):
        """Update current step with new details"""
        if self.current_step:
            self.current_step.details = details
            if self._enabled:
                self._display_step(self.current_step)
    
    def add_substep(self, substep: str):
        """Add a substep to current step"""
        if self.current_step:
            self.current_step.substeps.append(substep)
            if self._enabled:
                self._display_step(self.current_step)
    
    def complete_step(self, status: str = "complete"):
        """Mark current step as complete"""
        if self.current_step:
            self.current_step.status = status
            self.current_step.end_time = time.time()
            
            if self._enabled:
                self._display_step_completion(self.current_step)
            
            self.current_step = None
    
    def error_step(self, error_msg: str):
        """Mark current step as error"""
        if self.current_step:
            self.current_step.status = "error"
            self.current_step.details = error_msg
            self.current_step.end_time = time.time()
            
            if self._enabled:
                self._display_step_completion(self.current_step)
            
            self.current_step = None
    
    def _display_step(self, step: Step):
        """Display a step (in progress)"""
        text = Text()
        text.append(f"{step.emoji} ", style="bold")
        text.append(step.label, style="cyan")
        
        if step.details:
            text.append(f": {step.details}", style="dim")
        
        if step.substeps:
            for substep in step.substeps:
                text.append(f"\n  • {substep}", style="dim")
        
        self.console.print(text)
    
    def _display_step_completion(self, step: Step):
        """Display completed step with duration"""
        text = Text()
        text.append(f"{step.emoji} ", style="bold")
        
        if step.status == "complete":
            text.append(step.label, style="green")
        else:
            text.append(step.label, style="red")
        
        duration_ms = int(step.duration * 1000)
        text.append(f" ({duration_ms}ms)", style="dim")
        
        if step.details and step.status == "error":
            text.append(f"\n  {step.details}", style="red dim")
        
        self.console.print(text)
    
    def get_summary(self) -> str:
        """Get summary of all steps"""
        total_duration = sum(s.duration for s in self.steps)
        complete = sum(1 for s in self.steps if s.status == "complete")
        errors = sum(1 for s in self.steps if s.status == "error")
        
        return f"{complete} steps completed, {errors} errors, {total_duration:.2f}s total"
    
    def enable(self):
        """Enable visual output"""
        self._enabled = True
    
    def disable(self):
        """Disable visual output (silent mode)"""
        self._enabled = False


class StreamingDisplay:
    """
    Handles streaming token display with statistics.
    Shows tokens as they arrive with live stats like ChatGPT.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.token_count = 0
        self.start_time: Optional[float] = None
        self.accumulated_text = []
        self._live: Optional[Live] = None
    
    def start(self):
        """Start streaming display"""
        self.token_count = 0
        self.start_time = time.time()
        self.accumulated_text = []
        self.console.print()  # Add newline before stream
    
    def add_token(self, token: str) -> None:
        """Add a token to the display"""
        self.token_count += 1
        self.accumulated_text.append(token)
        
        # Print token immediately for real-time streaming
        self.console.print(token, end="")
    
    def finish(self) -> Dict[str, Any]:
        """Finish streaming and show stats"""
        if self.start_time:
            duration = time.time() - self.start_time
            tokens_per_sec = self.token_count / duration if duration > 0 else 0
            
            # Add newline after content
            self.console.print()
            
            # Show stats in dim text
            stats = Text()
            stats.append(f"└─ {self.token_count} tokens", style="dim")
            stats.append(f" • {tokens_per_sec:.1f} tok/s", style="dim")
            stats.append(f" • {duration:.2f}s", style="dim")
            self.console.print(stats)
            
            return {
                "tokens": self.token_count,
                "duration": duration,
                "tokens_per_sec": tokens_per_sec,
                "text": "".join(self.accumulated_text)
            }
        return {}


def create_thinking_spinner(console: Console, message: str = "Thinking...") -> Live:
    """Create a live spinner for thinking indicator"""
    spinner = Spinner("dots", text=Text(message, style="cyan"))
    return Live(spinner, console=console, refresh_per_second=10)


def show_tool_execution(console: Console, tool: str, params: Dict[str, Any]):
    """Show tool execution with parameters"""
    text = Text()
    text.append("🛠️  ", style="bold")
    text.append(f"Using {tool}", style="cyan")
    
    if params:
        text.append(" with ", style="dim")
        param_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3])
        text.append(param_str, style="yellow")
    
    console.print(text)


def show_search_progress(console: Console, query: str, sources: int = 0):
    """Show web search progress"""
    text = Text()
    text.append("🔍 ", style="bold")
    text.append(f"Searching: {query}", style="cyan")
    
    if sources > 0:
        text.append(f" ({sources} sources found)", style="dim")
    
    console.print(text)
