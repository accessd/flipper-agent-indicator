"""Binary frame protocol shared with the Flipper `.fap`.

One BLE write = one frame. Keep frames under 100 bytes to stay MTU-safe on
stock negotiation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

TAG_NOTIFY = 0x01
TAG_PING = 0x02
TAG_ACK = 0x81
TAG_PONG = 0x82

MAX_TEXT_BYTES = 64


class AgentId(IntEnum):
    CLAUDE = 0
    CODEX = 1
    OPENCODE = 2
    GENERIC = 0xFF


class State(IntEnum):
    OFF = 0
    RUNNING = 1
    NEEDS_INPUT = 2
    DONE = 3


@dataclass(frozen=True)
class Notify:
    agent: AgentId
    state: State
    text: str = ""


@dataclass(frozen=True)
class Ack:
    agent: AgentId


@dataclass(frozen=True)
class Ping:
    pass


@dataclass(frozen=True)
class Pong:
    pass


Frame = Notify | Ack | Ping | Pong


def encode(frame: Frame) -> bytes:
    if isinstance(frame, Notify):
        text = frame.text.encode("utf-8")[:MAX_TEXT_BYTES]
        return bytes([TAG_NOTIFY, int(frame.agent), int(frame.state), len(text)]) + text
    if isinstance(frame, Ack):
        return bytes([TAG_ACK, int(frame.agent)])
    if isinstance(frame, Ping):
        return bytes([TAG_PING])
    if isinstance(frame, Pong):
        return bytes([TAG_PONG])
    raise TypeError(f"unknown frame type: {type(frame).__name__}")


def decode(buf: bytes) -> Frame:
    if not buf:
        raise ValueError("empty frame")
    tag = buf[0]
    if tag == TAG_NOTIFY:
        if len(buf) < 4:
            raise ValueError("NOTIFY header truncated")
        agent, state, text_len = buf[1], buf[2], buf[3]
        payload = buf[4 : 4 + text_len]
        if len(payload) != text_len:
            raise ValueError("NOTIFY text truncated")
        return Notify(AgentId(agent), State(state), payload.decode("utf-8", errors="replace"))
    if tag == TAG_ACK:
        if len(buf) < 2:
            raise ValueError("ACK header truncated")
        return Ack(AgentId(buf[1]))
    if tag == TAG_PING:
        return Ping()
    if tag == TAG_PONG:
        return Pong()
    raise ValueError(f"unknown tag: 0x{tag:02x}")
