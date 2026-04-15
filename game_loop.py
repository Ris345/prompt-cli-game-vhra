from __future__ import annotations

import random

from rich.prompt import Prompt

from .claude_client import generate_response, score_prompt
from .renderer import console, render_scene, render_score_panel
from .world_state import PromptScore, WorldState, save_session

SCENARIOS = [
    "product-manager",
    "software-engineer",
    "data-analyst",
    "technical-writer",
    "marketer",
    "recruiter",
]

SCENARIO_HINTS = {
    "product-manager":   "write PRDs, user stories, feature specs",
    "software-engineer": "code review, debugging, architecture advice",
    "data-analyst":      "query writing, data interpretation, reporting",
    "technical-writer":  "docs, API guides, how-to articles",
    "marketer":          "ad copy, campaign briefs, email drafts",
    "recruiter":         "job descriptions, interview questions, candidate evals",
}


def pick_scenario() -> str:
    console.print("[dim]scenarios:[/dim]")
    for s in SCENARIOS:
        console.print(f"  [cyan]{s}[/cyan]  [dim]{SCENARIO_HINTS[s]}[/dim]")
    choice = Prompt.ask(
        "\n[dim white]pick a scenario or press Enter for random[/dim white]",
        default="",
    )
    if not choice.strip():
        scenario = random.choice(SCENARIOS)
        console.print(f"[dim]randomly selected:[/dim] [cyan]{scenario}[/cyan]")
        return scenario
    lower = choice.strip().lower()
    for s in SCENARIOS:
        if s.startswith(lower) or lower in s:
            return s
    return lower


def run_game_loop(world_state: WorldState) -> None:
    render_scene(world_state, response=None)

    while True:
        console.print()
        try:
            user_input = Prompt.ask("[bold cyan]>[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[dim]session {world_state.session_id[:8]} saved.[/dim]")
            save_session(world_state)
            break

        stripped = user_input.strip()
        if not stripped:
            continue
        if stripped.lower() in {"quit", "exit", "q", ":q"}:
            console.print(f"[dim]session {world_state.session_id[:8]} saved.[/dim]")
            save_session(world_state)
            break

        with console.status("[dim]...[/dim]", spinner="dots"):
            try:
                score = score_prompt(stripped, world_state.history)
                response = generate_response(stripped, world_state, score)
            except Exception as exc:
                console.print(f"[red]API error:[/red] {exc}")
                continue

        console.print()
        render_scene(world_state, response)
        console.print()
        render_score_panel(score)

        world_state.add_turn(stripped, response, score)
        save_session(world_state)


def replay_session(world_state: WorldState) -> None:
    """Walk through a saved session turn by turn."""
    console.print(
        f"[dim]replaying session [cyan]{world_state.session_id[:8]}[/cyan]"
        f" — scenario: [cyan]{world_state.scenario}[/cyan]"
        f" — {len(world_state.scores)} turns[/dim]\n"
    )

    user_turns = [m["content"] for m in world_state.history if m["role"] == "user"]
    asst_turns = [m["content"] for m in world_state.history if m["role"] == "assistant"]

    offset = len(world_state.scores) - len(user_turns)

    for i, score_data in enumerate(world_state.scores):
        history_i = i - offset

        score = PromptScore(
            specificity=score_data["specificity"],
            context_provision=score_data["context_provision"],
            constraint_clarity=score_data["constraint_clarity"],
            output_format=score_data["output_format"],
            overall=score_data["overall"],
            feedback=["(replay — feedback not stored)"],
        )

        console.rule(f"[dim]Turn {i + 1} of {len(world_state.scores)}[/dim]")

        if 0 <= history_i < len(user_turns):
            console.print(f"[dim white]Prompt:[/dim white] {user_turns[history_i]}")
            console.print()
            if history_i < len(asst_turns):
                from .renderer import _T
                from rich.panel import Panel
                console.print(
                    Panel(
                        f"[{_T['response']}]{asst_turns[history_i]}[/{_T['response']}]",
                        border_style=_T["border"],
                        padding=(0, 2),
                    )
                )
                console.print()
        render_score_panel(score)

        try:
            Prompt.ask("[dim]  press Enter for next turn, Ctrl-C to stop[/dim]", default="")
        except (KeyboardInterrupt, EOFError):
            break
