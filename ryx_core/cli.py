"""
RYX AI CLI - Modern Command Line Interface

Built with Typer for a beautiful, intuitive CLI experience.
"""

import typer
from typing import Optional
from enum import Enum
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="ryx",
    help="🟣 Ryx AI - Intelligent Local AI Agent for your terminal",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False,
)


class SafetyMode(str, Enum):
    strict = "strict"
    normal = "normal"
    loose = "loose"


class ModelTierEnum(str, Enum):
    fast = "fast"
    balanced = "balanced"
    powerful = "powerful"
    ultra = "ultra"
    uncensored = "uncensored"


@app.command("chat")
def chat_cmd(
    prompt: Optional[str] = typer.Argument(
        None,
        help="Natural language prompt to execute",
    ),
    tier: ModelTierEnum = typer.Option(
        ModelTierEnum.balanced,
        "--tier", "-t",
        help="Model tier to use",
    ),
    safety: SafetyMode = typer.Option(
        SafetyMode.normal,
        "--safety", "-s",
        help="Safety mode for command execution",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream response output",
    ),
):
    """
    💬 Chat with Ryx AI using natural language.
    
    If no prompt is provided, starts an interactive session.
    
    Examples:
        ryx chat "find my notes about Python"
        ryx chat "open hyprland config" --tier fast
        ryx chat "refactor this function" --tier powerful
    """
    if prompt is None:
        _start_session(safety_mode=safety.value, tier=tier.value)
    else:
        _handle_prompt(prompt, tier=tier.value, safety_mode=safety.value, stream=stream)


@app.command("session")
def session_cmd(
    safety: SafetyMode = typer.Option(
        SafetyMode.normal,
        "--safety", "-s",
        help="Safety mode for command execution",
    ),
    tier: ModelTierEnum = typer.Option(
        ModelTierEnum.balanced,
        "--tier", "-t",
        help="Default model tier",
    ),
):
    """
    🔄 Start an interactive chat session.
    
    Use Ctrl+C to pause and save state.
    Use Ctrl+D to exit.
    """
    _start_session(safety_mode=safety.value, tier=tier.value)


@app.command("status")
def status_cmd():
    """
    📊 Show system status and health.
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    # Build status table
    table = Table(title="🟣 Ryx AI Status", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    # Check vLLM (primary LLM backend)
    try:
        import requests
        resp = requests.get("http://localhost:8001/v1/models", timeout=2)
        if resp.ok:
            models = resp.json().get("data", [])
            model_name = models[0].get("id", "unknown").split('/')[-1] if models else "none"
            table.add_row("vLLM", "✅ Running", f"Model: {model_name}")
        else:
            table.add_row("vLLM", "⚠️ Degraded", "API not responding properly")
    except Exception:
        table.add_row("vLLM", "❌ Offline", "Not reachable at localhost:8001")
    
    # Check data directories
    data_dir = PROJECT_ROOT / "data"
    if data_dir.exists():
        table.add_row("Data Directory", "✅ Available", str(data_dir))
    else:
        table.add_row("Data Directory", "⚠️ Missing", "Will be created on first use")
    
    # Check configs
    config_dir = PROJECT_ROOT / "configs"
    if config_dir.exists():
        table.add_row("Config Directory", "✅ Available", str(config_dir))
    else:
        table.add_row("Config Directory", "❌ Missing", "Required configs not found")
    
    console.print()
    console.print(table)
    console.print()


@app.command("models")
def models_cmd():
    """
    🤖 List available AI models.
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    table = Table(title="Available Models", show_header=True)
    table.add_column("Model", style="cyan")
    table.add_column("Size", style="yellow")
    table.add_column("Modified", style="dim")
    
    try:
        import requests
        resp = requests.get("http://localhost:8001/v1/models", timeout=5)
        if resp.ok:
            models_data = resp.json().get("data", [])
            for model in models_data:
                name = model.get("id", "unknown")
                table.add_row(name, "-", "-")
            
            if not models_data:
                console.print("[yellow]No models available[/yellow]")
                console.print("[dim]Install with: vllm serve <model>[/dim]")
        else:
            console.print("[red]Failed to fetch models[/red]")
    except Exception as e:
        console.print(f"[red]Error connecting to vLLM: {e}[/red]")
        console.print("[dim]Make sure vLLM is running: vllm serve[/dim]")
        return
    
    console.print()
    console.print(table)
    console.print()


