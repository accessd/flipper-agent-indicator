"""Per-(agent, state) pattern table.

The Flipper firmware chooses the actual LED/vibra pattern from the `(agent,
state)` pair in the NOTIFY frame. Host-side this table is for logging and for
validating user overrides from ``config.toml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .protocol import AgentId, State


@dataclass(frozen=True)
class Pattern:
    led_rgb: tuple[int, int, int]
    vibra_sequence: tuple[int, ...]  # alternating on/off ms
    label: str


# Agent base colors (blue / green / purple / white).
_AGENT_COLOR: dict[AgentId, tuple[int, int, int]] = {
    AgentId.CLAUDE: (40, 100, 255),
    AgentId.CODEX: (40, 220, 120),
    AgentId.OPENCODE: (180, 80, 255),
    AgentId.GENERIC: (255, 255, 255),
}

# Vibra pattern per state. Host does not play these; firmware does.
_STATE_VIBRA: dict[State, tuple[int, ...]] = {
    State.OFF: (),
    State.RUNNING: (60, 120),
    State.NEEDS_INPUT: (120, 80, 120, 80, 120, 400),
    State.DONE: (200,),
}

_STATE_LABEL: dict[State, str] = {
    State.OFF: "off",
    State.RUNNING: "running",
    State.NEEDS_INPUT: "needs input",
    State.DONE: "done",
}

_AGENT_LABEL: dict[AgentId, str] = {
    AgentId.CLAUDE: "Claude",
    AgentId.CODEX: "Codex",
    AgentId.OPENCODE: "OpenCode",
    AgentId.GENERIC: "Agent",
}


class PatternTable:
    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._overrides: dict[tuple[AgentId, State], Pattern] = {}
        if overrides:
            self._load_overrides(overrides)

    def get(self, agent: AgentId, state: State) -> Pattern:
        override = self._overrides.get((agent, state))
        if override is not None:
            return override
        return Pattern(
            led_rgb=_AGENT_COLOR[agent],
            vibra_sequence=_STATE_VIBRA[state],
            label=f"{_AGENT_LABEL[agent]}: {_STATE_LABEL[state]}",
        )

    def _load_overrides(self, raw: dict[str, Any]) -> None:
        for agent_name, states in raw.items():
            agent = _parse_agent(agent_name)
            if agent is None or not isinstance(states, dict):
                continue
            for state_name, spec in states.items():
                state = _parse_state(state_name)
                if state is None or not isinstance(spec, dict):
                    continue
                led = spec.get("led_rgb", _AGENT_COLOR[agent])
                vibra = spec.get("vibra_sequence", _STATE_VIBRA[state])
                label = spec.get("label", f"{_AGENT_LABEL[agent]}: {_STATE_LABEL[state]}")
                self._overrides[(agent, state)] = Pattern(
                    led_rgb=tuple(int(x) for x in led),  # type: ignore[arg-type]
                    vibra_sequence=tuple(int(x) for x in vibra),
                    label=str(label),
                )


def _parse_agent(name: str) -> AgentId | None:
    try:
        return AgentId[name.upper()]
    except KeyError:
        return None


def _parse_state(name: str) -> State | None:
    try:
        return State[name.upper().replace("-", "_")]
    except KeyError:
        return None
