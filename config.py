from typing import Optional, Union, List, Tuple, Any, Dict
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from leds import controllers
# Unless otherwise specified, all dimensions are in mm


class BaseConfig(ABC):
    web_port: int = 5001

    @abstractmethod
    def get_led_count(self) -> int:
        pass


@dataclass
class ScaleConfig(BaseConfig):
    web_port: int = 5001
    # A tuple of (pin, channel) per panel
    pins: List[Tuple[int, int]] = field(
        default_factory=lambda: [(13, 1), (19, 1), (26, 2)])

    # Scale dimensions
    base_length: float = 25
    base_width: float = 2
    base_height: float = 110
    spike_size: float = 50

    # Scale lean
    lean_base: float = 5
    lean_factor: float = 0.05

    # Panel layout
    spacing: int = 55  # Spacing between scales
    panel_spacing_scales: int = 1  # Spacing between panels
    x_count: int = 6
    y_count: int = 12
    panel_count: int = 3

    # LEDs
    led_diameter: float = 10
    led_diffuser_thickness: float = 6
    led_template_diameter: float = 3  # Note that this is just the marked size.

    # Filament weight and price
    estimated_weight_g: float = 23 / 2  # You probably don't want to change this
    price_per_kilo: float = 20  # Price in {currency} per kilogram of filament

    # 3D Printing
    x_print_bed: float = 200
    y_print_bed: float = 200
    x_print_spacing: float = 15
    y_print_additional_spacing: float = 6
    print_outside_padding: float = 20
    # You'll want to change this
    scad_path: Union[str,
                     Path] = "B:/programs/Program Files/OpenSCAD/openscad.exe"
    x_per_build_plate_override: Optional[int] = None
    y_per_build_plate_override: Optional[int] = 1
    # This is purely visual and doesn't affect the result
    print_bed_spacing: float = 400

    # Debug
    is_fast: bool = False

    def __post_init__(self):
        # Adjust print bed dimensions
        if len(self.pins) != self.panel_count:
            raise ValueError(
                f"Number of pins ({len(self.pins)}) must match number of panels ({self.panel_count})")
        if self.panel_count % 2 != 1:
            raise ValueError("Panel count must be an odd number")

    @property
    def spike_height(self) -> float:
        return self.base_height - self.spike_size

    @property
    def panel_width(self) -> float:
        return self.x_count * self.spacing

    @property
    def panel_height(self) -> float:
        return (self.y_count + 0.5) * self.spacing

    @property
    def total_width(self) -> float:
        return self.panel_width * self.panel_count + (self.spacing * (self.panel_count - 1))

    @property
    def total_height(self) -> float:
        return self.panel_height

    @property
    def scale_per_panel_count(self) -> int:
        return (self.x_count + self.x_count - 1) * self.y_count

    def get_led_count(self) -> int:
        return self.scale_per_panel_count * self.panel_count

    @property
    def total_weight_kg(self) -> float:
        return self.estimated_weight_g * self.get_led_count() / 1000

    @property
    def total_price_eur(self) -> float:
        return self.total_weight_kg * self.price_per_kilo

    @property
    def total_area_m2(self) -> float:
        return (self.panel_width * self.panel_height * self.panel_count) / 1000000


class Hexagon:
    def __init__(self, x: float, y: float, ordered_leds: List[int]):
        self.x = x
        self.y = y
        self.ordered_leds = ordered_leds

    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'ordered_leds': self.ordered_leds
        }


class HexConfig(BaseConfig):
    def __init__(self):
        self.hexagons = [
            Hexagon(0, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
            Hexagon(0, 1, [50, 51, 52, 53, 54, 55, 56, 57, 58, 59]),
            Hexagon(1, 0.5, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]),
            Hexagon(1, 1.5, [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]),
            Hexagon(2, 0, [60, 61, 62, 63, 64, 65, 66, 67, 68, 69]),
            Hexagon(2, 1, [30, 31, 32, 33, 34, 35, 36, 37, 38, 39]),
            Hexagon(2, 2, [40, 41, 42, 43, 44, 45, 46, 47, 48, 49]),
        ]

    def __post_init__(self):
        for hexagon in self.hexagons:
            if hexagon.x % 2 == 0:
                if hexagon.y % 1 != 0.5:
                    raise ValueError(
                        f"Hexagon {hexagon.x}, {hexagon.y} has y coordinate {hexagon.y}, expected half-digit number")
            else:
                if hexagon.y % 1 != 0:
                    raise ValueError(
                        f"Hexagon {hexagon.x}, {hexagon.y} has y coordinate {hexagon.y}, expected integer")

            max_led_index = 0
            for hexagon in self.hexagons:
                max_led_index = max(max_led_index, *hexagon.ordered_leds)
            if max_led_index != len(hexagon.ordered_leds) - 1:
                raise ValueError(
                    f"Hexagon {hexagon.x}, {hexagon.y} has {len(hexagon.ordered_leds)} LEDs, expected {max_led_index + 1}")

    def get_led_count(self) -> int:
        return sum(len(hexagon.ordered_leds) for hexagon in self.hexagons)

    pins: Tuple[int, int] = (13, 1)


# Change this to choose the config you want
_config = HexConfig()
# _config = ScaleConfig()


def get_config() -> BaseConfig:
    return _config


def get_led_controller(mock: bool) -> controllers.ControllerBase:
    if isinstance(_config, ScaleConfig):  # type: ignore
        return controllers.ScalePanelLEDController(_config, mock)
    if isinstance(_config, HexConfig):  # type: ignore
        return controllers.HexPanelLEDController(_config, mock)
    raise ValueError(f"Unknown config type: {type(_config)}")
