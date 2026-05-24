from __future__ import annotations

from .poller import run_once
from .store import JsonStore


def main() -> None:
    run_once(JsonStore())


if __name__ == "__main__":
    main()
