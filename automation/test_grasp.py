#!/usr/bin/env python3
"""
Test script for GRASP evaluator API endpoint
"""

import requests
import time
import json
import sys

API_BASE = "http://localhost:8888"

def test_grasp_api():
    print("Testing GRASP Evaluator API endpoint...")
    
    # 1. Health check
    print("\n1. Testing health endpoint...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Available tools: {data.get('tools', [])}")
        
        if 'graspevaluator' not in data.get('tools', []):
            print("❌ GRASP evaluator not found in available tools!")
            return
        else:
            print("✅ GRASP evaluator found in available tools")
            
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 2. Start GRASP analysis
    print("\n2. Starting GRASP Evaluator analysis...")
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    
    try:
        resp = requests.post(
            f"{API_BASE}/graspevaluator/analyze",
            json={"url": test_url}
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code != 202:
            print("❌ Failed to start GRASP analysis")
            return
            
        job_id = resp.json().get('job_id')
        if not job_id:
            print("❌ No job_id in response")
            return
        else:
            print(f"✅ Job started with ID: {job_id}")
            
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 3. Monitor status
    print(f"\n3. Monitoring GRASP evaluation job {job_id}...")
    
    for i in range(20):  # Check for up to 200 seconds
        time.sleep(10)
        
        try:
            resp = requests.get(f"{API_BASE}/status/{job_id}")
            print(f"\nCheck {i+1}/20:")
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                status = data.get('status')
                print(f"Job status: {status}")
                
                if status == 'completed':
                    print("✅ GRASP evaluation completed!")
                    break
                elif status == 'failed':
                    print("❌ GRASP evaluation failed!")
                    print(f"Error: {data.get('error')}")
                    return
            else:
                print(f"❌ Error getting status: {resp.status_code}")
                print(f"Response: {resp.json()}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        print("⏰ Timeout waiting for completion")
        return
    
    # 4. Get results
    print(f"\n4. Getting GRASP evaluation results...")
    try:
        resp = requests.get(f"{API_BASE}/results/{job_id}")
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', {})
            print(f"✅ Results retrieved!")
            print(f"Output directory: {results.get('output_directory')}")
            print(f"Files: {list(results.get('files', {}).keys())}")
            print(f"Metrics: {results.get('metrics', {})}")
        else:
            print(f"❌ Error getting results: {resp.status_code}")
            print(f"Response: {resp.json()}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_grasp_api()