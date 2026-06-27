"""Expiry sweep worker.

Run periodically (cron, a scheduler, or the loop below) to revoke access for
members whose paid period has ended.

    python -m bot.worker --once
    python -m bot.worker --interval 3600
"""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime

from bot.app import build_service
from bot.config import Settings


def run_once(service) -> int:
    expired = service.sweep_expired(datetime.now(tz=UTC))
    print(f"[sweep] revoked {len(expired)} expired member(s)")
    return len(expired)


def main() -> None:
    parser = argparse.ArgumentParser(description="Membership expiry sweeper")
    parser.add_argument("--once", action="store_true", help="run a single sweep")
    parser.add_argument("--interval", type=int, default=3600, help="seconds between sweeps")
    args = parser.parse_args()

    service = build_service(Settings())

    if args.once:
        run_once(service)
        return

    while True:  # pragma: no cover - long-running loop
        run_once(service)
        time.sleep(args.interval)


if __name__ == "__main__":  # pragma: no cover
    main()
