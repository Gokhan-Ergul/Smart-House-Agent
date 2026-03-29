"""Stream / debug helpers (replaces notebook `run_query`)."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def run_query(str_input: str, agentt: Any, *, recursion_limit: int = 7) -> None:
    inputs = {"messages": [HumanMessage(content=str_input)]}
    try:
        for s in agentt.stream(inputs, config={"recursion_limit": recursion_limit}):
            for agent_name, output in s.items():
                logger.info("--- 🤖 %s ---", agent_name)

                if "next" in output:
                    logger.info("🔀 Rota: %s", output["next"])

                if "messages" in output:
                    last_msg = output["messages"][-1]
                    if isinstance(last_msg, SystemMessage):
                        continue

                    if hasattr(last_msg, "content") and last_msg.content:
                        logger.info("💬 Message: %s", last_msg.content)

                    if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
                        logger.info("🛠️ Tool: %s", last_msg.tool_calls[0]["name"])
                        logger.info("📝 Args: %s", last_msg.tool_calls[0]["args"])

                logger.info("------------------------------\n")

    except Exception as e:
        logger.exception("🛑 An error occurred: %s", e)
