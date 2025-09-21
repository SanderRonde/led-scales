"""Utility for exporting effect parameters to frontend-friendly formats"""

from typing import Dict, Any
from leds.effects.parameters import Parameter
from leds.effects.effect import Effect


def get_all_effects_parameters(effects: Dict[str, Effect]) -> Dict[str, Dict[str, Any]]:
    """Get parameters for all effects in the system"""
    result: Dict[str, Dict[str, Any]] = {}
    for effect_name, effect_class in effects.items():
        params: Dict[str, Dict[str, Any]] = {}
        for key, value in effect_class.PARAMETERS.__dict__.items():
            typed_param: Parameter = value
            params[key] = typed_param.json()
        result[effect_name] = params
    return result
