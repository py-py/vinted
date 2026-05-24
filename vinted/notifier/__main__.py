from __future__ import annotations

from .poller import run_once
from .store import get_store


def main() -> None:
    run_once(get_store())


if __name__ == "__main__":
    main()
