"""
Performance monitoring and debug logging system for LED components.
Provides timing decorators, profiling tools, and comprehensive logging.
"""

import time
import functools
import logging
import json
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics


@dataclass
class PerformanceMetric:
    """Stores performance data for a single operation"""
    name: str
    duration_ms: float
    timestamp: float
    thread_id: int
    memory_usage_mb: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None


class PerformanceProfiler:
    """
    Comprehensive performance profiler for LED operations.
    Tracks timing, memory usage, and provides statistics.
    """
    
    def __init__(self, max_history: int = 10000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.active_timers: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.enabled = True
        
        # Setup logging
        self.logger = logging.getLogger("led_performance")
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler for performance logs
        log_path = Path.home() / ".led_performance.log"
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler for important metrics
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def start_timer(self, name: str) -> None:
        """Start timing an operation"""
        if not self.enabled:
            return
            
        with self.lock:
            self.active_timers[name] = time.perf_counter()
            
    def end_timer(self, name: str, additional_data: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and record the metric"""
        if not self.enabled:
            return 0.0
            
        end_time = time.perf_counter()
        
        with self.lock:
            start_time = self.active_timers.pop(name, end_time)
            duration_ms = (end_time - start_time) * 1000
            
            metric = PerformanceMetric(
                name=name,
                duration_ms=duration_ms,
                timestamp=time.time(),
                thread_id=threading.get_ident(),
                additional_data=additional_data
            )
            
            self.metrics[name].append(metric)
            
            # Log the metric
            self.logger.debug(f"{name}: {duration_ms:.2f}ms")
            
            # Log warning for slow operations
            if duration_ms > 50:  # More than 50ms
                self.logger.warning(f"SLOW OPERATION: {name}: {duration_ms:.2f}ms")
                
            return duration_ms
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a specific operation"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
            
        durations = [m.duration_ms for m in self.metrics[name]]
        
        return {
            "count": len(durations),
            "avg_ms": statistics.mean(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "median_ms": statistics.median(durations),
            "std_dev_ms": statistics.stdev(durations) if len(durations) > 1 else 0.0,
            "total_ms": sum(durations)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all tracked operations"""
        return {name: self.get_stats(name) for name in self.metrics.keys()}
    
    def dump_to_file(self, filepath: Optional[Path] = None) -> None:
        """Dump all performance data to a JSON file"""
        if filepath is None:
            filepath = Path.home() / ".led_performance_dump.json"
            
        data = {
            "stats": self.get_all_stats(),
            "raw_metrics": {
                name: [asdict(m) for m in metrics]
                for name, metrics in self.metrics.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        self.logger.info(f"Performance data dumped to {filepath}")
    
    def log_summary(self) -> None:
        """Log a summary of all performance statistics"""
        stats = self.get_all_stats()
        
        self.logger.info("=== PERFORMANCE SUMMARY ===")
        for name, stat in sorted(stats.items(), key=lambda x: x[1].get('avg_ms', 0), reverse=True):
            if stat.get('count', 0) > 0:
                self.logger.info(
                    f"{name}: avg={stat['avg_ms']:.2f}ms, "
                    f"count={stat['count']}, "
                    f"total={stat['total_ms']:.2f}ms, "
                    f"max={stat['max_ms']:.2f}ms"
                )
    
    def reset(self) -> None:
        """Clear all performance data"""
        with self.lock:
            self.metrics.clear()
            self.active_timers.clear()
        self.logger.info("Performance data reset")


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance"""
    return _profiler


def profile_function(name: Optional[str] = None, log_args: bool = False):
    """
    Decorator to profile function execution time.
    
    Args:
        name: Custom name for the operation (defaults to function name)
        log_args: Whether to log function arguments
    """
    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            additional_data = {}
            if log_args:
                additional_data["args_count"] = len(args)
                additional_data["kwargs_keys"] = list(kwargs.keys())
            
            _profiler.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                _profiler.end_timer(operation_name, additional_data)
        
        return wrapper
    return decorator


def profile_block(name: str):
    """
    Context manager to profile a block of code.
    
    Usage:
        with profile_block("my_operation"):
            # code to profile
            pass
    """
    class ProfileBlock:
        def __enter__(self):
            _profiler.start_timer(name)
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            _profiler.end_timer(name)
    
    return ProfileBlock()


def log_performance_summary():
    """Log and dump performance summary"""
    _profiler.log_summary()
    _profiler.dump_to_file()


def reset_performance_data():
    """Reset all performance tracking data"""
    _profiler.reset()


def enable_profiling(enabled: bool = True):
    """Enable or disable performance profiling"""
    _profiler.enabled = enabled
    _profiler.logger.info(f"Performance profiling {'enabled' if enabled else 'disabled'}")
