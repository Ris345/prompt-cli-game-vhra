from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .world_state import PromptScore, ScenarioResponse, WorldState

console = Console()

_T = {
    "border":     "dim white",
    "title":      "bold cyan",
    "response":   "white",
    "gaps":       "dim yellow",
    "interp":     "dim cyan",
    "score_hi":   "bright_green",
    "score_mid":  "yellow",
    "score_lo":   "red",
    "feedback":   "dim cyan",
    "dim":        "dim white",
}


# ---------------------------------------------------------------------------
# Splash
# ---------------------------------------------------------------------------

def render_splash() -> None:
    try:
        import pyfiglet
        fig = pyfiglet.figlet_format("vhra", font="slant")
    except Exception:
        fig = " vhra\n"
    console.clear()
    console.print(f"[bold green]{fig}[/bold green]")
    console.print(f"[{_T['dim']}]  the prompt training engine[/{_T['dim']}]\n")


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

def render_scene(world_state: WorldState, response: ScenarioResponse | None = None, opener: str = "") -> None:
    turn_num = world_state.scene_number + 1

    if response is None:
        situation = f"\n[white]{opener}[/white]\n" if opener else ""
        body = (
            f"[{_T['dim']}]scenario: [cyan]{world_state.scenario}[/cyan][/{_T['dim']}]"
            f"{situation}\n"
            f"[{_T['dim']}]The more specific and context-rich your prompt, the better Claude responds.[/{_T['dim']}]"
        )
        console.print(
            Panel(
                body,
                title=f"[{_T['title']}]vhra — {world_state.scenario}[/{_T['title']}]",
                border_style=_T["border"],
                padding=(1, 3),
            )
        )
        return

    # Interpretation line
    interp = f"[{_T['interp']}]Claude understood: {response.what_claude_got}[/{_T['interp']}]"

    # Simulated response
    sim = f"[{_T['response']}]{response.simulated_response}[/{_T['response']}]"

    # Gaps
    if response.gaps:
        gap_lines = "\n".join(f"  - {g}" for g in response.gaps)
        gaps_block = f"\n[{_T['gaps']}]missing context:\n{gap_lines}[/{_T['gaps']}]"
    else:
        gaps_block = f"\n[{_T['score_hi']}]  prompt was complete — no gaps detected[/{_T['score_hi']}]"

    grid = Table.grid(padding=(0, 0))
    grid.add_column()
    grid.add_row(interp)
    grid.add_row("")
    grid.add_row(sim)
    grid.add_row(gaps_block)

    console.print(
        Panel(
            grid,
            title=f"[{_T['title']}]Turn {turn_num} — {world_state.scenario}[/{_T['title']}]",
            border_style=_T["border"],
            padding=(1, 2),
        )
    )


# ---------------------------------------------------------------------------
# Score panel
# ---------------------------------------------------------------------------

def _score_color(val: int) -> str:
    if val >= 70:
        return _T["score_hi"]
    if val >= 40:
        return _T["score_mid"]
    return _T["score_lo"]


def render_score_panel(score: PromptScore) -> None:
    dims = [
        ("Specificity",        score.specificity),
        ("Context Provision",  score.context_provision),
        ("Constraint Clarity", score.constraint_clarity),
        ("Output Format",      score.output_format),
        ("Overall",            score.overall),
    ]

    bar_table = Table(show_header=False, box=None, padding=(0, 1))
    bar_table.add_column("label", style="dim white", min_width=19, no_wrap=True)
    bar_table.add_column("bar",   min_width=22, no_wrap=True)
    bar_table.add_column("val",   min_width=4, justify="right", no_wrap=True)

    for label, val in dims:
        filled = round(val / 100 * 20)
        bar = "#" * filled + "-" * (20 - filled)
        color = _score_color(val)
        is_overall = label == "Overall"
        lbl = f"[bold]{label}[/bold]" if is_overall else label
        bar_table.add_row(lbl, f"[{color}]{bar}[/{color}]", f"[{color}]{val:3d}[/{color}]")

    feedback_lines = "\n".join(f"  * {tip}" for tip in score.feedback)
    feedback = f"\n[{_T['feedback']}]{feedback_lines}[/{_T['feedback']}]"

    grid = Table.grid(padding=(0, 0))
    grid.add_column()
    grid.add_row(bar_table)
    grid.add_row(feedback)

    panel = Panel(
        grid,
        title=f"[dim]prompt score — {score.overall}/100[/dim]",
        border_style="dim",
        padding=(0, 1),
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Stats table
# ---------------------------------------------------------------------------

def render_stats_table(sessions: list[WorldState]) -> None:
    table = Table(
        title="[bold cyan]vhra — all session stats[/bold cyan]",
        box=box.SIMPLE_HEAVY,
        border_style="dim",
        header_style="bold dim white",
        show_lines=False,
    )
    table.add_column("Session",          style="dim",     width=10)
    table.add_column("Scenario",                          width=18)
    table.add_column("Turns",            justify="right", width=6)
    table.add_column("Avg Score",        justify="right", width=10)
    table.add_column("Best",             justify="right", width=6)
    table.add_column("Specificity",      justify="right", width=12)
    table.add_column("Context",          justify="right", width=10)
    table.add_column("Constraints",      justify="right", width=12)

    for ws in sessions:
        if not ws.scores:
            continue
        n = len(ws.scores)
        avg_overall = sum(s["overall"]           for s in ws.scores) / n
        avg_spec    = sum(s["specificity"]       for s in ws.scores) / n
        avg_ctx     = sum(s["context_provision"] for s in ws.scores) / n
        avg_con     = sum(s["constraint_clarity"] for s in ws.scores) / n
        best        = max(s["overall"]           for s in ws.scores)
        color       = _score_color(int(avg_overall))

        table.add_row(
            ws.session_id[:8],
            ws.scenario,
            str(n),
            f"[{color}]{avg_overall:.1f}[/{color}]",
            f"[bright_green]{best}[/bright_green]",
            f"{avg_spec:.1f}",
            f"{avg_ctx:.1f}",
            f"{avg_con:.1f}",
        )

    console.print(table)
