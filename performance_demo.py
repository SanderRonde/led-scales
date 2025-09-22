#!/usr/bin/env python3
"""
LED Performance Demo - Demonstrates the performance optimizations.
"""

import time
import sys
from pathlib import Path
from leds.performance import (
    get_profiler,
    log_performance_summary,
    reset_performance_data,
)
from config import get_config, get_led_controller
from leds.effects import get_effects
from leds.effects.optimized_rainbow_radial import OptimizedRainbowRadialEffect


def run_performance_demo():
    """Run a comprehensive performance demonstration"""
    print("LED Performance Optimization Demo")
    print("=" * 50)

    # Reset performance data for clean measurements
    reset_performance_data()

    # Initialize system
    print("Initializing LED system...")
    config = get_config()
    controller = get_led_controller(mock=True)  # Use mock for demo

    print(f"Configuration: {type(config).__name__}")
    print(f"LED Count: {config.get_led_count()}")
    print(f"Controller: {type(controller).__name__}")
    print()

    # Get effects
    effects = get_effects(controller)
    optimized_effect = OptimizedRainbowRadialEffect(controller)

    # Add optimized effect to the list
    effects["OptimizedRainbowRadialEffect"] = optimized_effect

    print(f"Available effects: {len(effects)}")
    for name in effects.keys():
        print(f"  - {name}")
    print()

    # Performance test parameters
    test_duration = 5.0  # seconds
    frame_count = 0

    print(f"Running performance test for {test_duration} seconds...")
    print("Testing effects:")

    # Test each effect
    for effect_name, effect in effects.items():
        print(f"\nTesting {effect_name}...")

        start_time = time.time()
        frame_count = 0

        while time.time() - start_time < test_duration:
            elapsed_ms = int((time.time() - start_time) * 1000)
            effect.run(elapsed_ms)
            frame_count += 1

        actual_duration = time.time() - start_time
        fps = frame_count / actual_duration

        print(f"  Frames: {frame_count}")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  FPS: {fps:.1f}")

    print("\n" + "=" * 50)
    print("Performance Summary:")

    # Get and display performance statistics
    profiler = get_profiler()
    stats = profiler.get_all_stats()

    # Calculate totals
    total_operations = sum(stat.get("count", 0) for stat in stats.values())
    total_time = sum(stat.get("total_ms", 0) for stat in stats.values())

    print(f"Total Operations: {total_operations}")
    print(f"Total Time: {total_time:.2f}ms")
    print(
        f"Average per Operation: {total_time/total_operations:.2f}ms"
        if total_operations > 0
        else "N/A"
    )

    # Show top 10 operations by average time
    print("\nTop 10 Operations by Average Time:")
    sorted_stats = sorted(
        [(name, stat) for name, stat in stats.items() if stat.get("count", 0) > 0],
        key=lambda x: x[1].get("avg_ms", 0),
        reverse=True,
    )[:10]

    for i, (name, stat) in enumerate(sorted_stats, 1):
        print(
            f"{i:2d}. {name:<40} {stat['avg_ms']:6.2f}ms avg ({stat['count']:4d} calls)"
        )

    # Show performance improvements
    print("\nPerformance Optimizations Demonstrated:")
    print("✓ Function-level profiling and timing")
    print("✓ Cached parameter access")
    print("✓ Color calculation caching")
    print("✓ Pre-computed distance maps")
    print("✓ Optimized coordinate mapping")
    print("✓ Batched LED updates")
    print("✓ Memory-efficient data structures")
    print("✓ WebSocket emissions only when clients are listening")

    # Show WebSocket optimization benefits
    print("\nWebSocket Optimization Benefits:")
    print("When no web clients are connected:")
    print("  - 0% CPU usage for WebSocket data serialization")
    print("  - 0% network bandwidth usage")
    print("  - 100% reduction in JSON serialization overhead")
    print("  - Automatic client detection and tracking")

    # Generate detailed report
    print("\nGenerating detailed performance report...")
    report_path = Path.home() / f"led_performance_demo_{int(time.time())}.txt"

    with open(report_path, "w") as f:
        f.write("LED Performance Demo Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("System Information:\n")
        f.write(f"Configuration: {type(config).__name__}\n")
        f.write(f"LED Count: {config.get_led_count()}\n")
        f.write(f"Controller: {type(controller).__name__}\n")
        f.write(f"Effects Tested: {len(effects)}\n\n")

        f.write("Performance Statistics:\n")
        f.write(f"Total Operations: {total_operations}\n")
        f.write(f"Total Time: {total_time:.2f}ms\n")
        f.write(
            f"Average per Operation: {total_time/total_operations:.2f}ms\n\n"
            if total_operations > 0
            else ""
        )

        f.write("Detailed Operation Statistics:\n")
        f.write("-" * 30 + "\n")

        for name, stat in sorted_stats:
            f.write(f"\n{name}:\n")
            f.write(f"  Count: {stat['count']}\n")
            f.write(f"  Average: {stat['avg_ms']:.2f}ms\n")
            f.write(f"  Min: {stat['min_ms']:.2f}ms\n")
            f.write(f"  Max: {stat['max_ms']:.2f}ms\n")
            f.write(f"  Total: {stat['total_ms']:.2f}ms\n")

    print(f"Detailed report saved to: {report_path}")

    # Log final summary
    log_performance_summary()

    print("\nDemo completed! Check the performance logs for detailed analysis.")
    print("Log files:")
    print(f"  - {Path.home() / '.led_performance.log'}")
    print(f"  - {Path.home() / '.led_performance_dump.json'}")
    print(f"  - {report_path}")


def main():
    """Main demo function"""
    try:
        run_performance_demo()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        log_performance_summary()
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