@app.command("workflow")
def workflow_cmd(
    name: str = typer.Argument(
        ...,
        help="Workflow name or description",
    ),
    visualize: bool = typer.Option(
        False,
        "--visualize", "-v",
        help="Show workflow visualization",
    ),
):
    """
    🔀 Run or view a workflow.
    
    Workflows are multi-step AI operations shown with N8N-style visualization.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.tree import Tree
    
    console = Console()
    
    if visualize:
        # Show workflow structure
        tree = Tree(f"🔀 Workflow: {name}")
        tree.add("📥 Input: User Prompt")
        tree.add("🔄 Router: Model Selection").add("qwen2.5-coder:14b")
        tree.add("⚙️ Execute: Tool Chain")
        tree.add("📤 Output: Response")
        
        console.print()
        console.print(Panel(tree, title="Workflow Visualization"))
        console.print()
    else:
        console.print(f"[cyan]Running workflow:[/cyan] {name}")
        console.print("[dim]Use --visualize to see workflow structure[/dim]")


@app.command("config")
def config_cmd(
    show: bool = typer.Option(
        False,
        "--show",
        help="Show current configuration",
    ),
    edit: bool = typer.Option(
        False,
        "--edit",
        help="Open config in editor",
    ),
):
    """
    ⚙️ View or edit Ryx configuration.
    """
    from rich.console import Console
    from rich.syntax import Syntax
    import json
    
    console = Console()
    config_file = PROJECT_ROOT / "configs" / "settings.json"
    
    if edit:
        import subprocess
        editor = "nvim" if Path("/usr/bin/nvim").exists() else "vim"
        subprocess.run([editor, str(config_file)])
    elif show or True:  # Default to show
        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)
            syntax = Syntax(
                json.dumps(config_data, indent=2),
                "json",
                theme="monokai",
                line_numbers=True,
            )
            console.print()
            console.print(syntax)
            console.print()
        else:
            console.print("[yellow]Config file not found[/yellow]")


@app.command("clean")
def clean_cmd(
    aggressive: bool = typer.Option(
        False,
        "--aggressive",
        help="Aggressive cleanup (removes more data)",
    ),
):
    """
    🧹 Clean up cache and temporary files.
    """
    from rich.console import Console
    from rich.progress import Progress
    
    console = Console()
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Cleaning up...", total=100)
        
        # Clean cache
        cache_dir = PROJECT_ROOT / "data" / "cache"
        if cache_dir.exists():
            for f in cache_dir.iterdir():
                if f.is_file():
                    f.unlink()
            progress.update(task, advance=50)
        
        # Clean logs if aggressive
        if aggressive:
            logs_dir = PROJECT_ROOT / "data" / "logs"
            if logs_dir.exists():
                for f in logs_dir.iterdir():
                    if f.suffix == ".log" and f.stat().st_size > 10_000_000:  # 10MB
                        f.unlink()
        progress.update(task, advance=50)
    
    console.print("[green]✅ Cleanup complete[/green]")


@app.command("serve")
def serve_cmd(
    host: str = typer.Option(
        "127.0.0.1",
        "--host", "-h",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8420,
        "--port", "-p",
        help="Port to bind to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development",
    ),
):
    """
    🚀 Start the Ryx AI backend server.
    
    Provides REST API and WebSocket endpoints for the web UI.
    """
    from rich.console import Console
    console = Console()
    
    console.print(f"[cyan]🟣 Starting Ryx AI Server[/cyan]")
    console.print(f"   Host: {host}")
    console.print(f"   Port: {port}")
    console.print()
    
    try:
        import uvicorn
        # Import the API app
        from ryx_core.api import app as api_app
        uvicorn.run(api_app, host=host, port=port, reload=reload)
    except ImportError:
        console.print("[yellow]FastAPI server not yet implemented[/yellow]")
        console.print("[dim]Run: ryx session for CLI-based interaction[/dim]")


@app.command("version")
def version_cmd():
    """
    📋 Show Ryx AI version.
    """
    from rich.console import Console
    console = Console()
    
    console.print()
    console.print("[bold cyan]🟣 Ryx AI[/bold cyan]")
    console.print("   Version: 0.2.0")
    console.print("   Python: " + sys.version.split()[0])
    console.print()


def _start_session(safety_mode: str = "normal", tier: str = "balanced"):
    """Start interactive session"""
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    # Show welcome banner
    console.print()
    welcome = """[bold cyan]🟣 ryx – Local AI Agent[/bold cyan]

[dim]Tier:[/dim] {tier}
[dim]Safety:[/dim] {safety}

[dim]Commands: /help, /tier <name>, /quit[/dim]
[dim]Press Ctrl+C to save and exit[/dim]""".format(tier=tier, safety=safety_mode)
    
    console.print(Panel(welcome, border_style="cyan"))
    console.print()
    
    # Try to use existing session loop
    try:
        from core.session_loop import SessionLoop
        session = SessionLoop(safety_mode=safety_mode)
        session.run()
    except ImportError:
        # Fallback to simple REPL
        console.print("[yellow]Session loop not available, using simple mode[/yellow]")
        while True:
            try:
                prompt = console.input("[cyan]> [/cyan]")
                if prompt.strip().lower() in ["/quit", "/exit", "exit", "quit"]:
                    break
                if prompt.strip().lower() == "/help":
                    console.print("[dim]Commands: /quit, /help, /tier <name>[/dim]")
                    continue
                if prompt.strip():
                    _handle_prompt(prompt, tier=tier, safety_mode=safety_mode)
            except KeyboardInterrupt:
                console.print("\n[dim]Use /quit to exit[/dim]")
            except EOFError:
                break
    
    console.print("[dim]Goodbye! 👋[/dim]")


def _handle_prompt(prompt: str, tier: str = "balanced", safety_mode: str = "normal", stream: bool = True):
    """Handle a single prompt"""
    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()
    
    try:
        # Try to use the AI engine
        from core.ai_engine_v2 import AIEngineV2
        from core.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        intent = classifier.classify(prompt)
        
        console.print(f"[dim]Intent: {intent.intent_type.value}[/dim]")
        
        ai = AIEngineV2()
        response = ai.query(prompt, tier=tier)
        console.print(Markdown(response))
        
    except ImportError:
        # Fallback
        console.print(f"[yellow]AI engine not fully configured[/yellow]")
        console.print(f"[dim]Would process: {prompt}[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# Default behavior when no command given
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Main callback - start session if no command"""
    if ctx.invoked_subcommand is None:
        _start_session()


if __name__ == "__main__":
    app()
