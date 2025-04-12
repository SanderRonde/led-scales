import os
import sys
from typing import Tuple, Type, Any

# Try to import the real library first
try:
    from rpi_ws281x import PixelStrip as RealPixelStrip, Color as RealColor
    REAL_LIBRARY_AVAILABLE = True
except ImportError:
    REAL_LIBRARY_AVAILABLE = False

# Import our mock implementation
from .mock.mock_ws281x import PixelStrip as MockPixelStrip, Color as MockColor

def get_library() -> Tuple[Type[Any], Type[Any]]:
    """
    Returns the appropriate (PixelStrip, Color) implementation based on environment
    and availability.
    
    To force mock implementation: FORCE_MOCK_LEDS=1
    To force real implementation: FORCE_REAL_LEDS=1
    """
    force_mock = os.environ.get('FORCE_MOCK_LEDS') == '1'
    force_real = os.environ.get('FORCE_REAL_LEDS') == '1'
    
    if force_real and not REAL_LIBRARY_AVAILABLE:
        raise ImportError("Real LED library was forced but rpi_ws281x is not available")
        
    # Use mock if forced or if real library is not available
    if force_mock or not REAL_LIBRARY_AVAILABLE:
        print("Using mock LED implementation", file=sys.stderr)
        return MockPixelStrip, MockColor
        
    # Use real implementation
    print("Using real LED implementation", file=sys.stderr)
    return RealPixelStrip, RealColor

# Export the selected implementation
PixelStrip, Color = get_library() 