from typing import Optional, Union, List, Tuple, Any, Dict
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from leds import controllers
from leds.performance import profile_function, profile_block, get_profiler

# Unless otherwise specified, all dimensions are in mm


class BaseConfig(ABC):
    web_port: int = 5001

    @abstractmethod
    def get_led_count(self) -> int:
        pass


@dataclass(frozen=True)
class ScaleConfig(BaseConfig):
    web_port: int = 5001
    # A tuple of (pin, channel) per panel
    pins: Tuple[Tuple[int, int], ...] = ((13, 1), (19, 1), (26, 2))

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
    x_print_bed: float = 256
    y_print_bed: float = 256
    x_print_spacing: float = 25
    y_print_additional_spacing: float = 10
    print_outside_padding: float = 10
    # You'll want to change this
    scad_path: Union[str, Path] = "B:/programs/Program Files/OpenSCAD/openscad.exe"
    x_per_build_plate_override: Optional[int] = None
    y_per_build_plate_override: Optional[int] = None
    # This is purely visual and doesn't affect the result
    print_bed_spacing: float = 400

    # Debug
    is_fast: bool = False

    @profile_function("ScaleConfig.validate")
    def validate(self):
        with profile_block("ScaleConfig.validate.pin_check"):
            # Adjust print bed dimensions
            if len(self.pins) != self.panel_count:
                raise ValueError(
                    f"Number of pins ({len(self.pins)}) must match number of panels ({self.panel_count})"
                )
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
    def print_bed_x(self) -> float:
        return self.x_print_bed - (self.print_outside_padding * 2)

    @property
    def print_bed_y(self) -> float:
        return self.y_print_bed - (self.print_outside_padding * 2)

    @property
    def total_width(self) -> float:
        return self.panel_width * self.panel_count + (
            self.spacing * (self.panel_count - 1)
        )

    @property
    def total_height(self) -> float:
        return self.panel_height

    @property
    @lru_cache(maxsize=1)
    def scale_per_panel_count(self) -> int:
        return (self.x_count + self.x_count - 1) * self.y_count

    @lru_cache(maxsize=1)
    def get_led_count(self) -> int:
        return self.scale_per_panel_count * self.panel_count

    @property
    @lru_cache(maxsize=1)
    def total_weight_kg(self) -> float:
        return self.estimated_weight_g * self.get_led_count() / 1000

    @property
    @lru_cache(maxsize=1)
    def total_price_eur(self) -> float:
        return self.total_weight_kg * self.price_per_kilo

    @property
    @lru_cache(maxsize=1)
    def total_area_m2(self) -> float:
        return (self.panel_width * self.panel_height * self.panel_count) / 1000000


class Hexagon:
    def __init__(self, x: float, y: float, ordered_leds: List[int]):
        self.x = x
        self.y = y
        self.ordered_leds = ordered_leds

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "ordered_leds": self.ordered_leds}


class HexConfig(BaseConfig):
    def __init__(self):
        self.hexagons = [
            Hexagon(0, 1, [199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 248, 249, 250, 251, 252]),
            Hexagon(0, 2, [172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 303, 304, 305, 306]),
            Hexagon(0, 3, [145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 330, 331, 332, 333]),
            Hexagon(1, 0.5, [221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247]),
            Hexagon(1, 1.5, [194, 195, 196, 197, 198, 253, 254, 255, 256, 257, 258, 259, 260, 261, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302]),
            Hexagon(1, 2.5, [167, 168, 169, 170, 171, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329]),
            Hexagon(1, 3.5, [131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 334, 335, 336, 337, 338, 339, 340, 341, 342, 371, 372, 373, 374]),
            Hexagon(2, 0, [0, 1, 2, 3, 4, 5, 6, 7, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490]),
            Hexagon(2, 1, [262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288]),
            Hexagon(2, 3, [343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370]),
            Hexagon(2, 4, [113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 375, 376, 377, 378, 379, 380, 381, 382, 383]),
            Hexagon(3, 0.5, [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469]),
            Hexagon(3, 1.5, [45, 46, 47, 48, 49, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451]),
            Hexagon(3, 2.5, [72, 73, 74, 75, 76, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424]),
            Hexagon(3, 3.5, [99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397]),
            Hexagon(4, 1, [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 452, 453, 454, 455, 456]),
            Hexagon(4, 2, [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 425, 426, 427, 428, 429]),
            Hexagon(4, 3, [77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 398, 399, 400, 401, 402]),
        ]

    @profile_function("HexConfig.validate")
    def validate(self):
        get_profiler().logger.debug("Validating HexConfig")
        
        with profile_block("HexConfig.validate.coordinate_check"):
            for hexagon in self.hexagons:
                if hexagon.x % 2 == 1:
                    if hexagon.y % 1 != 0.5:
                        raise ValueError(
                            f"Hexagon {hexagon.x}, {hexagon.y} has y coordinate {hexagon.y}, expected half-digit number"
                        )
                else:
                    if hexagon.y % 1 != 0:
                        raise ValueError(
                            f"Hexagon {hexagon.x}, {hexagon.y} has y coordinate {hexagon.y}, expected integer"
                        )
        
        with profile_block("HexConfig.validate.led_count_check"):
            max_led_index = 0
            for hexagon in self.hexagons:
                max_led_index = max(max_led_index, *hexagon.ordered_leds)
            if max_led_index != self.get_led_count() - 1:
                raise ValueError(
                    f"Hexagon has {max_led_index + 1} LEDs, expected {self.get_led_count()}"
                )
        
        get_profiler().logger.debug(f"HexConfig validated: {len(self.hexagons)} hexagons, {self.get_led_count()} LEDs")

    @lru_cache(maxsize=1)
    def get_led_count(self) -> int:
        return sum(len(hexagon.ordered_leds) for hexagon in self.hexagons)

    pins: Tuple[int, int] = (13, 1)


# Change this to choose the config you want
_config = HexConfig()
# _config = ScaleConfig()

# Always validate the config with performance monitoring
with profile_block("config_validation"):
    _config.validate()
    get_profiler().logger.info(f"Configuration loaded and validated: {type(_config).__name__}")


def get_config() -> BaseConfig:
    return _config


@profile_function("get_led_controller")
def get_led_controller(mock: bool) -> controllers.ControllerBase:
    with profile_block("led_controller_creation"):
        if isinstance(_config, ScaleConfig):  # type: ignore
            controller = controllers.ScalePanelLEDController(_config, mock)
        elif isinstance(_config, HexConfig):  # type: ignore
            controller = controllers.HexPanelLEDController(_config, mock)
        else:
            raise ValueError(f"Unknown config type: {type(_config)}")
        
        get_profiler().logger.info(
            f"LED controller created: {type(controller).__name__}, "
            f"mock={mock}, LEDs={_config.get_led_count()}"
        )
        return controller
