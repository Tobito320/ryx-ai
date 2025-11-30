# Task 1.4: Typer CLI Structure

**Time:** 20 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Create a Typer CLI application scaffold for Ryx AI with all command structures defined, argument parsing, and help text.

## Output File(s)

`ryx/interfaces/cli/main.py`

## Requirements

1. Create a Typer application with these commands:

   | Command | Usage | Description |
   |---------|-------|-------------|
   | default | `ryx "prompt"` | Execute a single prompt |
   | interactive | `ryx` | Start interactive mode |
   | model | `ryx -m model` | Specify model to use |
   | mode | `ryx --code/--chat/--dev` | Set operation mode |
   | flags | `ryx --stream/--quiet/--explain/--dry-run` | Behavior flags |

2. Command structure:
   ```
   ryx [OPTIONS] [PROMPT]
   
   Options:
     -m, --model TEXT      Specify model (qwen, mistral, deepseek, etc.)
     --code                Code mode: optimize for code generation
     --chat                Chat mode: conversational responses
     --dev                 Dev mode: include debug information
     --stream              Stream response tokens
     --quiet               Minimal output, just the result
     --explain             Explain the reasoning process
     --dry-run             Show what would be done without executing
     -v, --verbose         Verbose output
     --version             Show version and exit
     --help                Show this help message
   ```

3. Subcommands:
   ```
   ryx config    # View/edit configuration
   ryx history   # View command history
   ryx models    # List available models
   ryx status    # Show system status
   ```

4. All commands should print "Command executed: [name]" for testing

5. Include help text for all options and commands

## Code Template

```python
"""
Ryx AI - Command Line Interface
Typer-based CLI for natural language system commands
"""

from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel

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
        console.print("ryx version 0.1.0")
        raise typer.Exit()
    
    if ctx.invoked_subcommand is not None:
        return
    
    if prompt:
        # Execute single prompt
        console.print(f"Command executed: prompt")
        console.print(f"  Prompt: {prompt}")
        console.print(f"  Model: {model or 'auto'}")
        console.print(f"  Mode: {'code' if code else 'chat' if chat else 'dev' if dev else 'auto'}")
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
```

## Acceptance Criteria

- [ ] Typer app created with name "ryx"
- [ ] Main callback handles prompt and interactive mode
- [ ] `-m, --model` option for model selection
- [ ] `--code`, `--chat`, `--dev` mode flags implemented
- [ ] `--stream`, `--quiet`, `--explain`, `--dry-run` flags implemented
- [ ] `-v, --verbose` and `--version` flags implemented
- [ ] `config` subcommand with key/value handling
- [ ] `history` subcommand with limit and clear options
- [ ] `models` subcommand with refresh option
- [ ] `status` subcommand implemented
- [ ] All commands print "Command executed: [name]" for testing
- [ ] Help text provided for all options
- [ ] File can run: `python -m ryx.interfaces.cli.main --help`

## Notes

- Create the directory structure if it doesn't exist
- Add `__init__.py` files as needed for the package structure
- Use Rich console for pretty output
- The `@app.callback(invoke_without_command=True)` pattern handles both direct prompts and subcommands
- All subcommands should be scaffolds that print confirmation only
- No actual implementation of AI logic required
