"""Rules / operations subgraph (rule_operations)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from smart_house_agent.models.rules import RuleAndOperation
from smart_house_agent.models.state import AgentState

logger = logging.getLogger(__name__)


def make_rule_keeper(llm: BaseChatModel, rules_file: Path):
    def rule_keeper(state: AgentState):
        """
        Responsible for creating, updating, or deleting automation rules and routines (macros).

        Trigger this agent ONLY when the user defines a FUTURE behavior or SCENARIO:
        1. Defining Routines/Modes:
           - e.g., "Create 'Cinema Mode' that turns off lights and turns on TV."
           - e.g., "Update 'Morning Routine' to also open the curtains."
        2. Setting Persistent Rules:
           - e.g., "Always ask for confirmation before unlocking the door."
           - e.g., "Never turn on the music after 10 PM."

        Capabilities:
        - Parses user intent into structured JSON (Operations & Rules).
        - Persists data to 'rules_operations.json'.
        - Merges new instructions with existing ones (Update/Overwrite logic).

        Do NOT use for:
        - Executing a command RIGHT NOW (e.g., "Turn on the light" -> use 'home_system_agent').
        - Queries about current device status.
        """
        rules_path = str(rules_file)

        default_data = {"rules": [], "operations": []}

        rules_data = default_data

        try:
            if os.path.exists(rules_path):
                with open(rules_path, encoding="utf-8") as f:
                    try:
                        file_content = json.load(f)

                        if file_content:
                            rules_data = file_content
                            logger.info("Rules Agent: Loaded existing rules from JSON.")
                        else:
                            logger.info("Rules Agent: JSON file is empty. Using default structure.")

                    except json.JSONDecodeError:
                        logger.warning("Rules Agent: JSON decode error (file might be corrupted). Starting fresh.")
            else:
                logger.info("Rules Agent: '%s' not found. Starting fresh.", rules_path)

        except Exception as e:
            logger.warning("Rules Agent: Error reading file: %s", e)

        current_rules_content = json.dumps(rules_data, ensure_ascii=False, indent=2)

        system_prompt_content = """
    You are the "Rule Manager" of a smart home system.
    Your ONLY job is to maintain a persistent record of automation rules based on user commands.

    ### CURRENT DATABASE (JSON format):
    {current_rules_content}

    ### INSTRUCTIONS:
    1. Analyze the User's Input to identify the **Trigger** (e.g., "Cinema Mode", "I'm home") and the **Actions** (e.g., "Lights off", "TV on").

    2. **SEMANTIC MATCHING**
        - Before creating a new Trigger key, look at the CURRENT DATABASE keys.
        - If the user's trigger is semantically similar to an existing key (e.g., "Movie Mode" ≈ "Cinema Mood", "I'm back" ≈ "Welcome Home"), **USE THE EXISTING KEY**.

    3. **UPDATE LOGIC:**
        - If the Trigger is NEW: Create the entry.
        - If the Trigger EXISTS:
            a. **MERGE** the new actions with the existing actions.
            b. **DEDUPLICATE:** Remove exact duplicates (e.g., do NOT allow ["Light on", "Light on"]).
            c. **RESOLVE CONFLICTS:** If a NEW action conflicts with an OLD action (e.g., Old: "Light On", New: "Light Off"), the **NEW action overwrites** the old one.
            d. **CONTEXT AWARENESS:** If the user phrase implies a full definition (e.g., "When I say X, do A, B and C"), ensure the final list reflects exactly A, B, and C. Remove unrelated old actions if they seem contradictory to the new definition.

    4. **OUTPUT FORMAT:**
        - Output ONLY the updated JSON string.
        - No markdown, no conversation, no explanations.
        - If the user input is unclear, return the CURRENT DATABASE unchanged.

    ### EXAMPLE:
    Current: {{"cinema mode": ["lights off", "tv on"]}}
    User: "For cinema mode, also close the curtains"
    Output: {{"cinema mode": ["lights off", "tv on", "close the curtains"]}}

    Current: {{"sleep mode": ["lights on"]}}
    User: "Change sleep mode to turn lights off"
    Output: {{"sleep mode": ["lights off"]}}
    """

        user_msg = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None,
        )
        if not user_msg:
            return {"messages": [AIMessage(content="No user message found to process.")]}

        structured_llm = llm.with_structured_output(RuleAndOperation)

        system_prompt = SystemMessage(
            content=system_prompt_content.format(current_rules_content=current_rules_content)
        )

        messages = [
            system_prompt,
            HumanMessage(content=user_msg),
        ]

        response_obj = structured_llm.invoke(messages)

        if os.path.exists(rules_path):
            try:
                with open(rules_path, encoding="utf-8") as f:
                    current_data = json.load(f)
            except json.JSONDecodeError:
                current_data = {"rules": [], "operations": []}
        else:
            current_data = {"rules": [], "operations": []}

        if "rules" not in current_data:
            current_data["rules"] = []
        if "operations" not in current_data:
            current_data["operations"] = []

        changes_log = []

        if response_obj.rules:
            added_count = 0
            for new_rule in response_obj.rules:
                if new_rule not in current_data["rules"]:
                    current_data["rules"].append(new_rule)
                    added_count += 1

            if added_count > 0:
                changes_log.append(f"Added {added_count} new rules.")

        new_op_name = None
        if response_obj.operations:
            new_op_data = response_obj.operations.model_dump()
            new_op_name = new_op_data.get("operation_name")

            found_index = -1
            for i, existing_op in enumerate(current_data["operations"]):
                if existing_op.get("operation_name") == new_op_name:
                    found_index = i
                    break

            if found_index != -1:
                current_data["operations"][found_index] = new_op_data
                changes_log.append(f"Updated existing operation: '{new_op_name}'")
            else:
                current_data["operations"].append(new_op_data)
                changes_log.append(f"Created new operation: '{new_op_name}'")

        try:
            if changes_log:
                confirmation_msg = f"[SYSTEM_REPORT] Database updated successfully. {' '.join(changes_log)}"
                with open(rules_path, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=4)
            else:
                confirmation_msg = (
                    f"[SYSTEM_REPORT] No new changes detected. The operation '{new_op_name}' already exists with these settings."
                )

            logger.info("Rules Agent: %s", confirmation_msg)

            return {"messages": [AIMessage(content=confirmation_msg, name="rule_operations")]}

        except Exception as e:
            error_msg = f"[SYSTEM_REPORT] File write error: {e}"
            logger.error("Rules Agent Error: %s", e)
            return {"messages": [AIMessage(content=error_msg, name="rule_operations")]}

    return rule_keeper


def build_rule_operations_graph(llm: BaseChatModel, rules_file: Path):
    graph_rule = StateGraph(AgentState)
    graph_rule.add_node("keep_user_rules", make_rule_keeper(llm, rules_file))
    graph_rule.add_edge(START, "keep_user_rules")
    graph_rule.add_edge("keep_user_rules", END)
    return graph_rule.compile(name="rule_operations")
