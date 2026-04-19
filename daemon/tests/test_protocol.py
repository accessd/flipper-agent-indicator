import pytest

from flipper_indicator.protocol import (
    MAX_TEXT_BYTES,
    TAG_ACK,
    TAG_NOTIFY,
    TAG_PING,
    TAG_PONG,
    Ack,
    AgentId,
    Notify,
    Ping,
    Pong,
    State,
    decode,
    encode,
)


def roundtrip(frame):
    return decode(encode(frame))


def test_notify_roundtrip():
    f = Notify(AgentId.CLAUDE, State.NEEDS_INPUT, "Bash: rm -rf build/")
    assert roundtrip(f) == f


def test_notify_empty_text():
    f = Notify(AgentId.CODEX, State.DONE, "")
    encoded = encode(f)
    assert encoded == bytes([TAG_NOTIFY, AgentId.CODEX, State.DONE, 0])
    assert roundtrip(f) == f


def test_notify_text_truncated_to_max():
    long_text = "x" * (MAX_TEXT_BYTES * 2)
    f = Notify(AgentId.OPENCODE, State.RUNNING, long_text)
    decoded = roundtrip(f)
    assert isinstance(decoded, Notify)
    assert decoded.text == "x" * MAX_TEXT_BYTES


def test_notify_unicode_truncation_does_not_corrupt_utf8():
    text = "ё" * 40
    f = Notify(AgentId.CLAUDE, State.RUNNING, text)
    encoded = encode(f)
    assert encoded[3] <= MAX_TEXT_BYTES
    decoded = decode(encoded)
    assert isinstance(decoded, Notify)
    assert "\ufffd" not in decoded.text or decoded.text.endswith("\ufffd") or all(
        c == "ё" for c in decoded.text
    )


def test_ack_roundtrip():
    f = Ack(AgentId.GENERIC)
    assert encode(f) == bytes([TAG_ACK, 0xFF])
    assert roundtrip(f) == f


def test_ping_pong_roundtrip():
    assert encode(Ping()) == bytes([TAG_PING])
    assert encode(Pong()) == bytes([TAG_PONG])
    assert roundtrip(Ping()) == Ping()
    assert roundtrip(Pong()) == Pong()


def test_decode_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        decode(b"")


def test_decode_rejects_unknown_tag():
    with pytest.raises(ValueError, match="unknown tag"):
        decode(bytes([0x55]))


def test_decode_rejects_truncated_notify_header():
    with pytest.raises(ValueError, match="NOTIFY header"):
        decode(bytes([TAG_NOTIFY, 0, 0]))


def test_decode_rejects_truncated_notify_text():
    with pytest.raises(ValueError, match="NOTIFY text"):
        decode(bytes([TAG_NOTIFY, 0, 0, 10, ord("a")]))


def test_decode_rejects_truncated_ack():
    with pytest.raises(ValueError, match="ACK header"):
        decode(bytes([TAG_ACK]))


def test_encode_rejects_unknown_type():
    with pytest.raises(TypeError):
        encode("not-a-frame")  # type: ignore[arg-type]


def test_frame_size_stays_mtu_safe():
    f = Notify(AgentId.CLAUDE, State.NEEDS_INPUT, "x" * MAX_TEXT_BYTES)
    assert len(encode(f)) <= 100
