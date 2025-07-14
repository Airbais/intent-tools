# LLMS.txt Generator

Automatically generate LLMS.txt files for any website to help Large Language Models better understand and reference your content.

## Overview

The LLMS.txt Generator crawls websites and creates standardized LLMS.txt files following the specification at [llmstxt.org](https://llmstxt.org/). These files provide LLMs with a concise, structured overview of your website's content, making it easier for AI assistants to understand and accurately reference your site.

## Features

🤖 **Automatic Site Analysis** - Intelligently crawls and analyzes website structure  
📝 **Spec Compliant** - Generates files following the official LLMS.txt specification  
🧠 **AI-Enhanced Descriptions** - Optional AI-powered generation of link descriptions  
📊 **Multiple Output Formats** - Generates .txt, .md, and .json versions  
🔍 **Smart Section Detection** - Automatically categorizes content into docs, API, guides, etc.  
📈 **Detailed Reports** - Comprehensive generation reports with crawl statistics  
🎯 **Configurable Crawling** - Control depth, page limits, and URL patterns  
🚀 **Dashboard Integration** - Visualize results in the Airbais master dashboard

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/airbais-tools.git
cd airbais-tools/llmstxtgenerator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up AI API keys for enhanced descriptions:
```bash
export OPENAI_API_KEY="your-openai-api-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

## Usage

### Quick Start

Generate LLMS.txt for a website:
```bash
python llmstxtgenerator.py https://example.com
```

With custom name and description:
```bash
python llmstxtgenerator.py https://example.com --name "My Project" --description "An awesome project that does amazing things"
```

### Using Configuration File

Edit `config.yaml` to set your preferences:
```yaml
website:
  url: "https://example.com"
  name: "My Project"  # Optional
  description: "Project description"  # Optional

generation:
  max_pages: 100
  max_depth: 3
  sections:
    - "docs"
    - "api"
    - "guides"
    - "tutorials"
```

Then run:
```bash
python llmstxtgenerator.py
```

## Configuration

### Example Configuration
```yaml
website:
  url: "https://gofastmcp.com"
  name: null  # Auto-detected if not specified
  description: null  # Auto-detected or AI-generated

generation:
  max_pages: 100  # Maximum pages to crawl
  max_depth: 3  # Maximum crawl depth
  include_patterns:  # URL patterns to include (regex)
    - ".*"
  exclude_patterns:  # URL patterns to exclude
    - ".*\\.pdf$"
    - ".*/assets/.*"
  sections:  # Sections to organize content
    - "docs"
    - "api"
    - "guides"
    - "tutorials"
    - "examples"
    - "reference"
  max_links_per_section: 20

analysis:
  use_ai_descriptions: true  # Generate descriptions with AI
  ai_model: "gpt-4o-mini"  # AI model to use
  extract_meta: true  # Extract meta tags
  extract_headings: true  # Extract page headings

output:
  directory: "results"
  keep_past_results: true
  generate_report: true
  formats:  # Output formats to generate
    - "txt"
    - "markdown"
    - "json"

crawling:
  timeout: 30  # Request timeout in seconds
  user_agent: "LLMS.txt Generator Bot (https://airbais.com)"
  delay: 0.5  # Delay between requests
  follow_redirects: true
  verify_ssl: true
  max_retries: 3
```

## Output Structure

```
results/
└── YYYY-MM-DD/
    ├── llms.txt           # Standard LLMS.txt file
    ├── llms.md            # Markdown version with metadata
    ├── llms.json          # Structured JSON data
    ├── generation_report.md  # Detailed generation report
    └── dashboard-data.json   # Dashboard integration data
```

### Example LLMS.txt Output
```markdown
# FastMCP

> Build and interact with Model Context Protocol servers and clients in Python

FastMCP is a Python library for building and interacting with MCP servers...

## Docs
- [Quickstart](https://gofastmcp.com/docs/quickstart): Get started with FastMCP
- [Installation](https://gofastmcp.com/docs/installation): Installation instructions
- [Core Concepts](https://gofastmcp.com/docs/concepts): Understanding MCP

## API
- [Server API](https://gofastmcp.com/api/server): Server implementation reference
- [Client API](https://gofastmcp.com/api/client): Client implementation reference

## Optional
- [Examples](https://gofastmcp.com/examples): Code examples and demos
```

## Dashboard Integration

### Local Dashboard
Launch the dashboard after generation:
```bash
python llmstxtgenerator.py https://example.com --dashboard
```

### Master Dashboard
The tool automatically generates `dashboard-data.json` for integration with the Airbais master dashboard:
```bash
cd ../dashboard
python dashboard.py
```

## Command Line Options

```
usage: llmstxtgenerator.py [-h] [-c CONFIG] [--name NAME] [--description DESCRIPTION]
                           [--max-pages MAX_PAGES] [--max-depth MAX_DEPTH] [--no-ai]
                           [-o OUTPUT_DIR] [--dashboard] [-v] [--version]
                           [url]

Generate LLMS.txt files for websites to help LLMs understand their content

positional arguments:
  url                   Website URL to generate LLMS.txt for

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Configuration file path (default: config.yaml)
  --name NAME           Website/project name (overrides auto-detection)
  --description DESCRIPTION
                        Website/project description (overrides auto-detection)
  --max-pages MAX_PAGES Maximum number of pages to crawl
  --max-depth MAX_DEPTH Maximum crawl depth
  --no-ai               Disable AI-generated descriptions
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory for results
  --dashboard           Launch dashboard after generation
  -v, --verbose         Enable verbose logging
  --version             show program's version number and exit

Examples:
  llmstxtgenerator.py https://example.com
  llmstxtgenerator.py https://example.com --name "My Project" --description "A cool project"
  llmstxtgenerator.py https://example.com --max-pages 50 --max-depth 2
  llmstxtgenerator.py https://example.com --no-ai --output-dir custom_results
  llmstxtgenerator.py --config custom_config.yaml
```

## Troubleshooting

### No pages found
- Check if the website URL is correct and accessible
- Verify that the site doesn't block automated crawlers
- Try adjusting the user agent in configuration
- Check include/exclude patterns in configuration

### AI descriptions not working
- Ensure you have set the appropriate API key (OPENAI_API_KEY or ANTHROPIC_API_KEY)
- Check that the AI model specified in config is valid
- Use `--no-ai` flag to disable AI descriptions

### Crawling too slow
- Reduce the delay between requests in configuration
- Lower the max_pages or max_depth limits
- Check your internet connection

### SSL certificate errors
- Set `verify_ssl: false` in crawling configuration (not recommended for production)
- Ensure the website has valid SSL certificates

## Advanced Usage

### Custom Crawl Patterns
Control which URLs to include or exclude:
```yaml
generation:
  include_patterns:
    - "https://example.com/docs/.*"
    - "https://example.com/api/.*"
  exclude_patterns:
    - ".*\\.(pdf|zip|tar\\.gz)$"
    - ".*/downloads/.*"
```

### Section Prioritization
Customize which sections appear in the LLMS.txt:
```yaml
generation:
  sections:
    - "quickstart"  # Appears first
    - "installation"
    - "api"
    - "tutorials"
  max_links_per_section: 15
```

### Using Without AI
For faster generation without AI descriptions:
```bash
python llmstxtgenerator.py https://example.com --no-ai
```

## Contributing

To extend the LLMS.txt Generator:

1. **Add new section detectors**: Edit `_determine_section()` in `src/crawler.py`
2. **Customize output formats**: Add new format handlers in `src/generator.py`
3. **Enhance AI descriptions**: Modify prompts in `src/analyzer.py`
4. **Add new crawl strategies**: Extend the `WebsiteCrawler` class

## License

Part of the Airbais Tools Suite. See LICENSE file for details.