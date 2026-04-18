from __future__ import annotations

from pathlib import Path

import anthropic

from .world_state import PromptScore, ScenarioResponse, WorldState

_client = anthropic.Anthropic()
_PROMPTS = Path(__file__).parent / "prompts"
_SCORE_MODEL = "claude-sonnet-4-6"
_SIM_MODEL = "claude-sonnet-4-6"

_prompt_cache: dict[str, str] = {}

_SCORE_TOOL = {
    "name": "score",
    "description": "Submit the prompt quality scores and feedback.",
    "input_schema": {
        "type": "object",
        "properties": {
            "specificity":        {"type": "integer", "minimum": 0, "maximum": 100},
            "context_provision":  {"type": "integer", "minimum": 0, "maximum": 100},
            "constraint_clarity": {"type": "integer", "minimum": 0, "maximum": 100},
            "output_format":      {"type": "integer", "minimum": 0, "maximum": 100},
            "overall":            {"type": "integer", "minimum": 0, "maximum": 100},
            "feedback":           {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
        },
        "required": ["specificity", "context_provision", "constraint_clarity", "output_format", "overall", "feedback"],
    },
}

_STORY_TOOL = {
    "name": "story_response",
    "description": "Submit the simulated Claude response and gap analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "what_claude_got":      {"type": "string"},
            "simulated_response":   {"type": "string"},
            "gaps":                 {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        },
        "required": ["what_claude_got", "simulated_response", "gaps"],
    },
}


def _load(name: str) -> str:
    if name not in _prompt_cache:
        _prompt_cache[name] = (_PROMPTS / name).read_text(encoding="utf-8")
    return _prompt_cache[name]


def _cached_system(name: str) -> list[dict]:
    return [{"type": "text", "text": _load(name), "cache_control": {"type": "ephemeral"}}]


def score_prompt(user_prompt: str, history: list[dict]) -> PromptScore:
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
        system=_cached_system("score.txt"),
        tools=[_SCORE_TOOL],
        tool_choice={"type": "tool", "name": "score"},
        messages=[{"role": "user", "content": f"{context}\nPrompt to score:\n{user_prompt}"}],
    )
    data = response.content[0].input
    return PromptScore(
        specificity=int(data["specificity"]),
        context_provision=int(data["context_provision"]),
        constraint_clarity=int(data["constraint_clarity"]),
        output_format=int(data["output_format"]),
        overall=int(data["overall"]),
        feedback=list(data["feedback"]),
    )


def generate_response(user_prompt: str, world_state: WorldState) -> ScenarioResponse:
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
        system=_cached_system("story.txt"),
        tools=[_STORY_TOOL],
        tool_choice={"type": "tool", "name": "story_response"},
        messages=messages,
    )
    data = response.content[0].input
    return ScenarioResponse(
        what_claude_got=str(data["what_claude_got"]),
        simulated_response=str(data["simulated_response"]),
        gaps=list(data.get("gaps", [])),
    )
