#!/usr/bin/env python3

import os
import sys
import json
import yaml
import subprocess
import threading
import uuid
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
import logging
import traceback

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), 'tools_config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {'tools': {}, 'server': {'port': 8888, 'host': '0.0.0.0'}}

# Load configuration
config = load_config()
TOOL_CONFIGS = config.get('tools', {})
SERVER_CONFIG = config.get('server', {})
TIMEOUT_CONFIG = config.get('timeouts', {})

app = Flask(__name__)
if SERVER_CONFIG.get('cors_enabled', True):
    CORS(app)  # Enable CORS for N8N

# Job storage (in production, use Redis or database)
jobs = {}  # Changed from defaultdict(dict) to regular dict
job_lock = threading.Lock()

def create_job(tool_name):
    """Create a new job entry"""
    job_id = str(uuid.uuid4())
    with job_lock:
        jobs[job_id] = {
            'id': job_id,
            'tool': tool_name,
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'completed_at': None,
            'error': None,
            'results': None,
            'logs': []
        }
    logger.info(f"Created job {job_id} for tool {tool_name}")
    logger.debug(f"Current jobs: {list(jobs.keys())}")
    return job_id

def update_job(job_id, updates):
    """Update job status"""
    with job_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)
            jobs[job_id]['updated_at'] = datetime.now().isoformat()

def get_job(job_id):
    """Get job details"""
    with job_lock:
        return jobs.get(job_id)

