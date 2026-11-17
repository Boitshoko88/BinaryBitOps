"""Validated 16-bit bitwise operations used by the demonstrator.

The demonstrator's only application function is a bitwise calculator. It is
intentionally tiny, deterministic and free of third-party dependencies so the
delivery path, not the application logic, is what Task 3.10 evidences.
"""

from __future__ import annotations

from typing import Any

MAX_VALUE = 0xFFFF
BIT_WIDTH = 16


class BitOpsError(ValueError):
    """Raised when an operand is not a 16-bit unsigned integer."""


def parse_operand(raw: Any, name: str) -> int:
    """Parse *raw* as a base-10 or prefixed integer in the 16-bit range."""

    if isinstance(raw, bool):
        raise BitOpsError(f"{name} must be an integer between 0 and {MAX_VALUE}")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text or len(text) > 12:
            raise BitOpsError(f"{name} must be an integer between 0 and {MAX_VALUE}")
        try:
            # int(..., 0) accepts 10, 0b1010, 0o12 and 0x0A.
            value = int(text, 0) if text[:2].lower() in {"0b", "0o", "0x"} else int(text, 10)
        except ValueError as exc:
            raise BitOpsError(f"{name} must be an integer between 0 and {MAX_VALUE}") from exc
    else:
        raise BitOpsError(f"{name} must be an integer between 0 and {MAX_VALUE}")

    if value < 0 or value > MAX_VALUE:
        raise BitOpsError(f"{name} must be an integer between 0 and {MAX_VALUE}")
    return value


def to_binary(value: int) -> str:
    """Return a fixed-width binary representation (``0000 0000 0000 1100``)."""

    bits = format(value, f"0{BIT_WIDTH}b")
    return " ".join(bits[index : index + 4] for index in range(0, BIT_WIDTH, 4))


def compute(left: int, right: int) -> dict[str, Any]:
    """Compute AND, OR and XOR for two validated 16-bit operands."""

    return {
        "left": left,
        "right": right,
        "and": left & right,
        "or": left | right,
        "xor": left ^ right,
        "binary": {
            "left": to_binary(left),
            "right": to_binary(right),
            "and": to_binary(left & right),
            "or": to_binary(left | right),
            "xor": to_binary(left ^ right),
        },
        "bit_width": BIT_WIDTH,
    }


def compute_from_strings(left: Any, right: Any) -> dict[str, Any]:
    """Parse two raw values and return the computed result."""

    return compute(parse_operand(left, "left"), parse_operand(right, "right"))
