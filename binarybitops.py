#!/usr/bin/env python3
"""Command-line view of the HDE model used by Task 3.10.

Run ``python binarybitops.py`` for the model output, or
``python -m binarybitops.server`` to start the workload.
"""

from __future__ import annotations

from binarybitops.bitops import compute
from binarybitops.hde_model import default_environment


def main() -> int:
    env = default_environment()
    env.display()
    env.audit_security()

    example = compute(12, 10)
    print("\n=== Demonstrator example ===")
    print(
        f"{example['left']} AND {example['right']} = {example['and']}, "
        f"OR = {example['or']}, XOR = {example['xor']}"
    )
    print("This CLI is a model view, not a live control assessment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
