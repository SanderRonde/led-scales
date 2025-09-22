"""
Optimized base classes for LED effects with performance improvements.
"""

from functools import lru_cache
from typing import Dict, Any, Literal, Optional
from abc import ABC, abstractmethod
import math
import time
from leds.controllers.controller_base import ControllerBase
from leds.color import RGBW
from leds.performance import profile_function, profile_block, get_profiler
from leds.effects.effect import Effect


class OptimizedEffect(Effect):
    """
    Performance-optimized base class for LED effects.
    Includes caching, batching, and profiling improvements.
    """
    
    @profile_function("OptimizedEffect.__init__")
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        
        # Performance tracking
        self._frame_count = 0
        self._last_param_check = 0
        self._param_cache_interval = 10  # Check parameters every N frames
        self._cached_params = {}
        
        # Color caching
        self._color_cache: Dict[tuple, RGBW] = {}
        self._max_cache_size = 1000
        
        # Timing optimizations
        self._last_time_ms = 0
        self._time_delta = 0
        
    def run(self, ms: int):
        """Optimized run method with profiling and caching"""
        with profile_block(f"{self.__class__.__name__}.run"):
            # Calculate time delta for smoother animations
            self._time_delta = ms - self._last_time_ms
            self._last_time_ms = ms
            
            # Cache parameter values to avoid repeated attribute access
            if self._frame_count % self._param_cache_interval == 0:
                self._update_param_cache()
            
            # Run the actual effect
            self._run_optimized(ms)
            
            # Clean cache periodically
            if self._frame_count % 100 == 0:
                self._cleanup_cache()
                
            self._frame_count += 1
    
    @abstractmethod
    def _run_optimized(self, ms: int):
        """Override this method instead of run() for optimized effects"""
        pass
    
    def _update_param_cache(self):
        """Cache frequently accessed parameter values"""
        if hasattr(self.PARAMETERS, 'speed'):
            self._cached_params['speed'] = self.PARAMETERS.speed.get_value()
        if hasattr(self.PARAMETERS, 'direction'):
            self._cached_params['direction'] = self.PARAMETERS.direction.get_value()
        if hasattr(self.PARAMETERS, 'color'):
            self._cached_params['color'] = self.PARAMETERS.color.get_value()
        if hasattr(self.PARAMETERS, 'brightness'):
            self._cached_params['brightness'] = self.PARAMETERS.brightness.get_value()
    
    def _cleanup_cache(self):
        """Clean up color cache to prevent memory growth"""
        if len(self._color_cache) > self._max_cache_size:
            # Keep only the most recent half of the cache
            items = list(self._color_cache.items())
            self._color_cache = dict(items[len(items)//2:])
    
    def get_cached_param(self, name: str, default=None):
        """Get a cached parameter value"""
        return self._cached_params.get(name, default)
    
    @lru_cache(maxsize=512)
    def cached_rainbow(self, value: float) -> RGBW:
        """Cached rainbow color generation"""
        return Effect.rainbow(value)
    
    @lru_cache(maxsize=1024)
    def cached_interpolate(self, from_color: RGBW, to_color: RGBW, 
                          value: float, interpolation: str = "linear") -> RGBW:
        """Cached color interpolation"""
        return Effect.interpolate_color(from_color, to_color, value, interpolation)
    
    def batch_set_pixels(self, pixel_data: Dict[int, RGBW], strip_index: int = 0):
        """Batch set multiple pixels for better performance"""
        strips = self.controller.get_strips()
        if strip_index < len(strips):
            strip = strips[strip_index]
            for pixel_index, color in pixel_data.items():
                if pixel_index < strip.numPixels():
                    strip.setPixelColor(pixel_index, color)


class FastRadialEffect(OptimizedEffect):
    """
    Optimized base class for radial effects with pre-computed distance maps.
    """
    
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self._distance_map = None
        self._max_distance = None
        self._precompute_distances()
    
    @profile_function("FastRadialEffect._precompute_distances")
    def _precompute_distances(self):
        """Pre-compute distance values for all LEDs"""
        self._distance_map = {}
        self._max_distance = self.controller.get_max_distance()
        
        def store_distance(distance: float, index: tuple):
            self._distance_map[index] = distance / self._max_distance if self._max_distance > 0 else 0
        
        self.controller.map_distance(store_distance)
        
        get_profiler().logger.debug(
            f"Pre-computed distances for {len(self._distance_map)} LEDs, "
            f"max_distance={self._max_distance:.2f}"
        )
    
    def map_radial_fast(self, color_func):
        """Fast radial mapping using pre-computed distances"""
        with profile_block("FastRadialEffect.map_radial_fast"):
            for (panel_idx, led_idx), normalized_distance in self._distance_map.items():
                color = color_func(normalized_distance)
                if color is not None:
                    strips = self.controller.get_strips()
                    if panel_idx < len(strips):
                        strips[panel_idx].setPixelColor(led_idx, color)


class BatchedEffect(OptimizedEffect):
    """
    Effect that batches LED updates for better performance.
    """
    
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self._pixel_buffer = {}
        self._batch_size = 50  # Update LEDs in batches
    
    def queue_pixel(self, strip_index: int, pixel_index: int, color: RGBW):
        """Queue a pixel update for batched processing"""
        if strip_index not in self._pixel_buffer:
            self._pixel_buffer[strip_index] = {}
        self._pixel_buffer[strip_index][pixel_index] = color
    
    def flush_pixel_buffer(self):
        """Apply all queued pixel updates"""
        with profile_block("BatchedEffect.flush_pixel_buffer"):
            strips = self.controller.get_strips()
            for strip_index, pixels in self._pixel_buffer.items():
                if strip_index < len(strips):
                    strip = strips[strip_index]
                    for pixel_index, color in pixels.items():
                        if pixel_index < strip.numPixels():
                            strip.setPixelColor(pixel_index, color)
            
            self._pixel_buffer.clear()


class PerformanceMonitoredEffect(OptimizedEffect):
    """
    Effect wrapper that provides detailed performance monitoring.
    """
    
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self._effect_times = []
        self._last_performance_log = time.time()
        self._performance_log_interval = 5.0  # Log every 5 seconds
    
    def _run_optimized(self, ms: int):
        start_time = time.perf_counter()
        
        # Call the actual effect implementation
        self._run_effect_impl(ms)
        
        # Track performance
        effect_time = (time.perf_counter() - start_time) * 1000
        self._effect_times.append(effect_time)
        
        # Periodic performance logging
        current_time = time.time()
        if current_time - self._last_performance_log > self._performance_log_interval:
            self._log_performance_stats()
            self._last_performance_log = current_time
    
    @abstractmethod
    def _run_effect_impl(self, ms: int):
        """Implement the actual effect logic here"""
        pass
    
    def _log_performance_stats(self):
        """Log detailed performance statistics"""
        if not self._effect_times:
            return
        
        profiler = get_profiler()
        avg_time = sum(self._effect_times) / len(self._effect_times)
        max_time = max(self._effect_times)
        min_time = min(self._effect_times)
        
        profiler.logger.info(
            f"{self.__class__.__name__} performance: "
            f"avg={avg_time:.2f}ms, min={min_time:.2f}ms, max={max_time:.2f}ms, "
            f"samples={len(self._effect_times)}"
        )
        
        # Clear times to prevent memory growth
        self._effect_times.clear()
