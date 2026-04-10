"""Top-level supervisor graph: refresh_context → supervisor."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph_supervisor import create_supervisor

from smart_house_agent.agents.home_system import build_home_operations_graph
from smart_house_agent.agents.rule_keeper import build_rule_operations_graph
from smart_house_agent.agents.user_memory import build_add_user_info_graph
from smart_house_agent.clients.home_api import HomeApiClient
from smart_house_agent.config import Settings
from smart_house_agent.graph.prompts import SUPERVISOR_STATIC_PROMPT, SUPERVISOR_TEMPLATE
from smart_house_agent.models.state import AgentState
from smart_house_agent.persistence.home_status import HomeStatusStore
from smart_house_agent.persistence.rules_store import RulesStore
from smart_house_agent.persistence.user_memory import UserMemoryStore
from smart_house_agent.tools.devices import create_device_tools
from smart_house_agent.tools.weather import create_weather_tool

logger = logging.getLogger(__name__)


def build_supervisor_application(
    settings: Settings,
    llm: BaseChatModel,
    *,
    home_status: HomeStatusStore | None = None,
    memory_store: UserMemoryStore | None = None,
    rules_store: RulesStore | None = None,
    api_client: HomeApiClient | None = None,
) -> Any:
    """
    Compile the full smart-home graph (supervisor + sub-agents).
    Pass custom stores/client for tests; defaults use paths and URL from settings.
    """
    home_status = home_status or HomeStatusStore(settings.home_status_path)
    memory_store = memory_store or UserMemoryStore(settings.user_memory_path)
    rules_store = rules_store or RulesStore(settings.rules_operations_path)
    api_client = api_client or HomeApiClient(settings.smart_house_api_url)

    home_status.load()
    rules_store.ensure_default_file()

    home_system_tools = create_device_tools(api_client)
    get_weather = create_weather_tool()

    add_user_info = build_add_user_info_graph(llm, memory_store)
    home_operations = build_home_operations_graph(
        home_status,
        rules_store,
        llm,
        home_system_tools + [get_weather],
    )
    rule_operations = build_rule_operations_graph(llm, rules_store.path)

    def supervisor_context_node(state: AgentState):
        current_memory = memory_store.read()
        current_rules = rules_store.get_formatted_rules_and_operations()

        dynamic_content = SUPERVISOR_TEMPLATE.format(
            memory=current_memory,
            rule_and_operations=current_rules,
        )

        return {
            "messages": [SystemMessage(content=dynamic_content)],
        }

    supervisor = create_supervisor(
        agents=[add_user_info, home_operations, rule_operations],
        model=llm,
        tools=[get_weather],
        prompt=SUPERVISOR_STATIC_PROMPT,
        add_handoff_back_messages=True,
        output_mode="full_history",
    )

    builder = StateGraph(AgentState)
    builder.add_node("refresh_context", supervisor_context_node)
    builder.add_node("supervisor", supervisor.compile())
    builder.add_edge(START, "refresh_context")
    builder.add_edge("refresh_context", "supervisor")
    builder.add_edge("supervisor", END)

    return builder.compile()


def maybe_warmup_api(client: HomeApiClient) -> None:
    """Notebook had a best-effort POST to verify API connectivity."""
    try:
        client.post_update_device("thermostat_mode", "set_mode_off")
    except Exception:
        logger.warning(
            "To run this code, you must ensure the home automation API server is running at localhost:8000. "
            "Or you can continue without api connection for testing purposes."
        )
