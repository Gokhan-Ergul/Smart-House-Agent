from typing import Literal, Optional

from pydantic import BaseModel, Field


class OperationsSchema(BaseModel):
    home_operations: list[
        Literal[
            "turn on light",
            "turn off light",
            "turn off tv",
            "turn on tv",
            "lock door",
            "unlock door",
            "close curtain",
            "open curtain",
            "open water valve",
            "close water valve",
            "turn on thermostat",
            "turn off thermostat",
        ]
    ] = Field(
        description="List of specific home automation actions required for the user-defined routine. "
        "Example: For 'Define Cinema Mode as a setting that turns off the lights and turns on the TV.', map to ['turn off light', 'turn on tv']."
    )
    operation_name: str = Field(
        description="The short name or trigger phrase for the operations defined by the user. "
        "Example: 'Cinema Mode' or 'Night Routine'."
    )


class RuleAndOperation(BaseModel):
    rules: list[str] = Field(
        description="Permanent behavioral instructions or preferences the user wants you to remember."
        "Example: 'Always speak formally to me' or 'Always ask me for approval before opening the door.'.",
        default_factory=list,
    )
    operations: Optional[OperationsSchema] = Field(
        description="Schema to define a new home automation routine/macro if the user requests one."
    )
