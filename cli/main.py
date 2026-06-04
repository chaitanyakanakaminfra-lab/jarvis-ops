"""
cli/main.py
────────────
Jarvis CLI — command line interface using Typer.

Usage:
  jarvis run "check the cluster health"
  jarvis listen
  jarvis status
  jarvis logs
  jarvis scale-down
  jarvis scale-up
"""

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app     = Console()
cli     = typer.Typer(name="jarvis", help="Jarvis AI Ops Platform CLI")
console = Console()

JARVIS_API = "http://localhost:8000"


@cli.command()
def run(command: str = typer.Argument(..., help="Command to send to Jarvis")):
    """Send a command to Jarvis and get a spoken response."""
    console.print(f"[bold blue]Jarvis:[/bold blue] Processing '{command}'...")
    try:
        response = httpx.post(
            f"{JARVIS_API}/agents/run",
            json={"command": command},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        console.print(Panel(
            f"[green]{data['response']}[/green]",
            title="[bold]Jarvis Response[/bold]",
            border_style="blue",
        ))
    except httpx.ConnectError:
        console.print("[red]Cannot connect to Jarvis. Run 'make run' first.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def status():
    """Check Jarvis system status."""
    try:
        response = httpx.get(f"{JARVIS_API}/health", timeout=10)
        data = response.json()
        color = "green" if data["brain_ready"] else "yellow"
        console.print(Panel(
            f"[{color}]Status: {data['status']}\n"
            f"Brain ready: {data['brain_ready']}\n"
            f"Version: {data['version']}[/{color}]",
            title="[bold]Jarvis Status[/bold]",
            border_style=color,
        ))
    except httpx.ConnectError:
        console.print("[red]Jarvis is not running. Run 'make run' first.[/red]")


@cli.command()
def agents():
    """List all 15 Jarvis agents."""
    try:
        response = httpx.get(f"{JARVIS_API}/agents/list", timeout=10)
        data = response.json()
        table = Table(title="Jarvis Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Category", style="green")
        for agent in data["agents"]:
            table.add_row(agent["id"], agent["name"], agent["category"])
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def runs():
    """Show recent agent run history."""
    try:
        response = httpx.get(f"{JARVIS_API}/runs/", timeout=10)
        data = response.json()
        if not data.get("runs"):
            console.print("[yellow]No runs found.[/yellow]")
            return
        table = Table(title="Recent Agent Runs")
        table.add_column("Agent", style="cyan")
        table.add_column("Command", style="white")
        table.add_column("Status", style="green")
        table.add_column("Duration", style="yellow")
        for run in data["runs"]:
            status_color = "green" if run["status"] == "success" else "red"
            table.add_row(
                run["agent_id"],
                run["command"][:50],
                f"[{status_color}]{run['status']}[/{status_color}]",
                f"{run.get('duration_ms', 0)}ms",
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def listen():
    """Start Jarvis voice session."""
    console.print("[bold blue]Starting Jarvis voice session...[/bold blue]")
    console.print("[yellow]Say 'Hey Jarvis' to begin.[/yellow]")
    try:
        import asyncio
        from voice.voice_session import VoiceSession
        from orchestrator.brain import JarvisBrain
        brain = JarvisBrain()
        brain.initialise()
        session = VoiceSession(brain_handler=brain.process)
        asyncio.run(session.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Voice session stopped.[/yellow]")
    except Exception as e:
        console.print(f"[red]Voice session error: {e}[/red]")


if __name__ == "__main__":
    cli()
