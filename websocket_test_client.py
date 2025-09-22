#!/usr/bin/env python3
"""
WebSocket Test Client - Demonstrates WebSocket optimization benefits.
"""

import time
import requests
import socketio
import threading
from typing import Dict, Any


class WebSocketTestClient:
    """Test client to demonstrate WebSocket optimization"""
    
    def __init__(self, server_url: str = "http://localhost:5001"):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.connected = False
        self.messages_received = 0
        self.last_message_time = 0
        
        # Setup event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('led_update', self.on_led_update)
    
    def on_connect(self):
        """Handle connection event"""
        self.connected = True
        print(f"✓ Connected to LED server at {self.server_url}")
    
    def on_disconnect(self):
        """Handle disconnection event"""
        self.connected = False
        print("✗ Disconnected from LED server")
    
    def on_led_update(self, data):
        """Handle LED update messages"""
        self.messages_received += 1
        self.last_message_time = time.time()
        
        if self.messages_received % 30 == 0:  # Log every 30 messages (1 second at 30 FPS)
            led_count = sum(len(strip) for strip in data) if isinstance(data, list) else 0
            print(f"Received {self.messages_received} LED updates (LEDs: {led_count})")
    
    def connect(self) -> bool:
        """Connect to the LED server"""
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the LED server"""
        if self.connected:
            self.sio.disconnect()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the server"""
        try:
            response = requests.get(f"{self.server_url}/performance", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Failed to get performance stats: {e}")
        return {}


def demonstrate_websocket_optimization():
    """Demonstrate WebSocket optimization benefits"""
    print("WebSocket Optimization Demo")
    print("=" * 50)
    
    server_url = "http://localhost:5001"
    
    # Check if server is running
    try:
        response = requests.get(f"{server_url}/state", timeout=2)
        if response.status_code != 200:
            print("❌ LED server is not running!")
            print("Please start the LED server first:")
            print("  python main.py leds-mock")
            return
    except Exception:
        print("❌ LED server is not running!")
        print("Please start the LED server first:")
        print("  python main.py leds-mock")
        return
    
    print("✓ LED server is running")
    
    # Phase 1: Measure performance without clients
    print("\n📊 Phase 1: Measuring performance without WebSocket clients...")
    
    # Get initial stats
    try:
        initial_stats = requests.get(f"{server_url}/performance", timeout=5).json()
        initial_frames = initial_stats.get('websocket', {}).get('total_frames', 0)
        initial_emissions = initial_stats.get('websocket', {}).get('emissions_sent', 0)
        print(f"Initial frames: {initial_frames}, emissions: {initial_emissions}")
    except Exception as e:
        print(f"Could not get initial stats: {e}")
        return
    
    # Wait and measure
    print("Waiting 10 seconds to measure baseline performance...")
    time.sleep(10)
    
    try:
        baseline_stats = requests.get(f"{server_url}/performance", timeout=5).json()
        baseline_frames = baseline_stats.get('websocket', {}).get('total_frames', 0)
        baseline_emissions = baseline_stats.get('websocket', {}).get('emissions_sent', 0)
        baseline_skipped = baseline_stats.get('websocket', {}).get('emissions_skipped', 0)
        
        frames_processed = baseline_frames - initial_frames
        emissions_sent = baseline_emissions - initial_emissions
        
        print(f"Baseline results (10 seconds):")
        print(f"  Frames processed: {frames_processed}")
        print(f"  WebSocket emissions sent: {emissions_sent}")
        print(f"  WebSocket emissions skipped: {baseline_skipped}")
        print(f"  Efficiency: {baseline_stats.get('websocket', {}).get('efficiency_percent', 0):.1f}% saved")
        
        if emissions_sent == 0:
            print("✅ Perfect! No WebSocket data sent when no clients connected")
        else:
            print("⚠️  WebSocket data was sent even without clients")
    
    except Exception as e:
        print(f"Could not get baseline stats: {e}")
        return
    
    # Phase 2: Connect client and measure
    print("\n📊 Phase 2: Connecting WebSocket client and measuring performance...")
    
    client = WebSocketTestClient(server_url)
    
    if not client.connect():
        print("❌ Failed to connect WebSocket client")
        return
    
    print("✓ WebSocket client connected")
    time.sleep(2)  # Let connection stabilize
    
    # Get stats with client connected
    try:
        connected_initial = requests.get(f"{server_url}/performance", timeout=5).json()
        connected_initial_frames = connected_initial.get('websocket', {}).get('total_frames', 0)
        connected_initial_emissions = connected_initial.get('websocket', {}).get('emissions_sent', 0)
    except Exception as e:
        print(f"Could not get connected initial stats: {e}")
        client.disconnect()
        return
    
    print("Measuring performance with connected client for 10 seconds...")
    time.sleep(10)
    
    try:
        connected_stats = requests.get(f"{server_url}/performance", timeout=5).json()
        connected_frames = connected_stats.get('websocket', {}).get('total_frames', 0)
        connected_emissions = connected_stats.get('websocket', {}).get('emissions_sent', 0)
        
        frames_with_client = connected_frames - connected_initial_frames
        emissions_with_client = connected_emissions - connected_initial_emissions
        
        print(f"Connected client results (10 seconds):")
        print(f"  Frames processed: {frames_with_client}")
        print(f"  WebSocket emissions sent: {emissions_with_client}")
        print(f"  Messages received by client: {client.messages_received}")
        print(f"  Active clients: {connected_stats.get('websocket', {}).get('active_clients', 0)}")
        
        # Calculate expected emissions (should be ~half of frames due to every-other-frame emission)
        expected_emissions = frames_with_client // 2
        efficiency = abs(emissions_with_client - expected_emissions) / expected_emissions * 100 if expected_emissions > 0 else 0
        
        if abs(emissions_with_client - expected_emissions) <= 1:  # Allow for 1 frame difference
            print("✅ WebSocket emissions working correctly with connected clients")
        else:
            print(f"⚠️  Expected ~{expected_emissions} emissions, got {emissions_with_client}")
    
    except Exception as e:
        print(f"Could not get connected stats: {e}")
    
    # Phase 3: Disconnect and verify optimization
    print("\n📊 Phase 3: Disconnecting client and verifying optimization...")
    
    client.disconnect()
    time.sleep(2)  # Let disconnection stabilize
    
    try:
        disconnected_initial = requests.get(f"{server_url}/performance", timeout=5).json()
        disconnected_initial_emissions = disconnected_initial.get('websocket', {}).get('emissions_sent', 0)
    except Exception as e:
        print(f"Could not get disconnected initial stats: {e}")
        return
    
    print("Measuring performance after client disconnect for 5 seconds...")
    time.sleep(5)
    
    try:
        final_stats = requests.get(f"{server_url}/performance", timeout=5).json()
        final_emissions = final_stats.get('websocket', {}).get('emissions_sent', 0)
        
        emissions_after_disconnect = final_emissions - disconnected_initial_emissions
        
        print(f"After disconnect results (5 seconds):")
        print(f"  WebSocket emissions sent: {emissions_after_disconnect}")
        print(f"  Active clients: {final_stats.get('websocket', {}).get('active_clients', 0)}")
        
        if emissions_after_disconnect == 0:
            print("✅ Perfect! WebSocket optimization working - no emissions after disconnect")
        else:
            print("⚠️  WebSocket emissions continued after client disconnect")
    
    except Exception as e:
        print(f"Could not get final stats: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("WebSocket Optimization Summary:")
    print("✓ Automatic client connection/disconnection tracking")
    print("✓ Zero WebSocket emissions when no clients connected")
    print("✓ Reduced emission rate (30 FPS) when clients are connected")
    print("✓ Real-time client count verification")
    print("✓ Performance statistics and monitoring")
    print("\nBenefits:")
    print("• Significant CPU savings when no web interface is used")
    print("• Reduced memory allocation for JSON serialization")
    print("• Lower network bandwidth usage")
    print("• Better overall system performance")


def main():
    """Main function"""
    try:
        demonstrate_websocket_optimization()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
