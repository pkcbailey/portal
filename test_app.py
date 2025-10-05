#!/usr/bin/env python3
"""
Test script to verify the IT Inventory Dashboard is working correctly
"""

import requests
import json
import time

def test_api_endpoints():
    """Test all API endpoints"""
    base_url = "http://localhost:5001/api"
    
    endpoints = [
        "summary",
        "business-units", 
        "systems",
        "systems/issues"
    ]
    
    print("🧪 Testing API endpoints...")
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}/{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: OK ({len(str(data))} chars)")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: {e}")
    
    # Test business unit details
    try:
        response = requests.get(f"{base_url}/business-units/CTIO", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ business-units/CTIO: OK ({len(data.get('systems', []))} systems)")
        else:
            print(f"❌ business-units/CTIO: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ business-units/CTIO: {e}")

def test_streamlit():
    """Test if Streamlit is accessible"""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit: OK")
        else:
            print(f"❌ Streamlit: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Streamlit: {e}")

def main():
    print("🚀 IT Inventory Dashboard Test")
    print("=" * 40)
    
    # Wait a moment for servers to start
    print("⏳ Waiting for servers to start...")
    time.sleep(2)
    
    # Test API
    test_api_endpoints()
    print()
    
    # Test Streamlit
    test_streamlit()
    print()
    
    print("🎯 Test completed!")
    print("📊 Dashboard: http://localhost:8501")
    print("🔌 API: http://localhost:5001")

if __name__ == "__main__":
    main()
