#!/usr/bin/env python3
"""
Test script for LLM evaluator API endpoint
"""

import requests
import time
import json
import sys
import os

API_BASE = "http://localhost:8888"

def test_llm_api():
    print("Testing LLM Evaluator API endpoint...")
    
    # 1. Health check
    print("\n1. Testing health endpoint...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Available tools: {data.get('tools', [])}")
        
        if 'llmevaluator' not in data.get('tools', []):
            print("❌ LLM evaluator not found in available tools!")
            return
        else:
            print("✅ LLM evaluator found in available tools")
            
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 2. Start LLM evaluation
    print("\n2. Starting LLM Evaluator analysis...")
    
    # Use provided config file path or default example
    config_file = sys.argv[1] if len(sys.argv) > 1 else "example_config.md"
    
    # Check if config file exists (relative to llmevaluator directory)
    llm_dir = "/home/bill/Pardicloud/Projects/Airbais/tools/llmevaluator"
    full_config_path = os.path.join(llm_dir, config_file)
    
    if not os.path.exists(full_config_path):
        print(f"❌ Config file not found: {full_config_path}")
        print("Available config files in llmevaluator directory:")
        for f in os.listdir(llm_dir):
            if f.endswith('.md') or f.endswith('.yaml'):
                print(f"  - {f}")
        return
    
    try:
        resp = requests.post(
            f"{API_BASE}/llmevaluator/analyze",
            json={
                "config": config_file,
                "dry_run": False,
                "log_level": "INFO"
            }
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code != 202:
            print("❌ Failed to start LLM evaluation")
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
    print(f"\n3. Monitoring LLM evaluation job {job_id}...")
    print("Note: LLM evaluation can take several minutes as it queries multiple models...")
    
    for i in range(60):  # Check for up to 600 seconds (10 minutes)
        time.sleep(10)
        
        try:
            resp = requests.get(f"{API_BASE}/status/{job_id}")
            print(f"\nCheck {i+1}/60:")
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                status = data.get('status')
                print(f"Job status: {status}")
                
                if status == 'completed':
                    print("✅ LLM evaluation completed!")
                    break
                elif status == 'failed':
                    print("❌ LLM evaluation failed!")
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
    print(f"\n4. Getting LLM evaluation results...")
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
    if len(sys.argv) < 2:
        print("Usage: python test_llm.py <config_file>")
        print("Example: python test_llm.py example_config.md")
        print("Note: Config file should be relative to llmevaluator directory")
        sys.exit(1)
    
    test_llm_api()