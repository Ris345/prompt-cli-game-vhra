from __future__ import annotations

import os
from typing import Optional

import typer

_STATIC_HELP = """
vhra — the prompt training engine

USAGE
  vhra                        start a new game
  vhra --stats                view scores across all sessions
  vhra --replay <session_id>  replay a past session turn-by-turn
  vhra --help                 show this help

SCENARIOS
  product-manager · software-engineer · data-analyst
  technical-writer · marketer · recruiter

HOW IT WORKS
  Each turn you type a prompt. Claude scores it on four dimensions:
  specificity, context provision, constraint clarity, and output format.
  Your score (0-100) determines how rich and useful Claude's response is.

TIPS
  - Name exact things: files, features, audiences, numbers
  - Give Claude the background it needs — role, goal, constraints
  - Specify what format you want: bullet points, table, code block, prose
  - Build on what Claude said in the previous turn

Session IDs are shown at the start of each game and in `vhra --stats`.
Use the first 8 characters or the full UUID with --replay.
"""

_HELP_SYSTEM_PROMPT = """You are the help assistant for vhra, a CLI game that trains prompting skills.

When a user runs `vhra --help`, give them a concise, friendly guide covering:
1. What vhra does in one sentence
2. The three commands (vhra, vhra --stats, vhra --replay <id>)
3. The six available scenarios and what each one is for
4. How scoring works (specificity, context provision, constraint clarity, output format)
5. Three concrete tips for writing higher-scoring prompts, with a before/after example each

Format for a terminal — plain text, no markdown. Keep it tight, under 35 lines.
Do not use bullet symbols or dashes for top-level sections — use ALL CAPS section labels instead."""


def _ai_help() -> None:
    import anthropic
    from .renderer import console

    client = anthropic.Anthropic()
    with console.status("[dim]loading help...[/dim]", spinner="dots"):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[{"type": "text", "text": _HELP_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": "show help"}],
        )
    console.print()
    console.print(response.content[0].text)
    console.print()


app = typer.Typer(
    name="vhra",
    add_completion=False,
    no_args_is_help=False,
    context_settings={"help_option_names": []},  # disable built-in --help so we control it
)


@app.command()
def main(
    help: bool = typer.Option(False, "--help", "-h", is_eager=False),
    replay: Optional[str] = typer.Option(
        None, "--replay", "-r", metavar="SESSION_ID",
        help="Replay a saved session (8-char prefix or full UUID).",
    ),
    stats: bool = typer.Option(
        False, "--stats", "-s",
        help="Show prompt score history across all sessions.",
    ),
) -> None:
    """vhra — the prompt training engine."""

    if help:
        if os.environ.get("ANTHROPIC_API_KEY"):
            _ai_help()
        else:
            typer.echo(_STATIC_HELP)
        raise typer.Exit()

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

    if stats:
        from .world_state import list_sessions
        from .renderer import render_stats_table

        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No sessions found yet. Run [cyan]vhra[/cyan] to start one.[/dim]")
        else:
            render_stats_table(sessions)
        return

    if replay:
        from .world_state import load_session
        from .game_loop import replay_session

        ws = load_session(replay)
        if ws is None:
            console.print(f"[red]Session [bold]{replay!r}[/bold] not found.[/red]")
            raise typer.Exit(code=1)
        replay_session(ws)
        return

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
