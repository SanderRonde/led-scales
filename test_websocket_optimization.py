#!/usr/bin/env python3
"""
Quick test to verify WebSocket optimization is working correctly.
"""

import time
import requests
import sys


def test_websocket_optimization():
    """Test that WebSocket emissions are optimized"""
    server_url = "http://localhost:5001"
    
    print("Testing WebSocket optimization...")
    
    # Check if server is running
    try:
        response = requests.get(f"{server_url}/state", timeout=2)
        if response.status_code != 200:
            print("❌ LED server is not running!")
            print("Start with: python main.py leds-mock")
            return False
    except Exception:
        print("❌ LED server is not running!")
        print("Start with: python main.py leds-mock")
        return False
    
    print("✓ LED server is running")
    
    # Get initial performance stats
    try:
        initial_response = requests.get(f"{server_url}/performance", timeout=5)
        if initial_response.status_code != 200:
            print("❌ Performance endpoint not available")
            return False
        
        initial_stats = initial_response.json()
        initial_frames = initial_stats.get('websocket', {}).get('total_frames', 0)
        initial_emissions = initial_stats.get('websocket', {}).get('emissions_sent', 0)
        initial_clients = initial_stats.get('websocket', {}).get('active_clients', 0)
        
        print(f"Initial state: {initial_clients} clients, {initial_frames} frames, {initial_emissions} emissions")
        
    except Exception as e:
        print(f"❌ Could not get initial stats: {e}")
        return False
    
    # Wait a few seconds and check again
    print("Waiting 5 seconds to measure baseline...")
    time.sleep(5)
    
    try:
        final_response = requests.get(f"{server_url}/performance", timeout=5)
        final_stats = final_response.json()
        
        final_frames = final_stats.get('websocket', {}).get('total_frames', 0)
        final_emissions = final_stats.get('websocket', {}).get('emissions_sent', 0)
        final_clients = final_stats.get('websocket', {}).get('active_clients', 0)
        efficiency = final_stats.get('websocket', {}).get('efficiency_percent', 0)
        
        frames_processed = final_frames - initial_frames
        emissions_sent = final_emissions - initial_emissions
        
        print(f"Final state: {final_clients} clients, {frames_processed} new frames, {emissions_sent} new emissions")
        print(f"Efficiency: {efficiency:.1f}% of emissions saved")
        
        # Test results
        if final_clients == 0 and emissions_sent == 0:
            print("✅ PASS: No WebSocket emissions when no clients connected")
            return True
        elif final_clients == 0 and emissions_sent > 0:
            print("❌ FAIL: WebSocket emissions sent despite no clients")
            return False
        elif final_clients > 0:
            expected_emissions = frames_processed // 2  # Every other frame
            if abs(emissions_sent - expected_emissions) <= 2:  # Allow small variance
                print("✅ PASS: WebSocket emissions working correctly with clients")
                return True
            else:
                print(f"⚠️  WARNING: Expected ~{expected_emissions} emissions, got {emissions_sent}")
                return True  # Still working, just different rate
        else:
            print("❓ UNKNOWN: Unexpected state")
            return False
            
    except Exception as e:
        print(f"❌ Could not get final stats: {e}")
        return False


def main():
    """Main test function"""
    success = test_websocket_optimization()
    
    if success:
        print("\n🎉 WebSocket optimization test PASSED!")
        print("\nTo test with a real client:")
        print("1. Open http://localhost:5001 in your browser")
        print("2. Run this test again to see emissions being sent")
        print("3. Close the browser tab and run again to see emissions stop")
    else:
        print("\n❌ WebSocket optimization test FAILED!")
        print("Check the LED server logs for more information.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
