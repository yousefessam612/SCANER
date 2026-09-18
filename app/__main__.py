"""نقطة الدخول: python -m app [convert|resume|batch|selftest]"""
from __future__ import annotations

import sys


def main() -> int:
    from .cli import main as cli_main
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
