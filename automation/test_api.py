#!/usr/bin/env python3
"""
Simple test script for the Airbais automation API
"""

import requests
import time
import json
import sys

API_BASE = "http://localhost:8888"

def test_api():
    print("Testing Airbais Automation API...")
    
    # 1. Health check
    print("\n1. Testing health endpoint...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 2. Start analysis
    print("\n2. Starting IntentCrawler analysis...")
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    
    try:
        resp = requests.post(
            f"{API_BASE}/intentcrawler/analyze",
            json={"url": test_url}
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code != 202:
            print("Failed to start analysis")
            return
            
        job_id = resp.json().get('job_id')
        if not job_id:
            print("No job_id in response")
            return
            
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 3. Check status
    print(f"\n3. Checking status for job {job_id}...")
    
    for i in range(10):  # Check for up to 100 seconds
        time.sleep(10)
        
        try:
            resp = requests.get(f"{API_BASE}/status/{job_id}")
            print(f"\nAttempt {i+1}:")
            print(f"Status: {resp.status_code}")
            print(f"Response: {json.dumps(resp.json(), indent=2)}")
            
            if resp.status_code == 200:
                status = resp.json().get('status')
                if status == 'completed':
                    print("\nAnalysis completed!")
                    break
                elif status == 'failed':
                    print("\nAnalysis failed!")
                    print(f"Error: {resp.json().get('error')}")
                    break
            else:
                print(f"Error getting status: {resp.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # 4. Get results if completed
    if status == 'completed':
        print(f"\n4. Getting results for job {job_id}...")
        try:
            resp = requests.get(f"{API_BASE}/results/{job_id}")
            print(f"Status: {resp.status_code}")
            print(f"Response: {json.dumps(resp.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {e}")
    
    # 5. List all jobs
    print("\n5. Listing all jobs...")
    try:
        resp = requests.get(f"{API_BASE}/jobs")
        print(f"Status: {resp.status_code}")
        print(f"Number of jobs: {len(resp.json())}")
        for job in resp.json()[:5]:  # Show first 5
            print(f"  - {job['id']}: {job['tool']} - {job['status']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()