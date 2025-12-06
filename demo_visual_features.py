#!/usr/bin/env python3
"""
Demo script showcasing RYX AI's new visual features.
This demonstrates the improvements without requiring vLLM to be running.
"""

import sys
import time
import asyncio
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.visual_steps import StepVisualizer, StepType, StreamingDisplay
from core.cli_ui import CLI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def demo_intro():
    """Show introduction"""
    console = Console()
    
    title = Text("RYX AI - New Visual Features Demo", style="bold cyan")
    subtitle = Text("Claude/ChatGPT-style process visualization", style="dim")
    
    content = Text()
    content.append("This demo showcases:\n\n", style="white")
    content.append("🤔 ", style="bold")
    content.append("Real-time thinking indicators\n")
    content.append("🔍 ", style="bold")
    content.append("Search progress visualization\n")
    content.append("🛠️  ", style="bold")
    content.append("Tool execution feedback\n")
    content.append("💬 ", style="bold")
    content.append("Token-by-token streaming\n")
    content.append("🏛️  ", style="bold")
    content.append("Multi-model council voting\n")
    
    panel = Panel(content, title=title, subtitle=subtitle, border_style="cyan")
    console.print("\n")
    console.print(panel)
    console.print("\n")
    
    time.sleep(2)


def demo_query_processing():
    """Demonstrate a typical query processing flow"""
    console = Console()
    cli = CLI()
    
    console.print("\n" + "─"*60, style="dim")
    console.print("SCENARIO 1: User Query Processing", style="bold yellow")
    console.print("─"*60 + "\n", style="dim")
    
    console.print(Text("User: ", style="bold purple") + Text("explain quantum computing", style="purple"))
    console.print()
    
    # Show the processing steps
    cli.thinking("Processing request...")
    time.sleep(0.5)
    
    cli.parsing("Analyzing query structure...")
    time.sleep(0.4)
    
    cli.planning("Plan: search web → synthesize explanation")
    time.sleep(0.3)
    
    cli.searching("quantum computing")
    time.sleep(0.6)
    cli.searching("quantum computing", 7)
    time.sleep(0.2)
    
    cli.synthesizing("Generating response...")
    time.sleep(0.5)
    
    # Simulate streaming response
    response_text = "Quantum computing is a revolutionary approach to computation that leverages quantum mechanics principles. Unlike classical computers that use bits (0 or 1), quantum computers use qubits which can exist in superposition."
    
    cli.stream_start("qwen2.5-7b")
    words = response_text.split()
    for word in words:
        cli.stream_token(word + " ")
        time.sleep(0.04)
    cli.stream_end()
    
    console.print()


def demo_code_review():
    """Demonstrate council code review"""
    console = Console()
    
    console.print("\n" + "─"*60, style="dim")
    console.print("SCENARIO 2: Council Code Review", style="bold yellow")
    console.print("─"*60 + "\n", style="dim")
    
    # Show sample code
    code = """\
def calculate_factorial(n):
    if n < 0:
        return None
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result\
"""
    
    console.print(Text("User: ", style="bold purple") + Text("/review <code>", style="purple"))
    console.print()
    
    from rich.syntax import Syntax
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Code to Review", border_style="blue"))
    console.print()
    
    # Show council processing
    console.print(Text("🏛️  ", style="bold") + Text("Council Session (3 members)", style="bold cyan"))
    console.print()
    
    time.sleep(0.5)
    
    # Simulate concurrent queries
    models = ["Coder", "General", "Fast"]
    for model in models:
        time.sleep(0.3)
        console.print(f"  ✓ {model}: analyzing...", style="dim")
    
    console.print()
    time.sleep(0.5)
    
    # Show results table
    from rich.table import Table
    
    table = Table(title="📊 Council Responses", show_header=True, header_style="bold cyan")
    table.add_column("Member", style="cyan")
    table.add_column("Rating", justify="center")
    table.add_column("Key Feedback", max_width=40)
    table.add_column("Time", justify="right", style="dim")
    
    table.add_row(
        "Coder",
        "7.5/10",
        "Good structure, but missing error handling for negative inputs",
        "850ms"
    )
    table.add_row(
        "General",
        "8.0/10",
        "Clear and readable. Consider adding type hints",
        "620ms"
    )
    table.add_row(
        "Fast",
        "7.0/10",
        "Works correctly, could use docstring",
        "420ms"
    )
    
    console.print(table)
    console.print()
    
    summary = Text()
    summary.append("└─ ", style="dim")
    summary.append("Avg: 7.5/10", style="yellow")
    summary.append(" • ", style="dim")
    summary.append("Agreement: 82%", style="cyan")
    summary.append(" • ", style="dim")
    summary.append("1.89s", style="dim")
    
    console.print(summary)
    console.print()


