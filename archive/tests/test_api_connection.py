#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script for development API server"""

import requests
import time
import json

BASE_URL = "http://localhost:8001"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Health Check Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"\nRoot Endpoint Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root endpoint failed: {e}")
        return False

def test_collections():
    """Test collections endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/collections", timeout=10)
        print(f"\nCollections Status: {response.status_code}")
        if response.status_code == 200:
            collections = response.json()
            print(f"Collections: {collections}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Collections endpoint failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Development API Server (Port 8001)...")
    print("=" * 50)
    
    # Wait a bit for server to be ready
    print("Waiting for server to be ready...")
    for i in range(10):
        if test_health():
            break
        time.sleep(3)
        print(f"Retry {i+1}/10...")
    
    print("\n" + "=" * 50)
    test_root()
    print("\n" + "=" * 50)
    test_collections()

