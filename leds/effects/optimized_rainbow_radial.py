"""
Optimized Rainbow Radial Effect with performance improvements.
"""

from leds.effects.optimized_effect import FastRadialEffect
from leds.effects.effect import SpeedWithDirectionParameters
from leds.performance import profile_function
from leds.controllers.controller_base import ControllerBase


class OptimizedRainbowRadialParameters(SpeedWithDirectionParameters):
    pass


class OptimizedRainbowRadialEffect(FastRadialEffect):
    """
    High-performance rainbow radial effect using pre-computed distances
    and cached color calculations.
    """
    
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = OptimizedRainbowRadialParameters()
    
    @profile_function("OptimizedRainbowRadialEffect._run_optimized")
    def _run_optimized(self, ms: int):
        # Get cached parameters
        speed = self.get_cached_param('speed', 0.6)
        direction = self.get_cached_param('direction', 'out')
        
        # Calculate time offset using cached values
        offset = self.time_offset(ms, speed, direction)
        
        # Use fast radial mapping with cached rainbow colors
        def color_func(distance: float):
            return self.cached_rainbow((distance + offset) % 1)
        
        self.map_radial_fast(color_func)
        self.controller.show()
    
    def get_name(self) -> str:
        return "Optimized Rainbow Radial"
