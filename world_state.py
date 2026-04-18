from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from tinydb import Query, TinyDB

SESSIONS_DIR = Path.home() / ".vhra" / "sessions"


@dataclass
class PromptScore:
    specificity: int
    context_provision: int
    constraint_clarity: int
    output_format: int
    overall: int
    feedback: list[str]


@dataclass
class ScenarioResponse:
    what_claude_got: str       # one-sentence summary of how Claude interpreted the prompt
    simulated_response: str    # the actual simulated reply
    gaps: list[str]            # what was missing / ambiguous in the prompt


@dataclass
class WorldState:
    scenario: str
    scene_number: int = 0
    history: list[dict] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scores: list[dict] = field(default_factory=list)

    def trim_history(self, max_turns: int = 10) -> None:
        """Keep only the last max_turns exchanges (2 messages each)."""
        cap = max_turns * 2
        if len(self.history) > cap:
            self.history = self.history[-cap:]

    def add_turn(self, user_prompt: str, response: ScenarioResponse, score: PromptScore) -> None:
        self.history.append({"role": "user", "content": user_prompt})
        self.history.append({"role": "assistant", "content": response.simulated_response})
        self.scores.append(
            {
                "turn": self.scene_number,
                "specificity": score.specificity,
                "context_provision": score.context_provision,
                "constraint_clarity": score.constraint_clarity,
                "output_format": score.output_format,
                "overall": score.overall,
            }
        )
        self.scene_number += 1
        self.trim_history()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> WorldState:
        return cls(
            scenario=data["scenario"],
            scene_number=data["scene_number"],
            history=data["history"],
            session_id=data["session_id"],
            scores=data["scores"],
        )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _db_path(session_id: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{session_id}.json"


def save_session(world_state: WorldState) -> None:
    db = TinyDB(_db_path(world_state.session_id))
    S = Query()
    data = world_state.to_dict()
    if db.search(S.session_id == world_state.session_id):
        db.update(data, S.session_id == world_state.session_id)
    else:
        db.insert(data)


def load_session(session_id: str) -> Optional[WorldState]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    matches = list(SESSIONS_DIR.glob(f"{session_id}*.json"))
    if not matches:
        return None
    path = matches[0]
    db = TinyDB(path)
    results = db.all()
    if results:
        return WorldState.from_dict(results[0])
    return None


def list_sessions() -> list[WorldState]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions: list[WorldState] = []
    for db_path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            db = TinyDB(db_path)
            for item in db.all():
                sessions.append(WorldState.from_dict(item))
        except Exception:
            pass
    return sessions
