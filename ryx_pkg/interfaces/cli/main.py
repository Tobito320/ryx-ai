"""
Ryx AI - Command Line Interface
Typer-based CLI for natural language system commands
"""

import sys
import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ryx import __version__

# Setup project root for core imports
def _setup_project_root() -> Path:
    """Find and setup project root for core module imports."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "core").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return current

PROJECT_ROOT = _setup_project_root()
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('RYX_PROJECT_ROOT', str(PROJECT_ROOT))

# Initialize Typer app
app = typer.Typer(
    name="ryx",
    help="🟣 Ryx AI - Local agentic AI assistant",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


# =============================================================================
# Main Command
# =============================================================================

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: Optional[str] = typer.Argument(
        None,
        help="Natural language prompt to execute"
    ),
    model: Optional[str] = typer.Option(
        None, "-m", "--model",
        help="Specify model (qwen, mistral, deepseek, etc.)"
    ),
    code: bool = typer.Option(
        False, "--code",
        help="Code mode: optimize for code generation"
    ),
    chat: bool = typer.Option(
        False, "--chat",
        help="Chat mode: conversational responses"
    ),
    dev: bool = typer.Option(
        False, "--dev",
        help="Dev mode: include debug information"
    ),
    stream: bool = typer.Option(
        False, "--stream",
        help="Stream response tokens"
    ),
    quiet: bool = typer.Option(
        False, "--quiet",
        help="Minimal output, just the result"
    ),
    explain: bool = typer.Option(
        False, "--explain",
        help="Explain the reasoning process"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be done without executing"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose",
        help="Verbose output"
    ),
    version: bool = typer.Option(
        False, "--version",
        help="Show version and exit"
    ),
):
    """
    🟣 Ryx AI - Local agentic AI assistant

    Execute natural language commands or start interactive mode.

    Examples:
        ryx "open my hyprland config"
        ryx "find large files in home directory"
        ryx --code "create a python script to backup dotfiles"
        ryx -m qwen "explain this error"
    """
    if version:
        console.print(f"ryx version {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    if prompt:
        # Execute single prompt
        try:
            from core.vllm_client import VLLMClient
            
            client = VLLMClient()
            
            if stream:
                # Streaming response
                if not quiet:
                    console.print("[cyan]Response:[/cyan]")
                for chunk in client.generate_stream(prompt=prompt):
                    console.print(chunk, end="")
                console.print()
            else:
                # Non-streaming response
                result = client.generate(prompt=prompt)
                
                if result.error:
                    console.print(f"[red]Error: {result.error}[/red]")
                else:
                    if explain:
                        console.print(Panel(
                            result.response,
                            title="[bold cyan]Ryx AI Response[/bold cyan]",
                            border_style="purple"
                        ))
                    elif quiet:
                        console.print(result.response)
                    else:
                        console.print(f"\n[cyan]{result.response}[/cyan]\n")
                        
        except ImportError as e:
            console.print(f"[red]Error: vLLM client not available: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error executing prompt: {e}[/red]")
    else:
        # Start interactive mode
        console.print(Panel(
            "[bold cyan]Ryx AI Interactive Mode[/bold cyan]\n"
            "Type your commands or 'exit' to quit.",
            title="🟣 Ryx",
            border_style="purple"
        ))
        
        try:
            from core.session_loop import SessionLoop
            session = SessionLoop()
            session.run()
        except ImportError:
            # Fallback to simple interactive mode
            console.print("[yellow]Full interactive mode requires core modules.[/yellow]")
            console.print("[yellow]Using basic prompt mode.[/yellow]\n")
            
            try:
                from core.vllm_client import VLLMClient
                client = VLLMClient()
                
                while True:
                    try:
                        user_input = console.input("[purple]🟣 > [/purple]")
                        if user_input.lower() in ['exit', 'quit', 'q']:
                            console.print("[cyan]Goodbye![/cyan]")
                            break
                        
                        result = client.generate(prompt=user_input)
                        
                        if result.error:
                            console.print(f"[red]Error: {result.error}[/red]")
                        else:
                            console.print(f"\n[cyan]{result.response}[/cyan]\n")
                            
                    except KeyboardInterrupt:
                        console.print("\n[cyan]Goodbye![/cyan]")
                        break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


# =============================================================================
# Subcommands
# =============================================================================

@app.command()
def config(
    key: Optional[str] = typer.Argument(
        None,
        help="Configuration key to view/set"
    ),
    value: Optional[str] = typer.Option(
        None, "--set",
        help="Value to set for the key"
    ),
):
    """
    View or edit Ryx configuration.

    Examples:
        ryx config                  # Show all config
        ryx config default_model    # Show specific key
        ryx config default_model --set qwen  # Set value
    """
    import json
    
    try:
        from core.paths import get_config_dir
        config_file = get_config_dir() / "ryx_config.json"
        
        # Load or create config
        config_data = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        
        if key and value:
            # Set a config value
            keys = key.split('.')
            current = config_data
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = value
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            console.print(f"[green]✓[/green] Set {key} = {value}")
            
        elif key:
            # Get a specific key
            keys = key.split('.')
            current = config_data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    console.print(f"[yellow]Key not found: {key}[/yellow]")
                    return
            console.print(f"[cyan]{key}[/cyan] = {current}")
            
        else:
            # Show all config
            console.print(Panel(
                json.dumps(config_data, indent=2) if config_data else "No configuration set",
                title="[bold purple]Ryx Configuration[/bold purple]",
                border_style="purple"
            ))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def history(
    limit: int = typer.Option(
        10, "-n", "--limit",
        help="Number of entries to show"
    ),
    clear: bool = typer.Option(
        False, "--clear",
        help="Clear command history"
    ),
):
    """
    View or clear command history.

    Examples:
        ryx history           # Show last 10 commands
        ryx history -n 50     # Show last 50 commands
        ryx history --clear   # Clear all history
    """
    import json
    
    try:
        from core.paths import get_data_dir
        history_file = get_data_dir() / "session_state.json"
        
        if clear:
            if history_file.exists():
                # Load, clear history, and save
                with open(history_file, 'r') as f:
                    data = json.load(f)
                data['conversation_history'] = []
                with open(history_file, 'w') as f:
                    json.dump(data, f, indent=2)
                console.print("[green]✓[/green] History cleared")
            else:
                console.print("[yellow]No history to clear[/yellow]")
            return
        
        if not history_file.exists():
            console.print("[yellow]No history found[/yellow]")
            return
        
        with open(history_file, 'r') as f:
            data = json.load(f)
        
        entries = data.get('conversation_history', [])
        if not entries:
            console.print("[yellow]No history entries[/yellow]")
            return
        
        # Show the last N entries
        to_show = entries[-limit:]
        
        table = Table(title="[purple]Conversation History[/purple]")
        table.add_column("#", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("Message")
        
        for i, entry in enumerate(to_show, 1):
            role = entry.get('role', 'unknown')
            content = entry.get('content', '')
            # Truncate long messages
            if len(content) > 80:
                content = content[:77] + "..."
            table.add_row(str(i), role, content)
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(to_show)} of {len(entries)} entries[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def models(
    refresh: bool = typer.Option(
        False, "--refresh",
        help="Refresh model list from vLLM"
    ),
):
    """
    List available AI models.

    Examples:
        ryx models            # List cached models
        ryx models --refresh  # Refresh from vLLM
    """
    try:
        from core.vllm_client import VLLMClient
        
        if refresh:
            console.print("[cyan]Refreshing model list from vLLM...[/cyan]")
        
        client = VLLMClient()
        available_models = client.list_models()
        
        table = Table(title="[purple]Available Models[/purple]")
        table.add_column("Model", style="cyan")
        table.add_column("Status")
        
        for model in available_models:
            table.add_row(model, "[green]✓ Available[/green]")
        
        console.print(table)
        console.print(f"\n[dim]{len(available_models)} models available[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Tip: Make sure vLLM server is running (vllm serve)[/yellow]")


@app.command()
def status():
    """
    Show Ryx system status.

    Displays:
        - Ollama connection status
        - Loaded models
        - Cache status
        - System resources
    """
    try:
        from core.system_status import SystemStatus
        
        status_checker = SystemStatus()
        console.print(status_checker.format_status_display())
        
    except ImportError:
        # Fallback to basic status
        try:
            from core.vllm_client import VLLMClient
            
            console.print(Panel(
                "[bold purple]Ryx AI Status[/bold purple]",
                border_style="purple"
            ))
            
            client = VLLMClient()
            health = client.health_check()
            
            if health.get('status') == 'healthy':
                console.print(f"[green]●[/green] vLLM: [green]Online[/green]")
                console.print(f"  URL: {health.get('base_url')}")
                console.print(f"  Models: {health.get('models_available', 0)} available")
            else:
                console.print(f"[red]●[/red] vLLM: [red]Offline[/red]")
                console.print(f"  Error: {health.get('error', 'Connection failed')}")
                console.print("[yellow]Tip: Start vLLM with 'vllm serve'[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error checking status: {e}[/red]")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    app()
