"""PyInstaller entry point: same dispatch as python -m app."""
from app.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
