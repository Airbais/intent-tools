#!/usr/bin/env python3
"""
Test script for Rules Evaluator automation API integration
"""

import requests
import time
import json
import sys

API_BASE = "http://localhost:8888"

def test_rulesevaluator_api():
    """Test Rules Evaluator through automation API"""
    print("Testing Rules Evaluator Automation API...")
    
    # 1. Health check
    print("\n1. Testing health endpoint...")
    try:
        resp = requests.get(f"{API_BASE}/health")
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 2. List available tools
    print("\n2. Listing available tools...")
    try:
        resp = requests.get(f"{API_BASE}/tools")
        tools = resp.json()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool}")
        
        if 'rulesevaluator' not in tools:
            print("ERROR: Rules Evaluator not found in available tools")
            return
        
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 3. Get tool info
    print("\n3. Getting Rules Evaluator info...")
    try:
        resp = requests.get(f"{API_BASE}/tools/rulesevaluator")
        tool_info = resp.json()
        print(f"Tool info: {json.dumps(tool_info, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 4. Start Rules Evaluator job
    print("\n4. Starting Rules Evaluator analysis...")
    rules_file = sys.argv[1] if len(sys.argv) > 1 else "rules/example_rules.json"
    
    try:
        payload = {
            "rules_file": rules_file,
            "config": "config.yaml",
            "log_level": "INFO"
        }
        
        resp = requests.post(
            f"{API_BASE}/tools/rulesevaluator/run", 
            json=payload
        )
        
        if resp.status_code != 200:
            print(f"Error starting job: {resp.status_code} - {resp.text}")
            return
        
        job_info = resp.json()
        job_id = job_info['job_id']
        print(f"Started job: {job_id}")
        print(f"Job info: {json.dumps(job_info, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # 5. Monitor job progress
    print(f"\n5. Monitoring job {job_id}...")
    while True:
        try:
            resp = requests.get(f"{API_BASE}/jobs/{job_id}")
            job_status = resp.json()
            
            status = job_status['status']
            print(f"Job status: {status}")
            
            if status in ['completed', 'failed']:
                print(f"Final job info: {json.dumps(job_status, indent=2)}")
                break
            
            # Wait before next check
            time.sleep(5)
            
        except Exception as e:
            print(f"Error checking status: {e}")
            break
    
    # 6. Get results if completed
    if status == 'completed':
        print(f"\n6. Getting results for job {job_id}...")
        try:
            resp = requests.get(f"{API_BASE}/jobs/{job_id}/results")
            
            if resp.status_code == 200:
                results = resp.json()
                print("Results summary:")
                if 'overall_results' in results:
                    overall = results['overall_results']
                    print(f"  Total Prompts: {overall.get('total_prompts', 'N/A')}")
                    print(f"  Pass Rate: {overall.get('overall_pass_rate', 'N/A')}%")
                    print(f"  Average Score: {overall.get('average_score', 'N/A')}")
                    print(f"  Critical Failures: {overall.get('critical_failures', 'N/A')}")
                else:
                    print("  Results format unexpected")
            else:
                print(f"Error getting results: {resp.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Job failed with status: {status}")
    
    print("\nRules Evaluator API test complete!")


if __name__ == "__main__":
    test_rulesevaluator_api()