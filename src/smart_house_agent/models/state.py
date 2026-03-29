from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from langgraph.managed import RemainingSteps

PowerStatus = Literal["on", "off", "unknown"]
powerAction = Literal["on", "off"]

LockStatus = Literal["locked", "unlocked", "unknown"]
LockAction = Literal["lock", "unlock"]

OpenCloseStatus = Literal["open", "closed", "unknown"]
OpenCloseAction = Literal["open", "close"]

HvacStatus = Literal["off", "unknown"]
HvacAction = Literal["set_mode_off", "set_mode_on"]


class AgentState(TypedDict):
    light: PowerStatus
    door_lock: LockStatus
    curtain: OpenCloseStatus
    tv: PowerStatus
    thermostat_mode: HvacStatus
    main_water_valve: OpenCloseStatus
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: RemainingSteps
