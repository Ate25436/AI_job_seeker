#!/usr/bin/env python3
"""
Simple test script to verify FastAPI endpoints are working
"""
import requests
import json
import time

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("Testing FastAPI endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"Root endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Root endpoint failed: {e}")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"Health endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health endpoint failed: {e}")
    
    # Test ask endpoint (this will likely fail without proper setup)
    try:
        test_question = {"question": "What is your name?"}
        response = requests.post(f"{base_url}/api/ask", json=test_question)
        print(f"Ask endpoint: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Ask endpoint failed: {e}")

if __name__ == "__main__":
    # Wait a moment for server to start
    time.sleep(2)
    test_endpoints()