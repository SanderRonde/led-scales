"""Utility for exporting effect parameters to frontend-friendly formats"""
from typing import Dict, List, Union, Type
from leds.effects.parameters import Parameter
from leds.effects.effect import Effect


def parameter_to_json(param: Parameter) -> Dict[str, Union[str, bool, float, int, List[str]]]:
    """Convert a Parameter to a JSON-serializable dictionary"""
    result: Dict[str, Union[str, bool, float, int, List[str]]] = {
        "name": param.name,
        "type": param.type.value,
        "required": param.required,
        "description": param.description
        # TODO:(sander) current value
    }

    if param.enum_values is not None:
        result["enum_values"] = param.enum_values

    return result


def get_effect_parameters_json(effect_class: Type[Effect]) -> List[Dict[str, Union[str, bool, float, int, List[str]]]]:
    """Get all parameters for an effect class in JSON-serializable format"""
    # Use explicitly defined parameters if available
    # type: ignore
    return [parameter_to_json(param) for param in effect_class.PARAMETERS]


def get_all_effects_parameters() -> Dict[str, List[Dict[str, Union[str, bool, float, int, List[str]]]]]:
    """Get parameters for all effects in the system"""
    from leds.effects import __all__
    from leds.effects import Effect

    result: Dict[str,
                 List[Dict[str, Union[str, bool, float, int, List[str]]]]] = {}
    for effect_name in __all__:
        if effect_name != 'Effect':  # Skip the base Effect class
            effect_class = getattr(__import__(
                'leds.effects', fromlist=[effect_name]), effect_name)
            if issubclass(effect_class, Effect):
                result[effect_name] = get_effect_parameters_json(effect_class)
    return result
