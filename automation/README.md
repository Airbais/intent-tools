# Airbais Tools Automation API

This API server provides HTTP endpoints for N8N workflows to interact with Airbais tools asynchronously.

## Installation

```bash
cd automation
pip install -r requirements.txt
```

## Running the Server

```bash
python api_server.py
```

The server will start on port 8888.

## API Endpoints

### Health Check
```
GET http://localhost:8888/health
```

### Intent Crawler Analysis

Start analysis:
```
POST http://localhost:8888/intentcrawler/analyze
Content-Type: application/json

{
  "url": "https://example.com"
}
```

### GRASP Evaluator Analysis

Start evaluation:
```
POST http://localhost:8888/graspevaluator/analyze
Content-Type: application/json

{
  "url": "https://example.com",
  "verbose": true
}
```

### GEO Evaluator Analysis

Start evaluation:
```
POST http://localhost:8888/geoevaluator/analyze
Content-Type: application/json

{
  "url": "https://example.com",
  "name": "Example Site",
  "max_pages": 50,
  "dashboard": true
}
```

### LLM Evaluator Analysis

Start evaluation:
```
POST http://localhost:8888/llmevaluator/analyze
Content-Type: application/json

{
  "config": "example_config.md",
  "log_level": "INFO",
  "dry_run": false
}
```

### Common Endpoints

Check status:
```
GET http://localhost:8888/status/{job_id}
```

Get results:
```
GET http://localhost:8888/results/{job_id}
```

## Common Issues

### Trailing Characters in Job IDs
If you're copying job IDs from terminal output, be careful not to include any trailing characters like backticks or quotes. The API will automatically clean common trailing special characters, but it's best to copy only the UUID itself.

## N8N Workflow Example
### NOTE: There are starter workflows in the workflows folder.

1. **HTTP Request Node** - Start Analysis
   - Method: POST
   - URL: `http://localhost:8888/intentcrawler/analyze`
   - Body: `{"url": "https://yoursite.com"}`
   - Store response in: `analysis_response`

2. **Wait Node** - 30 seconds

3. **HTTP Request Node** - Check Status
   - Method: GET
   - URL: `http://localhost:8888/status/{{$node["Start Analysis"].json["job_id"]}}`
   - Store response in: `status_response`

4. **IF Node** - Check if Complete
   - Condition: `{{$node["Check Status"].json["status"]}} == "completed"`

5. **HTTP Request Node** - Get Results
   - Method: GET  
   - URL: `http://localhost:8888/results/{{$node["Start Analysis"].json["job_id"]}}`
   - Store response in: `results_response`

6. **Read Binary Files Node** - Read Dashboard Data
   - File Path: `{{$node["Get Results"].json["results"]["files"]["dashboard_data"]}}`

### Example: GRASP Evaluator Workflow

For GRASP evaluator, the workflow is identical but uses different endpoints:

1. **HTTP Request Node** - Start GRASP Evaluation
   - Method: POST
   - URL: `http://localhost:8888/graspevaluator/analyze`
   - Body: `{"url": "https://yoursite.com", "verbose": true}`

2-6. Follow the same pattern as above using the same job ID

### Example: LLM Evaluator Workflow

For LLM evaluator, the workflow is similar but uses a config file parameter:

1. **HTTP Request Node** - Start LLM Evaluation
   - Method: POST
   - URL: `http://localhost:8888/llmevaluator/analyze`
   - Body: `{"config": "example_config.md", "log_level": "INFO"}`

2-6. Follow the same pattern as above using the same job ID

**Note**: LLM Evaluator requires a configuration file that defines the brand, evaluation prompts, and LLM settings. See the llmevaluator directory for example config files.

## Response Formats

### Start Analysis Response
```json
{
  "job_id": "uuid-here",
  "status": "queued",
  "message": "IntentCrawler analysis started"
}
```

### Status Response
```json
{
  "job_id": "uuid-here",
  "tool": "intentcrawler",
  "status": "running|completed|failed",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:01:00",
  "completed_at": null
}
```

### Results Response
```json
{
  "job_id": "uuid-here",
  "tool": "intentcrawler",
  "status": "completed",
  "created_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:05:00",
  "results": {
    "output_directory": "/path/to/results/2024-01-01",
    "files": {
      "dashboard_data": "/path/to/results/2024-01-01/dashboard-data.json",
      "intent_report": "/path/to/results/2024-01-01/intent-report.json",
      "intent_summary": "/path/to/results/2024-01-01/intent-summary.md",
      "llm_export": "/path/to/results/2024-01-01/llm-export.json"
    },
    "metrics": {
      "pages_analyzed": 150,
      "intents_discovered": 12,
      "processing_time_seconds": null
    }
  }
}
```

## Configuration

Tool configurations are managed in `tools_config.yaml`. This file contains:

- **Tool definitions**: Each tool's settings, parameters, and output files
- **Server settings**: Port, host, CORS, and other server configurations
- **Timeouts**: Tool-specific execution timeouts

### Supported Tools

### Currently Integrated:
1. **IntentCrawler** - Website intent analysis for LLMs
2. **GRASP Evaluator** - Content quality assessment (Grounded, Readable, Accurate, Structured, Polished)
3. **GEO Evaluator** - Generative Engine Optimization analysis
4. **LLM Evaluator** - Brand presence and sentiment evaluation across multiple LLM models

### Testing Tools:
Test scripts are provided for each tool:
```bash
# Test IntentCrawler
python test_api.py https://example.com

# Test GRASP Evaluator
python test_grasp.py https://example.com

# Test GEO Evaluator
python test_geo.py https://example.com "Site Name"

# Test LLM Evaluator
python test_llm.py example_config.md
```

## Adding New Tools

To add a new tool, edit `tools_config.yaml`:

```yaml
your_tool_name:
  name: "Your Tool Display Name"
  module_path: "your_tool_folder"
  script: "your_tool.py"
  description: "What your tool does"
  result_files:
    - "dashboard-data.json"
    - "your-report.json"
  required_params:
    - "url"
  optional_params:
    - "config"
    - "output"
  param_style: "flags"  # or "positional" for tools like intentcrawler
```

The API server will automatically pick up the new tool configuration on restart.

### Modifying Server Settings

Edit the `server` section in `tools_config.yaml`:

```yaml
server:
  port: 8888
  host: "0.0.0.0"
  debug: false
  cors_enabled: true
```