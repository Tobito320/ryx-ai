"""
Ryx AI - Command Line Interface
Typer-based CLI for natural language system commands
"""

from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel

from ryx import __version__

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
        console.print("Command executed: prompt")
        console.print(f"  Prompt: {prompt}")
        console.print(f"  Model: {model or 'auto'}")
        # Determine mode based on flags
        if code:
            mode_str = "code"
        elif chat:
            mode_str = "chat"
        elif dev:
            mode_str = "dev"
        else:
            mode_str = "auto"
        console.print(f"  Mode: {mode_str}")
        # TODO: Implement actual prompt execution
    else:
        # Start interactive mode
        console.print(Panel(
            "[bold cyan]Ryx AI Interactive Mode[/bold cyan]\n"
            "Type your commands or 'exit' to quit.",
            title="🟣 Ryx",
            border_style="purple"
        ))
        console.print("Command executed: interactive")
        # TODO: Implement actual interactive loop


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
    console.print("Command executed: config")
    if key:
        if value:
            console.print(f"  Setting {key} = {value}")
        else:
            console.print(f"  Viewing: {key}")
    else:
        console.print("  Showing all configuration")
    # TODO: Implement actual config operations


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
    console.print("Command executed: history")
    if clear:
        console.print("  Clearing history...")
    else:
        console.print(f"  Showing last {limit} entries")
    # TODO: Implement actual history operations


@app.command()
def models(
    refresh: bool = typer.Option(
        False, "--refresh",
        help="Refresh model list from Ollama"
    ),
):
    """
    List available AI models.

    Examples:
        ryx models            # List cached models
        ryx models --refresh  # Refresh from Ollama
    """
    console.print("Command executed: models")
    if refresh:
        console.print("  Refreshing model list...")
    else:
        console.print("  Listing available models")
    # TODO: Implement actual model listing


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
    console.print("Command executed: status")
    console.print("  Checking system status...")
    # TODO: Implement actual status check


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    app()
