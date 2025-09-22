#!/usr/bin/env python3
"""
LED Performance Monitor - Real-time performance analysis and logging.
"""

import time
import threading
import signal
import sys
from pathlib import Path
from leds.performance import get_profiler, log_performance_summary, reset_performance_data
from config import get_config, get_led_controller


class PerformanceMonitor:
    """Real-time performance monitoring for LED system"""
    
    def __init__(self, mock: bool = True):
        self.config = get_config()
        self.controller = get_led_controller(mock)
        self.profiler = get_profiler()
        self.running = False
        self.monitor_thread = None
        self._led_system = None  # Will be set if monitoring a running LED system
        
    def start_monitoring(self, interval: float = 5.0):
        """Start performance monitoring with specified interval"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                time.sleep(interval)
                if self.running:
                    self._log_system_stats()
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.profiler.logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        self.profiler.logger.info("Performance monitoring stopped")
    
    def _log_system_stats(self):
        """Log current system performance statistics"""
        stats = self.profiler.get_all_stats()
        
        # Calculate overall performance metrics
        total_operations = sum(stat.get('count', 0) for stat in stats.values())
        total_time = sum(stat.get('total_ms', 0) for stat in stats.values())
        
        # Get WebSocket statistics if available
        ws_stats_msg = ""
        if hasattr(self, '_led_system') and hasattr(self._led_system, 'get_websocket_stats'):
            ws_stats = self._led_system.get_websocket_stats()
            ws_stats_msg = f", WS clients: {ws_stats['active_clients']}, emissions: {ws_stats['emissions_sent']}/{ws_stats['frame_count']}"
        
        self.profiler.logger.info(
            f"System Performance: {total_operations} operations, "
            f"{total_time:.2f}ms total, "
            f"{len(stats)} tracked operations{ws_stats_msg}"
        )
        
        # Log top 5 slowest operations
        slowest = sorted(
            [(name, stat) for name, stat in stats.items() if stat.get('count', 0) > 0],
            key=lambda x: x[1].get('avg_ms', 0),
            reverse=True
        )[:5]
        
        if slowest:
            self.profiler.logger.info("Top 5 slowest operations:")
            for name, stat in slowest:
                self.profiler.logger.info(
                    f"  {name}: {stat['avg_ms']:.2f}ms avg, "
                    f"{stat['count']} calls, {stat['max_ms']:.2f}ms max"
                )
    
    def generate_report(self, filepath: Path = None):
        """Generate a comprehensive performance report"""
        if filepath is None:
            filepath = Path.home() / f".led_performance_report_{int(time.time())}.txt"
        
        stats = self.profiler.get_all_stats()
        
        with open(filepath, 'w') as f:
            f.write("LED System Performance Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Configuration: {type(self.config).__name__}\n")
            f.write(f"LED Count: {self.config.get_led_count()}\n")
            f.write(f"Controller: {type(self.controller).__name__}\n")
            f.write(f"Mock Mode: {self.controller.is_mock}\n\n")
            
            # Overall statistics
            total_operations = sum(stat.get('count', 0) for stat in stats.values())
            total_time = sum(stat.get('total_ms', 0) for stat in stats.values())
            
            f.write("Overall Statistics:\n")
            f.write(f"  Total Operations: {total_operations}\n")
            f.write(f"  Total Time: {total_time:.2f}ms\n")
            f.write(f"  Average per Operation: {total_time/total_operations:.2f}ms\n" if total_operations > 0 else "")
            f.write(f"  Tracked Operations: {len(stats)}\n\n")
            
            # Detailed operation statistics
            f.write("Detailed Operation Statistics:\n")
            f.write("-" * 30 + "\n")
            
            sorted_stats = sorted(
                stats.items(),
                key=lambda x: x[1].get('avg_ms', 0),
                reverse=True
            )
            
            for name, stat in sorted_stats:
                if stat.get('count', 0) > 0:
                    f.write(f"\n{name}:\n")
                    f.write(f"  Count: {stat['count']}\n")
                    f.write(f"  Average: {stat['avg_ms']:.2f}ms\n")
                    f.write(f"  Min: {stat['min_ms']:.2f}ms\n")
                    f.write(f"  Max: {stat['max_ms']:.2f}ms\n")
                    f.write(f"  Median: {stat['median_ms']:.2f}ms\n")
                    f.write(f"  Std Dev: {stat['std_dev_ms']:.2f}ms\n")
                    f.write(f"  Total: {stat['total_ms']:.2f}ms\n")
        
        self.profiler.logger.info(f"Performance report generated: {filepath}")
        return filepath


def main():
    """Main performance monitoring script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LED Performance Monitor")
    parser.add_argument("--mock", action="store_true", help="Use mock LED controller")
    parser.add_argument("--interval", type=float, default=5.0, help="Monitoring interval in seconds")
    parser.add_argument("--duration", type=float, help="Monitoring duration in seconds (default: run until interrupted)")
    parser.add_argument("--report", action="store_true", help="Generate performance report on exit")
    parser.add_argument("--reset", action="store_true", help="Reset performance data before starting")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_performance_data()
        print("Performance data reset")
    
    monitor = PerformanceMonitor(mock=args.mock)
    
    def signal_handler(signum, frame):
        print("\nShutting down performance monitor...")
        monitor.stop_monitoring()
        
        if args.report:
            report_path = monitor.generate_report()
            print(f"Performance report saved to: {report_path}")
        
        log_performance_summary()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"Starting LED performance monitor (mock={args.mock})")
    print(f"Monitoring interval: {args.interval}s")
    print("Press Ctrl+C to stop and generate report")
    
    monitor.start_monitoring(args.interval)
    
    if args.duration:
        print(f"Running for {args.duration} seconds...")
        time.sleep(args.duration)
        signal_handler(signal.SIGTERM, None)
    else:
        # Run until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
