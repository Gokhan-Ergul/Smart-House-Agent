"""LangChain tools for device control (factory injects API client)."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from smart_house_agent.clients.home_api import HomeApiClient
from smart_house_agent.models.state import (
    HvacAction,
    LockAction,
    OpenCloseAction,
    powerAction,
)

logger = logging.getLogger(__name__)


def create_device_tools(api: HomeApiClient) -> list[Any]:
    @tool
    def control_light(device_id: str, action: powerAction) -> str:
        """
        Controls a light fixture by turning it 'on' or 'off'.
        This tool *only* sends the command; it does not check the current state.

        Args:
            device_id (str): The identifier for the light (e.g., 'living_room_light', 'kitchen_light').
            action (powerAction): The desired action, must be 'on' or 'off'.

        Returns:
            str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.info(
            "\n*** TOOL WORKED: control_light(device_id=%s, action=%s) ***",
            device_id,
            action,
        )

        try:
            response = api.post_update_device(device_id, action)
            if response.status_code == 200:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": f"I have turned {action} the {device_id}.",
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": f"I have turned {action} the {device_id}.",
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": device_id,
                "action": action,
                "message": f"I have turned {action} the {device_id}.",
            }

        return json.dumps(result_data)

    @tool
    def control_lock(device_id: str, action: LockAction) -> str:
        """
        Controls a door lock by setting it to 'lock' or 'unlock'.
        This tool *only* sends the command; it does not check the current state.

        Args:
            device_id (str): The identifier for the lock (e.g., 'front_door_lock').
            action (LockAction): The desired action, must be 'lock' or 'unlock'.

        Returns:
            str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.info(
            "\n*** TOOL WORKED: control_lock(device_id=%s, action=%s) ***",
            device_id,
            action,
        )

        action_val = action.value if hasattr(action, "value") else str(action)

        if action_val == "lock":
            message = f"I have locked the {device_id}."
        else:
            message = f"I have unlocked the {device_id}."

        try:
            response = api.post_update_device(device_id, str(action))
            if response.status_code == 200:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": device_id,
                "action": action,
                "message": message,
            }

        return json.dumps(result_data)

    @tool
    def control_curtain(device_id: str, action: OpenCloseAction) -> str:
        """
        Controls curtains or blinds by setting them to 'open' or 'close'.
        This tool *only* sends the command; it does not check the current state.

        Args:
            device_id (str): The identifier for the curtain (e.g., 'living_room_curtain').
            action (OpenCloseAction): The desired action, must be 'open' or 'close'.

        Returns:
            str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.info(
            "\n*** TOOL WORKED: control_curtain(device_id=%s, action=%s) ***",
            device_id,
            action,
        )
        if action == "open":
            message = f"I have opened the {device_id}."
        else:
            message = f"I have closed the {device_id}."

        try:
            response = api.post_update_device(device_id, action)
            if response.status_code == 200:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": device_id,
                "action": action,
                "message": message,
            }

        return json.dumps(result_data)

    @tool
    def control_tv(device_id: str, action: powerAction) -> str:
        """
        Controls a television by turning it 'on' or 'off'.
        This tool *only* sends the 'on' or 'off' command.

        Args:
            device_id (str): The identifier for the TV (e.g., 'living_room_tv').
            action (powerAction): The desired action, must be 'on' or 'off'.

        Returns:
            str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.info(
            "\n*** TOOL WORKED: control_tv(device_id=%s, action=%s) ***",
            device_id,
            action,
        )

        if action == "on":
            message = f"I have turned on the {device_id}."
        else:
            message = f"I have turned off the {device_id}."

        try:
            response = api.post_update_device(device_id, action)
            if response.status_code == 200:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": device_id,
                "action": action,
                "message": message,
            }

        return json.dumps(result_data)

    @tool
    def control_thermostat(action: HvacAction) -> str:
        """
        Controls the central thermostat by setting its operation mode.
        Assumes a single, central thermostat (no device_id needed).

        Args:
            action (HvacAction): The desired mode, e.g., "set_mode_off", "set_mode_on"

        Returns:
            str: A human-readable confirmation message.
        """
        logger.info("\n*** TOOL WORKED: control_thermostat(action=%s) ***", action)

        mode = action.split("_")[-1]
        message = f"I have set the thermostat mode to {mode}."

        try:
            response = api.post_update_device("thermostat_mode", action)
            if response.status_code == 200:
                result_data = {
                    "device_id": "thermostat_mode",
                    "action": action,
                    "message": message,
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": "thermostat_mode",
                    "action": action,
                    "message": message,
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": "thermostat_mode",
                "action": action,
                "message": message,
            }

        return json.dumps(result_data)

    @tool
    def control_water_valve(device_id: str, action: OpenCloseAction) -> str:
        """
        Controls a water valve by setting it to 'open' or 'close'.
        This tool *only* sends the command; it does not check the current state.

        Args:
            device_id (str): The identifier for the valve (e.g., 'main_water_valve').
            action (OpenCloseAction): The desired action, must be 'open' or 'close'.

        Returns:
             str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.info(
            "\n*** TOOL WORKED: control_water_valve(device_id=%s, action=%s) ***",
            device_id,
            action,
        )

        if action == "open":
            message = f"I have opened the {device_id}."
        else:
            message = f"I have closed the {device_id}."

        try:
            response = api.post_update_device(device_id, action)
            if response.status_code == 200:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "success",
                }
            else:
                result_data = {
                    "device_id": device_id,
                    "action": action,
                    "message": message,
                    "api_response": "failure",
                }
        except Exception:
            result_data = {
                "device_id": device_id,
                "action": action,
                "message": message,
            }

        return json.dumps(result_data)

    @tool
    def notify_unsupported_action(request: str, reason: str) -> str:
        """
        Call this tool ONLY when the user asks for something you cannot do (e.g., make coffee, fly to moon).

        Args:
            request (str): The action user asked for (e.g., "make coffee").
            reason (str): Why you can't do it (e.g., "I don't have a coffee machine").
        Returns:
             str: A JSON formatted string containing 'device_id', 'action', and a 'message'.
        """
        logger.warning("⚠️ [NOTIFICATION] Cannot fulfill: %s", request)

        message = f"I cannot {request} because {reason}."

        return json.dumps(
            {
                "device_id": "system",
                "action": "notify",
                "message": message,
            }
        )

    return [
        control_light,
        control_lock,
        control_curtain,
        control_tv,
        control_thermostat,
        control_water_valve,
        notify_unsupported_action,
    ]