def demo_step_visualizer():
    """Demonstrate the StepVisualizer in action"""
    console = Console()
    
    console.print("\n" + "─"*60, style="dim")
    console.print("SCENARIO 3: Complex Multi-Step Task", style="bold yellow")
    console.print("─"*60 + "\n", style="dim")
    
    console.print(Text("User: ", style="bold purple") + Text("create a REST API for user management", style="purple"))
    console.print()
    
    viz = StepVisualizer(console)
    
    # Planning phase
    viz.start_step(StepType.PLANNING, "Analyzing requirements")
    time.sleep(0.5)
    viz.add_substep("Identified entities: User, Auth")
    time.sleep(0.3)
    viz.add_substep("Endpoints needed: CRUD + login")
    time.sleep(0.2)
    viz.complete_step()
    
    # Code generation
    viz.start_step(StepType.CODE_GENERATION, "Generating API structure")
    time.sleep(0.6)
    viz.update_step("Creating FastAPI application...")
    time.sleep(0.4)
    viz.add_substep("models.py - User model with SQLAlchemy")
    time.sleep(0.3)
    viz.add_substep("routes.py - CRUD endpoints")
    time.sleep(0.3)
    viz.add_substep("auth.py - JWT authentication")
    time.sleep(0.2)
    viz.complete_step()
    
    # File operations
    viz.start_step(StepType.FILE_OPERATION, "Writing files")
    time.sleep(0.4)
    viz.add_substep("Created: api/models.py")
    time.sleep(0.2)
    viz.add_substep("Created: api/routes.py")
    time.sleep(0.2)
    viz.add_substep("Created: api/auth.py")
    time.sleep(0.2)
    viz.add_substep("Created: requirements.txt")
    time.sleep(0.2)
    viz.complete_step()
    
    console.print()
    console.print(Text("✅ ", style="bold green") + Text("Task completed!", style="green"))
    console.print(f"   {viz.get_summary()}", style="dim")
    console.print()


def demo_streaming_comparison():
    """Compare old vs new streaming"""
    console = Console()
    
    console.print("\n" + "─"*60, style="dim")
    console.print("SCENARIO 4: Streaming Comparison", style="bold yellow")
    console.print("─"*60 + "\n", style="dim")
    
    sample_text = "The key to understanding recursion is to understand that each recursive call creates a new scope with its own local variables, and the function waits for the recursive call to return before continuing."
    
    # Old way (simulated)
    console.print(Text("❌ Old: Buffered response (no streaming)", style="bold red"))
    console.print()
    time.sleep(1.5)  # Simulate waiting
    console.print(sample_text, style="green")
    console.print()
    time.sleep(1)
    
    # New way
    console.print(Text("✅ New: Real-time token streaming", style="bold green"))
    console.print()
    
    display = StreamingDisplay(console)
    display.start()
    
    words = sample_text.split()
    for word in words:
        display.add_token(word + " ")
        time.sleep(0.06)
    
    stats = display.finish()
    console.print()
    
    # Show comparison
    comparison = Text()
    comparison.append("Benefits: ", style="bold")
    comparison.append("Immediate feedback", style="cyan")
    comparison.append(" • ", style="dim")
    comparison.append("Shows progress", style="cyan")
    comparison.append(" • ", style="dim")
    comparison.append("Interruptible", style="cyan")
    comparison.append(" • ", style="dim")
    comparison.append("Token stats", style="cyan")
    
    console.print(comparison)
    console.print()


def demo_outro():
    """Show conclusion"""
    console = Console()
    
    console.print("\n" + "─"*60, style="dim")
    console.print("Summary", style="bold yellow")
    console.print("─"*60 + "\n", style="dim")
    
    features = [
        ("🤔 Thinking Indicators", "Shows AI's processing state"),
        ("🔍 Search Progress", "Real-time web search feedback"),
        ("💬 Token Streaming", "See responses as they generate"),
        ("🏛️  Multi-Model Council", "Get consensus from multiple AIs"),
        ("📊 Performance Stats", "Tokens/s, latency, accuracy"),
        ("🎨 Rich Visualizations", "Tables, panels, syntax highlighting"),
    ]
    
    for emoji_title, desc in features:
        text = Text()
        text.append(f"{emoji_title}", style="bold cyan")
        text.append(f" - {desc}", style="dim")
        console.print(text)
    
    console.print()
    
    next_steps = Panel(
        Text.from_markup(
            "[bold cyan]Try it yourself![/]\n\n"
            "1. [yellow]Start vLLM:[/] ryx start vllm\n"
            "2. [yellow]Run session:[/] ryx\n"
            "3. [yellow]Try commands:[/]\n"
            "   • explain recursion\n"
            "   • /council What is the meaning of life?\n"
            "   • /review @mycode.py\n"
        ),
        title="Next Steps",
        border_style="green"
    )
    
    console.print(next_steps)
    console.print()


def main():
    """Run the complete demo"""
    try:
        demo_intro()
        demo_query_processing()
        demo_code_review()
        demo_step_visualizer()
        demo_streaming_comparison()
        demo_outro()
        
    except KeyboardInterrupt:
        console = Console()
        console.print("\n\n[yellow]Demo interrupted by user[/]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n\n[red]Demo error: {e}[/]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
