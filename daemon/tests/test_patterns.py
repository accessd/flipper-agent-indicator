from flipper_indicator.patterns import PatternTable
from flipper_indicator.protocol import AgentId, State


def test_defaults_exist_for_every_agent_and_state() -> None:
    table = PatternTable()
    for agent in AgentId:
        for state in State:
            p = table.get(agent, state)
            assert p.label
            assert len(p.led_rgb) == 3
            assert all(0 <= c <= 255 for c in p.led_rgb)


def test_needs_input_has_multi_pulse_vibra() -> None:
    table = PatternTable()
    p = table.get(AgentId.CLAUDE, State.NEEDS_INPUT)
    # at least two on-pulses so the user feels it's not a one-shot
    on_pulses = p.vibra_sequence[::2]
    assert len(on_pulses) >= 2


def test_overrides_replace_defaults() -> None:
    overrides = {
        "claude": {
            "running": {
                "led_rgb": [10, 20, 30],
                "vibra_sequence": [50, 50],
                "label": "custom",
            }
        }
    }
    table = PatternTable(overrides=overrides)
    p = table.get(AgentId.CLAUDE, State.RUNNING)
    assert p.led_rgb == (10, 20, 30)
    assert p.vibra_sequence == (50, 50)
    assert p.label == "custom"


def test_override_with_unknown_agent_is_ignored() -> None:
    table = PatternTable(overrides={"mystery": {"running": {"label": "nope"}}})
    # Default still returned.
    assert "mystery" not in table.get(AgentId.CLAUDE, State.RUNNING).label


def test_override_partial_keeps_defaults_for_missing_fields() -> None:
    table = PatternTable(overrides={"codex": {"done": {"label": "finished"}}})
    p = table.get(AgentId.CODEX, State.DONE)
    assert p.label == "finished"
    # led_rgb and vibra_sequence fall back to defaults.
    assert len(p.led_rgb) == 3
