"""Entrypoint: the analytics worker process.

Consumes click events from the Redis Stream and writes them to ClickHouse.
Built out in Phase 3 — this is a placeholder so the three-process layout from
plan.md Section 4 exists from Phase 0 onward.

Run locally with: uv run python -m app.worker_main
"""

import asyncio

from app.core.logging import configure_logging

configure_logging()


async def main() -> None:
    raise NotImplementedError("Worker event loop is built in Phase 3.")


if __name__ == "__main__":
    asyncio.run(main())
