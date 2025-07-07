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

- **Multi-LLM Evaluation**: Evaluate brand mentions across multiple LLMs simultaneously
- **Comparative Analysis**: Compare how different LLMs mention and represent your brand
- **Multi-Provider Support**: Works with OpenAI and Anthropic LLMs
- **Response Caching**: Efficiently reuse responses to save on API costs
- **Sentiment Analysis**: Hybrid approach using TextBlob and LLM-based analysis
- **Context Detection**: Identifies whether mentions are recommendations, comparisons, or examples
- **Position Tracking**: Tracks where in responses brands are mentioned
- **Dashboard Integration**: Automatically integrates with the master dashboard
- **Batch Processing**: Efficiently process multiple prompts
- **Detailed Reporting**: Generates comprehensive reports with per-LLM and comparative metrics

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

Create a markdown configuration file (see `example_multi_llm_config.md` for multi-LLM example):

```markdown
# Brand Configuration

## Brand Information
- **Name**: YourBrand
- **Website**: https://yourbrand.com
- **Aliases**: ["Your Brand", "YB"]
- **Competitors**: ["Competitor A", "Competitor B"]

## LLMs
- name: gpt4
  provider: openai
  model: gpt-4
  temperature: 0.7
  max_tokens: 300

- name: claude
  provider: anthropic
  model: claude-3-sonnet-20240229
  temperature: 0.5
  max_tokens: 300

## Evaluation Prompts

### Category: Getting Started
1. How do I get started with [your domain]?
2. What's the best tool for [your use case]?

### Category: Features
1. What features should I look for in [your product category]?
2. How do I implement [specific feature]?

## Evaluation Settings
- **Cache Responses**: true
- **Sentiment Analysis Method**: hybrid
```

## Usage

### 🚀 Quick Start

Basic evaluation:
```bash
python llmevaluator.py config.md
```

With dashboard:
```bash
python llmevaluator.py config.md --dashboard
```

View latest results:
```bash
python llmevaluator.py --dashboard-only
```

### Command Line Options
```bash
# Basic evaluation
python llmevaluator.py config.md

# With custom output directory
python llmevaluator.py config.md --output-dir ./custom-results

# Launch dashboard after evaluation
python llmevaluator.py config.md --dashboard

# View existing results in dashboard
python llmevaluator.py --dashboard-only
python llmevaluator.py --dashboard-date 2024-01-15

# Other options
python llmevaluator.py config.md --no-cache              # Disable caching
python llmevaluator.py config.md --clear-cache           # Clear cache first
python llmevaluator.py config.md --log-level DEBUG       # Debug logging
python llmevaluator.py config.md --dry-run               # Validate config only
python llmevaluator.py --list-results                    # Show available result dates
```

## Output

Results are saved in timestamped directories:
```
results/
└── 2024-01-15/
    ├── dashboard-data.json    # Dashboard-compatible data with multi-LLM structure
    ├── raw_results.json       # Detailed evaluation results for all LLMs
    ├── metrics_summary.json   # Aggregate metrics across all LLMs
    └── evaluation_report.txt  # Human-readable report with per-LLM and comparative analysis
```

### Multi-LLM Report Structure

The evaluation generates comprehensive reports including:
- **Per-LLM Metrics**: Individual performance metrics for each LLM
- **Comparative Metrics**: 
  - Consensus Score: How often LLMs agree on brand mentions
  - Sentiment Alignment: Agreement on brand sentiment
  - Mention Rate Variance: Variation in how often each LLM mentions the brand
- **Aggregate Metrics**: Overall performance averaged across all LLMs

## Dashboard Integration

Results automatically appear in the master dashboard at `/dashboard`. The dashboard will:
- Auto-discover llmevaluator results
- Display brand mention metrics for each LLM
- Show sentiment analysis per LLM
- Visualize context and position distributions
- Compare performance across categories and LLMs
- Show comparative metrics when multiple LLMs are evaluated

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

### Multi-LLM Metrics
When evaluating multiple LLMs, additional comparative metrics are calculated:
- **Consensus Score**: Percentage of prompts where all LLMs agree on mentioning (or not mentioning) the brand
- **Sentiment Alignment**: How closely LLMs agree on brand sentiment (0-100%)
- **Mention Rate Variance**: Statistical variance in mention rates across LLMs

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
python llmevaluator.py config.md --clear-cache
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