def run_tool_async(job_id, tool_name, params):
    """Run tool in background thread"""
    try:
        update_job(job_id, {'status': 'running'})
        
        tool_config = TOOL_CONFIGS.get(tool_name)
        if not tool_config:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Build paths
        tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tool_dir = os.path.join(tools_dir, tool_config['module_path'])
        tool_script = tool_config['script']
        
        # Use relative script name and run from tool's directory
        cmd = ['python3', tool_script]
        
        # Add tool-specific parameters based on config
        tool_params = tool_config.get('required_params', []) + tool_config.get('optional_params', [])
        param_style = tool_config.get('param_style', 'flags')  # Default to flags style
        
        # Handle parameters based on style
        if param_style == 'positional':
            # URL is a positional argument (like intentcrawler)
            if 'url' in params:
                cmd.append(params['url'])
            # Handle optional parameters with -- prefix
            for param in tool_config.get('optional_params', []):
                if param in params:
                    cmd.extend([f'--{param.replace("_", "-")}', str(params[param])])
        elif param_style == 'config_file':
            # Config file is a positional argument (like llmevaluator)
            if 'config' in params:
                cmd.append(params['config'])
            # Handle optional parameters with -- prefix
            for param in tool_config.get('optional_params', []):
                if param in params:
                    # Special handling for boolean flags
                    if param in ['no_cache', 'clear_cache', 'dry_run', 'dashboard']:
                        if params[param]:  # Only add flag if True
                            cmd.append(f'--{param.replace("_", "-")}')
                    else:
                        cmd.extend([f'--{param.replace("_", "-")}', str(params[param])])
        else:
            # All parameters use flags (default style)
            # Handle required parameters
            for param in tool_config.get('required_params', []):
                if param in params:
                    cmd.extend([f'--{param.replace("_", "-")}', str(params[param])])
            
            # Handle optional parameters
            for param in tool_config.get('optional_params', []):
                if param in params:
                    # Special handling for output directory parameter
                    if param == 'output' and tool_name == 'geoevaluator':
                        cmd.extend(['--output-dir', str(params[param])])
                    else:
                        cmd.extend([f'--{param.replace("_", "-")}', str(params[param])])
        
        logger.info(f"Running command: {' '.join(cmd)} in directory: {tool_dir}")
        
        # Run the tool in its own directory
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tool_dir
        )
        
        # Capture output
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Tool execution failed: {stderr}")
        
        # Parse output to find results directory
        results_dir = None
        for line in stdout.split('\n'):
            if 'Results saved to:' in line:
                results_dir = line.split('Results saved to:')[1].strip()
                break
        
        if not results_dir:
            # Try to find the latest results directory in the tool's directory
            base_dir = os.path.join(tool_dir, 'results')
            if os.path.exists(base_dir):
                dirs = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))], reverse=True)
                if dirs:
                    results_dir = os.path.join(base_dir, dirs[0])
        
        if not results_dir or not os.path.exists(results_dir):
            raise Exception("Could not find results directory")
        
        # Collect results
        results = {
            'output_directory': results_dir,
            'files': {},
            'metrics': {}
        }
        
        # Check for result files
        for file_name in tool_config.get('result_files', []):
            file_path = os.path.join(results_dir, file_name)
            if os.path.exists(file_path):
                results['files'][file_name.replace('.json', '').replace('.md', '').replace('-', '_')] = file_path
                
                # Extract metrics from dashboard data if available
                if file_name == 'dashboard-data.json':
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            results['metrics'] = {
                                'pages_analyzed': data.get('total_pages_analyzed', 0),
                                'intents_discovered': data.get('total_intents', 0),
                                'processing_time_seconds': None  # Would need to track this
                            }
                    except:
                        pass
        
        update_job(job_id, {
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        logger.error(traceback.format_exc())
        update_job(job_id, {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tools': list(TOOL_CONFIGS.keys()),
        'active_jobs': len(jobs)
    })

@app.route('/<tool_name>/analyze', methods=['POST'])
def analyze(tool_name):
    """Start analysis for a specific tool"""
    if tool_name not in TOOL_CONFIGS:
        return jsonify({
            'error': f'Unknown tool: {tool_name}',
            'available_tools': list(TOOL_CONFIGS.keys())
        }), 404
    
    try:
        params = request.get_json() or {}
        
        # Validate required parameters based on config
        required_params = TOOL_CONFIGS[tool_name].get('required_params', [])
        missing_params = [p for p in required_params if p not in params]
        if missing_params:
            return jsonify({
                'error': f'Missing required parameters: {", ".join(missing_params)}',
                'required': required_params,
                'optional': TOOL_CONFIGS[tool_name].get('optional_params', [])
            }), 400
        
        # Create job
        job_id = create_job(tool_name)
        
        # Verify job was created
        logger.info(f"Created job {job_id}, verifying...")
        test_job = get_job(job_id)
        if not test_job:
            logger.error(f"Job {job_id} not found immediately after creation!")
            return jsonify({'error': 'Failed to create job'}), 500
        
        # Start analysis in background
        thread = threading.Thread(
            target=run_tool_async,
            args=(job_id, tool_name, params)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': f'{TOOL_CONFIGS[tool_name]["name"]} analysis started'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': 'Failed to start analysis'}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status"""
    # Clean up job_id - remove any trailing special characters
    original_id = job_id
    # Remove any non-alphanumeric characters from the end (except hyphens)
    job_id = re.sub(r'[^a-zA-Z0-9\-]+$', '', job_id).strip()
    
    if original_id != job_id:
        logger.info(f"Cleaned job_id from '{original_id}' to '{job_id}'")
    
    logger.info(f"Status request for job: {job_id}")
    logger.debug(f"Available jobs: {list(jobs.keys())}")
    
    job = get_job(job_id)
    if not job:
        logger.warning(f"Job {job_id} not found in {len(jobs)} jobs")
        return jsonify({
            'error': 'Job not found',
            'requested_id': original_id,
            'cleaned_id': job_id,
            'available_jobs': list(jobs.keys())
        }), 404
    
    response = {
        'job_id': job['id'],
        'tool': job['tool'],
        'status': job['status'],
        'created_at': job['created_at'],
        'updated_at': job['updated_at'],
        'completed_at': job['completed_at']
    }
    
    if job['status'] == 'failed':
        response['error'] = job['error']
    
    return jsonify(response)

@app.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get job results"""
    # Clean up job_id - remove any trailing special characters
    original_id = job_id
    job_id = re.sub(r'[^a-zA-Z0-9\-]+$', '', job_id).strip()
    
    if original_id != job_id:
        logger.info(f"Cleaned job_id from '{original_id}' to '{job_id}'")
    
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found', 'cleaned_id': job_id}), 404
    
    if job['status'] != 'completed':
        return jsonify({
            'error': f'Job not completed. Current status: {job["status"]}'
        }), 400
    
    return jsonify({
        'job_id': job['id'],
        'tool': job['tool'],
        'status': job['status'],
        'created_at': job['created_at'],
        'completed_at': job['completed_at'],
        'results': job['results']
    })

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (optional - useful for debugging)"""
    with job_lock:
        job_list = list(jobs.values())
    
    # Sort by creation time, newest first
    job_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Limit to last 100 jobs
    return jsonify(job_list[:100])

if __name__ == '__main__':
    port = SERVER_CONFIG.get('port', 8888)
    host = SERVER_CONFIG.get('host', '0.0.0.0')
    debug = SERVER_CONFIG.get('debug', False)
    
    logger.info(f"Starting Airbais Tools Automation API on {host}:{port}")
    logger.info(f"Available tools: {', '.join(TOOL_CONFIGS.keys())}")
    
    app.run(host=host, port=port, debug=debug)