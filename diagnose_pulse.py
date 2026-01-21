import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def run_diagnostic():
    console.print("[bold cyan]Pulse Engine Diagnostic[/bold cyan]\n")
    
    try:
        from pulse import core
        HAS_PULSE = True
    except ImportError:
        HAS_PULSE = False
        console.print("[red]✖ Pulse package not found. Run 'pip install .' first.[/red]")
        return

    # Check for Rust Core
    try:
        import pulse_core
        HAS_RUST = True
        rust_version = getattr(pulse_core, "__version__", "Native")
    except ImportError:
        HAS_RUST = False
        rust_version = "Missing"

    # Engine Status Table
    table = Table(title="System Integrity Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Potential", justify="right")

    if HAS_RUST:
        table.add_row("Rust Engine", "[green]ACTIVE[/green]", "[bold]100%[/bold]")
        table.add_row("Precision", "[green]ENABLED[/green]", "0.2s Refresh")
    else:
        table.add_row("Rust Engine", "[yellow]INACTIVE[/yellow]", "[dim]70%[/dim]")
        table.add_row("Precision", "[yellow]DISABLED[/yellow]", "Fallback Mode")

    console.print(table)

    if HAS_RUST:
        console.print(Panel(
            "[bold green]SUCCESS:[/bold green] Pulse is running at [bold]FULL POTENTIAL[/bold].\n"
            "The native Rust engine is handling the data crunching.",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold yellow]NOTICE:[/bold yellow] Pulse is running in [bold]FALLBACK MODE[/bold].\n"
            "This is normal if you haven't installed the native binary yet.\n"
            "Automated builds are running on GitHub to fix this!",
            border_style="yellow"
        ))

if __name__ == "__main__":
    run_diagnostic()
