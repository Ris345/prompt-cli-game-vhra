from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic

from .world_state import PromptScore, ScenarioResponse, WorldState

_client = anthropic.Anthropic()
_PROMPTS = Path(__file__).parent / "prompts"
_SCORE_MODEL = "claude-sonnet-4-5"
_SIM_MODEL = "claude-sonnet-4-5"


def _load(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8")


def _parse_json(text: str) -> dict:
    """Robustly extract a JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end_idx = next(
            (i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"),
            len(lines),
        )
        text = "\n".join(lines[start:end_idx]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No valid JSON found in model output:\n{text[:300]}")


def score_prompt(user_prompt: str, history: list[dict]) -> PromptScore:
    """Call 1: silently score the user's prompt on domain prompting dimensions."""
    context = ""
    if history:
        last_assistant = next(
            (m["content"] for m in reversed(history) if m["role"] == "assistant"),
            "",
        )
        if last_assistant:
            context = f"\nPrior assistant response (for context_provision scoring):\n{last_assistant[:600]}\n"

    response = _client.messages.create(
        model=_SCORE_MODEL,
        max_tokens=512,
        system=_load("score.txt"),
        messages=[
            {
                "role": "user",
                "content": f"{context}\nPrompt to score:\n{user_prompt}",
            }
        ],
    )
    data = _parse_json(response.content[0].text)
    return PromptScore(
        specificity=int(data["specificity"]),
        context_provision=int(data["context_provision"]),
        constraint_clarity=int(data["constraint_clarity"]),
        output_format=int(data["output_format"]),
        overall=int(data["overall"]),
        feedback=list(data["feedback"]),
    )


def generate_response(
    user_prompt: str, world_state: WorldState, score: PromptScore
) -> ScenarioResponse:
    """Call 2: simulate how Claude would respond to this prompt in the given scenario."""
    tagged_prompt = (
        f"[Scenario: {world_state.scenario}] "
        f"[Turn: {world_state.scene_number + 1}]\n\n"
        f"{user_prompt}"
    )

    messages = list(world_state.history)
    messages.append({"role": "user", "content": tagged_prompt})

    response = _client.messages.create(
        model=_SIM_MODEL,
        max_tokens=1200,
        system=_load("story.txt"),
        messages=messages,
    )
    data = _parse_json(response.content[0].text)
    return ScenarioResponse(
        what_claude_got=str(data["what_claude_got"]),
        simulated_response=str(data["simulated_response"]),
        gaps=list(data.get("gaps", [])),
    )
