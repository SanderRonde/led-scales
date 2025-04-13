"""Parameter definitions for LED effects"""
from dataclasses import dataclass
from typing import Any, List, Union
from enum import Enum


class ParameterType(Enum):
    """Types of parameters that can be used in effects"""
    FLOAT = "float"
    COLOR = "color"
    ENUM = "enum"
    COLOR_LIST = "color_list"


@dataclass
class Parameter:
    """Definition of a single parameter"""
    name: str
    type: ParameterType
    required: bool = True
    default: Any = None
    description: str = ""
    enum_values: Union[List[str], None] = None
