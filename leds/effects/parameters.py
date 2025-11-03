"""Parameter definitions for LED effects"""

from dataclasses import dataclass
from typing import Any, List, Dict, Optional
from abc import ABC, abstractmethod
from enum import Enum
from leds.color import RGBW, Color


class ParameterType(Enum):
    """Types of parameters that can be used in effects"""

    FLOAT = "float"
    COLOR = "color"
    ENUM = "enum"
    COLOR_LIST = "color_list"


@dataclass
class Parameter(ABC):
    """Definition of a single parameter"""

    default: Any = None
    description: str = ""
    value: Any = None
    type: ParameterType = NotImplemented

    def __init__(self, default: Any = None, description: str = ""):
        self.default = default if default is not None else self.default
        self.description = description
        self.value = self.default

    @abstractmethod
    def get_value(self) -> Any:
        """Get the value of the parameter"""
        self.value = self.default

    def set_value(self, value: Any):
        """Set the value of the parameter"""
        self.value = value

    def json(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "description": self.description,
            "value": self.value,
        }


class FloatParameter(Parameter):
    """Float parameter"""

    default: float = 0.0
    type: ParameterType = ParameterType.FLOAT

    def __init__(self, default: float = 0.0, description: str = ""):
        super().__init__(default, description)

    def get_value(self) -> float:
        """Get the value of the parameter"""
        return float(self.value)


class ColorParameter(Parameter):
    """Color parameter"""

    default: RGBW = Color(0, 0, 0)
    type: ParameterType = ParameterType.COLOR

    def __init__(self, default: RGBW = Color(0, 0, 0), description: str = ""):
        super().__init__(default, description)

    def get_value(self) -> RGBW:
        """Get the value of the parameter"""
        return self.value

    def set_value(self, value: Dict[str, int]):
        """Set the value of the parameter"""
        self.value = Color(value["r"], value["g"], value["b"])

    def json(self) -> Dict[str, Any]:
        return {**super().json(), "value": self.value.to_dict()}


class EnumParameter(Parameter):
    """Enum parameter"""

    default: str = ""
    enum_values: List[str] = []
    type: ParameterType = ParameterType.ENUM

    def __init__(
        self,
        default: str = "",
        description: str = "",
        enum_values: Optional[List[str]] = None,
    ):
        super().__init__(default, description)
        self.enum_values = enum_values or []

    def get_value(self) -> str:
        """Get the value of the parameter"""
        return self.value

    def json(self) -> Dict[str, Any]:
        return {**super().json(), "enum_values": self.enum_values}


class ColorListParameter(Parameter):
    """Color list parameter"""

    default: List[RGBW] = []
    type: ParameterType = ParameterType.COLOR_LIST

    def __init__(self, default: Optional[List[RGBW]] = None, description: str = ""):
        super().__init__(default, description)
        self.default = default or []

    def get_value(self) -> List[RGBW]:
        """Get the value of the parameter"""
        return self.value

    def set_value(self, value: List[Dict[str, int]]):
        """Set the value of the parameter"""
        self.value = [Color(color["r"], color["g"], color["b"]) for color in value]

    def json(self) -> Dict[str, Any]:
        """Override json method to properly serialize RGBW objects in the list"""
        return {
            "type": self.type.value,
            "description": self.description,
            "value": [
                color.to_dict() if isinstance(color, RGBW) else color
                for color in self.value
            ],
        }
