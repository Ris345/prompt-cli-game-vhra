from __future__ import annotations

import os
from typing import Optional

import typer

_EPILOG = """
Scenarios: product-manager · software-engineer · data-analyst · technical-writer · marketer · recruiter

Session IDs are shown at the start of each game and in `vhra --stats`.
Use the first 8 characters or the full UUID with --replay.

Requires: ANTHROPIC_API_KEY env var (get one at https://console.anthropic.com)
"""

app = typer.Typer(
    name="vhra",
    help="vhra — the prompt training engine",
    add_completion=False,
    no_args_is_help=False,
    epilog=_EPILOG,
)


@app.command(epilog=_EPILOG)
def main(
    replay: Optional[str] = typer.Option(
        None, "--replay", "-r", metavar="SESSION_ID",
        help="Replay a saved session turn-by-turn (8-char prefix or full UUID).",
    ),
    stats: bool = typer.Option(
        False, "--stats", "-s",
        help="Show prompt score history across all sessions.",
    ),
) -> None:
    """Train your prompting skills through real-world scenario practice.

    Run without arguments to start a new game. Pick a scenario, then type
    prompts to practice — each one is silently scored on specificity, context,
    constraints, and output format.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo(
            "\nError: ANTHROPIC_API_KEY is not set.\n\n"
            "  1. Get a key at https://console.anthropic.com\n"
            "  2. Run: export ANTHROPIC_API_KEY=\"sk-ant-...\"\n"
            "  3. Then run: vhra\n",
            err=True,
        )
        raise typer.Exit(code=1)

    from .renderer import console, render_splash

    render_splash()

    # --stats
    if stats:
        from .world_state import list_sessions
        from .renderer import render_stats_table

        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No sessions found yet. Run [cyan]vhra[/cyan] to start one.[/dim]")
        else:
            render_stats_table(sessions)
        return

    # --replay <id>
    if replay:
        from .world_state import load_session
        from .game_loop import replay_session

        ws = load_session(replay)
        if ws is None:
            console.print(f"[red]Session [bold]{replay!r}[/bold] not found.[/red]")
            raise typer.Exit(code=1)
        replay_session(ws)
        return

    # New game
    from .game_loop import pick_scenario, run_game_loop
    from .world_state import WorldState

    scenario = pick_scenario()
    world_state = WorldState(scenario=scenario)

    console.print(
        f"\n[dim]session id:[/dim] [dim white]{world_state.session_id}[/dim white]"
    )
    console.print(
        "[dim]type your prompts and press Enter each turn. "
        "[cyan]quit[/cyan] or [cyan]Ctrl-C[/cyan] to exit.[/dim]\n"
    )

    run_game_loop(world_state)



if __name__ == "__main__":
    app()
