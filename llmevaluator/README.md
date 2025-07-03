# LLM Evaluator

A tool to evaluate how brands are mentioned and represented in Large Language Model (LLM) responses based on targeted user intents.

## Overview

LLM Evaluator helps brand managers understand:
- How often their brand is mentioned in LLM responses
- How often their website is referenced
- The sentiment associated with their brand
- The context in which their brand appears (recommendation, comparison, example)
- How they compare to competitors

## Features

- **Multi-Provider Support**: Works with OpenAI and Anthropic LLMs
- **Response Caching**: Efficiently reuse responses to save on API costs
- **Sentiment Analysis**: Hybrid approach using TextBlob and LLM-based analysis
- **Context Detection**: Identifies whether mentions are recommendations, comparisons, or examples
- **Position Tracking**: Tracks where in responses brands are mentioned
- **Dashboard Integration**: Automatically integrates with the master dashboard
- **Batch Processing**: Efficiently process multiple prompts
- **Detailed Reporting**: Generates comprehensive reports and metrics

## Installation

1. Install dependencies:
```bash
cd llmevaluator
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Create a markdown configuration file (see `example_config.md`):

```markdown
# Brand Configuration

## Brand Information
- **Name**: YourBrand
- **Website**: https://yourbrand.com
- **Aliases**: ["Your Brand", "YB"]
- **Competitors**: ["Competitor A", "Competitor B"]

## Evaluation Prompts

### Category: Getting Started
1. How do I get started with [your domain]?
2. What's the best tool for [your use case]?

### Category: Features
1. What features should I look for in [your product category]?
2. How do I implement [specific feature]?

## Evaluation Settings
- **LLM Provider**: openai
- **Model**: gpt-4
- **Temperature**: 0.7
- **Cache Responses**: true
```

## Usage

### Basic Evaluation
```bash
python evaluate.py path/to/config.md
```

### Command Line Options
```bash
python evaluate.py config.md --output-dir ./custom-results
python evaluate.py config.md --no-cache              # Disable caching
python evaluate.py config.md --clear-cache           # Clear cache first
python evaluate.py config.md --log-level DEBUG       # Debug logging
python evaluate.py config.md --dry-run               # Validate config only
```

## Output

Results are saved in timestamped directories:
```
results/
└── 2024-01-15/
    ├── dashboard-data.json    # Dashboard-compatible data
    ├── raw_results.json       # Detailed evaluation results
    ├── metrics_summary.json   # Aggregate metrics
    └── evaluation_report.txt  # Human-readable report
```

## Dashboard Integration

Results automatically appear in the master dashboard at `/dashboard`. The dashboard will:
- Auto-discover llmevaluator results
- Display brand mention metrics
- Show sentiment analysis
- Visualize context and position distributions
- Compare performance across categories

## Metrics Explained

### Brand Mentions
- **Total Mentions**: Count of brand name appearances
- **Mention Rate**: Average mentions per prompt
- **Position**: Where mentions appear (beginning, middle, end)

### Sentiment Analysis
- **Score**: -1 (negative) to +1 (positive)
- **Label**: Positive, Negative, or Neutral
- **Method**: Hybrid (TextBlob + LLM analysis)

### Context Types
- **Recommendation**: Brand suggested as solution
- **Comparison**: Brand compared to others
- **Example**: Brand used as example
- **Explanation**: General explanation mentioning brand

## API Configuration

### Multiple Providers
Edit your markdown config to add provider details:
```markdown
## LLM Providers

### OpenAI
- **Endpoint**: https://api.openai.com/v1
- **API Key**: $OPENAI_API_KEY
- **Models**: ["gpt-4", "gpt-3.5-turbo"]

### Anthropic
- **Endpoint**: https://api.anthropic.com
- **API Key**: $ANTHROPIC_API_KEY
- **Models**: ["claude-3-opus", "claude-3-sonnet"]
```

## Troubleshooting

### No API Key Found
Ensure your `.env` file contains valid API keys:
```
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Rate Limiting
The tool implements automatic retries with exponential backoff. For persistent issues, reduce batch size or add delays.

### Cache Issues
Clear cache if you encounter stale results:
```bash
python evaluate.py config.md --clear-cache
```

## Advanced Usage

### Custom Cache Settings
In `.env`:
```
CACHE_DIR=./custom-cache
CACHE_EXPIRE_HOURS=48
```

### Programmatic Usage
```python
from src.config import ConfigurationManager
from src.llm_interface import LLMInterface
from src.prompt_executor import PromptExecutor

# Load config
config = ConfigurationManager('config.md')

# Create interface
llm = LLMInterface.create_from_config(config)

# Execute prompts
executor = PromptExecutor(llm)
results = executor.execute_batch(config.prompts, config.settings)
```

## Contributing

When adding new features:
1. Maintain dashboard compatibility
2. Follow existing code patterns
3. Add appropriate logging
4. Update documentation

## License

Part of the Airbais Tools Suite