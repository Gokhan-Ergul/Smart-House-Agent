"""Home device control subgraph (home_operations)."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from smart_house_agent.models.state import AgentState
from smart_house_agent.persistence.home_status import HomeStatusStore
from smart_house_agent.persistence.rules_store import RulesStore

logger = logging.getLogger(__name__)


def make_home_system_agent(
    home_status: HomeStatusStore,
    rules_store: RulesStore,
    home_system_llm: BaseChatModel,
):
    def home_system_agent(state: AgentState) -> dict:
        """
        Responsible for executing immediate commands to control smart home devices.

        Trigger this agent ONLY when the user wants to change the physical state of:
        - Lights (turn on/off)
        - TV (turn on/off)
        - Curtains/Blinds (open/close)
        - Door Locks (lock/unlock)
        - Thermostat (set mode off/on)
        - Main Water Valve (open/close)

        Capabilities:
        - Checks the current state (HOME_DB) to avoid redundant actions.
        - Handles predefined automation modes that affect these devices.

        Do NOT use for:
        - Creating or editing automation rules.
        - Updating user profile/memory.
        """

        db = home_status.data
        light = db["light"]
        tv = db["tv"]
        curtain = db["curtain"]
        door_lock = db["door_lock"]
        thermostat_mode = db["thermostat_mode"]
        main_water_valve = db["main_water_valve"]

        rules_content = rules_store.get_operations_json_for_prompt()

        system_prompt = f"""You are a precise smart home automation agent.

# 1. TRUTH: CURRENT DEVICE STATE
- Light: {light}
- Door Lock: {door_lock}
- Curtain: {curtain}
- TV: {tv}
- Thermostat Mode: {thermostat_mode}
- Main Water Valve: {main_water_valve}

# 1.5. KNOWLEDGE BASE: AUTOMATION MODES
If the user asks for a Mode (e.g. "Good Night"), use these definitions:
{rules_content}

# 2. DEVICE ID MAPPING
Use ONLY: 'light', 'door_lock', 'curtain', 'tv', 'main_thermostat', 'main_water_valve'.

# 3. EXECUTION ALGORITHM (MANDATORY)
You must process the user's request using this exact 3-step logic for EVERY device mentioned:

Step 1: Identify ALL devices mentioned in the user's request.
Step 2: For EACH device, compare "Current State" vs "Desired State":
**YOU HAVE TO PROVE** that (Current State != Desired State) before calling any tool.
   - IF (Current == Desired) -> **IGNORE** (Do nothing).
   - IF (Current != Desired) -> **ADD TO QUEUE** (Call the tool).
Step 3: Final Decision:
   - **IF Queue has tools:** Call them immediately.
      
# 4. HANDLING UNSUPPORTED REQUESTS
If a request is physically impossible (e.g., "Make coffee", "Play music"):
- Call `notify_unsupported_action(request=..., reason=...)`.

# 5. EXAMPLE LOGIC
User: "Turn off light (currently off) and TV (currently on)."
- Light: Off == Off -> Ignore.
- TV: On != Off -> **Call control_tv(action='off').**
Result: Only call TV tool.

User Request:"""

        messages = state["messages"]
        executed_tool_outputs = []

        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                if msg.name and "transfer" in msg.name:
                    break
                executed_tool_outputs.append(msg)
            else:
                break

        if executed_tool_outputs:
            response_sentences = []

            for tool_msg in reversed(executed_tool_outputs):
                try:
                    content = json.loads(tool_msg.content)

                    user_text = content.get("message", f"Action completed for {content.get('device_id')}.")
                    response_sentences.append(user_text)

                    device_id = str(content.get("device_id", "")).lower()
                    action = str(content.get("action", "")).lower()

                    if "set_mode_" in action:
                        action = action.split("_")[-1]
                    if "lock" == action:
                        action = "locked"
                    if "unlock" == action:
                        action = "unlocked"
                    if "close" == action:
                        action = "closed"
                    if "open" == action:
                        action = "open"

                    home_status.update_device(device_id, action)

                except json.JSONDecodeError:
                    response_sentences.append("Task completed.")
            home_status.save()

            final_response = " ".join(response_sentences)

            return {"messages": [AIMessage(content=final_response, name="home_operations")]}

        user_msg = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None,
        )

        if not user_msg:
            return {"messages": [AIMessage(content="I'm ready. What can I help you with?", name="home_operations")]}

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ]

        response = home_system_llm.invoke(messages)

        logger.info("home agent message: %s", response)
        return {
            "messages": [response],
        }

    return home_system_agent


def make_should_continue(state: AgentState) -> str:
    """
    Decides whether to continue the workflow or end it.
    If the last AIMessage contains a tool call, continue to the tool node.
    Otherwise, end the workflow.
    """
    last_message = state["messages"][-1] if state["messages"] else None

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


def build_home_operations_graph(
    home_status: HomeStatusStore,
    rules_store: RulesStore,
    llm: BaseChatModel,
    home_system_tools: list[Any],
):
    home_system_llm = llm.bind_tools(home_system_tools)
    agent_fn = make_home_system_agent(home_status, rules_store, home_system_llm)
    tool_node = ToolNode(home_system_tools)

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_fn)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        make_should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile(name="home_operations")
