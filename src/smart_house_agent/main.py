"""CLI entry point."""

from __future__ import annotations

import argparse
import logging

from smart_house_agent.config import configure_logging, get_llm, get_settings
from smart_house_agent.graph.supervisor_graph import build_supervisor_application, maybe_warmup_api
from smart_house_agent.runner import run_query

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart House multi-agent supervisor")
    parser.add_argument(
        "query",
        nargs="?",
        default="What is the weather like today?",
        help="User message to send to the supervisor graph",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip best-effort API warmup POST",
    )
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    llm = get_llm(settings)

    from smart_house_agent.clients.home_api import HomeApiClient

    api = HomeApiClient(settings.smart_house_api_url)
    if not args.no_warmup:
        maybe_warmup_api(api)

    graph = build_supervisor_application(settings, llm, api_client=api)
    run_query(args.query, graph)


if __name__ == "__main__":
    main()
