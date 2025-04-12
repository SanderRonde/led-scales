from dataclasses import dataclass
from typing import Optional, Union
from pathlib import Path

@dataclass
class ScaleConfig:
    # Scale dimensions
    base_length: float = 25
    base_width: float = 2
    base_height: float = 110
    spike_size: float = 50

    # Scale lean
    lean_base: float = 5
    lean_factor: float = 0.05

    # Panel layout
    spacing: float = 55
    x_count: int = 6
    y_count: int = 12
    panel_count: int = 3

    # LEDs
    led_diameter: float = 3 # Note that this is just the marked size. Real size does not matter and is up to your drill bit.

    # Filament weight and price
    estimated_weight_g: float = 23 / 2 # You probably don't want to change this
    price_per_kilo: float = 20 # Price in {currency} per kilogram of filament

    # 3D Printing
    x_print_bed: float = 200
    y_print_bed: float = 200
    x_print_spacing: float = 15
    y_print_additional_spacing: float = 6
    print_outside_padding: float = 20
    scad_path: Union[str, Path] = "B:/programs/Program Files/OpenSCAD/openscad.exe" # You'll want to change this
    x_per_build_plate_override: Optional[int] = None
    y_per_build_plate_override: Optional[int] = 1
    print_bed_spacing: float = 400 # This is purely visual and doesn't affect the result

    # Debug
    is_fast: bool = False

    def __post_init__(self):
        # Adjust print bed dimensions
        self.x_print_bed = self.x_print_bed - self.print_outside_padding
        self.y_print_bed = self.y_print_bed - self.print_outside_padding

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
    def scale_count(self) -> int:
        return (self.x_count + self.x_count - 1) * self.y_count * self.panel_count

    @property
    def total_weight_kg(self) -> float:
        return self.estimated_weight_g * self.scale_count / 1000

    @property
    def total_price_eur(self) -> float:
        return self.total_weight_kg * self.price_per_kilo

    @property
    def total_area_m2(self) -> float:
        return (self.panel_width * self.panel_height * self.panel_count) / 1000000

# Default configuration
default_config = ScaleConfig() 