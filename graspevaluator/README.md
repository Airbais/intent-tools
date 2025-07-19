# GRASP Content Quality Evaluator

The GRASP Content Quality Evaluator is a comprehensive tool that assesses website content across five critical dimensions to optimize for LLM understanding and response generation.

## What is GRASP?

GRASP evaluates content quality using five key metrics:

- **G**rounded (40%) - Content alignment with customer intents
- **R**eadable (10%) - Appropriate reading level for target audience  
- **A**ccurate (30%) - Content freshness as a proxy for accuracy
- **S**tructured (10%) - Semantic HTML structure for LLM consumption
- **P**olished (10%) - Grammar and language quality

## Features

### Content Quality Assessment
- **Intent Alignment**: Uses AI to evaluate how well content answers customer questions
- **Readability Analysis**: Calculates reading level and matches to target audience
- **Freshness Detection**: Finds and evaluates last-modified dates from multiple sources
- **Structure Evaluation**: Analyzes HTML semantic structure, headings, and schema markup
- **Language Quality**: AI-powered grammar, spelling, and style checking

### Comprehensive Reporting
- Overall GRASP score with weighted breakdown
- Individual metric scores and analysis
- Actionable improvement recommendations
- Dashboard-compatible output format
- Detailed JSON results

### AI-Powered Analysis
- OpenAI integration for grounded and polished metrics
- Fallback rule-based analysis when AI is unavailable
- Configurable AI models and parameters

## Installation

1. Clone the repository and navigate to the graspevaluator directory:
```bash
cd tools/graspevaluator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key in the `.env` file:
```bash
# In tools/.env
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Single URL Evaluation
```bash
python graspevaluator.py --url https://example.com
```

### Batch Evaluation (Default)
```bash
python graspevaluator.py
```

### With Dashboard
```bash
python graspevaluator.py --dashboard
```

### Custom Configuration
```bash
python graspevaluator.py --url https://example.com --config custom_config.yaml
```

## Configuration

The evaluator uses a YAML configuration file (`config/grasp_config.yaml`) to customize:

- Target URLs for batch evaluation
- Customer intents for grounded evaluation
- Reading level targets
- Freshness thresholds
- AI model settings
- Output preferences

### Example Configuration

```yaml
targets:
  - url: "https://yoursite.com"

grounded:
  intents:
    - "How do I contact support?"
    - "What are your pricing options?"
    - "How do I get started?"

readable:
  target_audience: "general_public"

accurate:
  freshness_thresholds:
    high: 180    # 6 months
    medium: 365  # 1 year

polished:
  use_llm: true
  llm_model: "gpt-3.5-turbo"
```

## Understanding Your Results

### GRASP Score
The overall GRASP score is calculated as:
- Grounded: 40% weight
- Readable: 10% weight  
- Accurate: 30% weight
- Structured: 10% weight
- Polished: 10% weight

### Grade Scale
- **90-100**: A (Excellent)
- **80-89**: B (Good)
- **70-79**: C (Fair)
- **60-69**: D (Poor)
- **Below 60**: F (Very Poor)

### Metric Details

#### Grounded (40%)
- Evaluates how well content supports answering customer intents
- Uses AI to attempt answering questions using only your content
- Scores based on answer quality and content support
- Scale: 0-10 points

#### Readable (10%)
- Analyzes reading level using multiple readability formulas
- Compares against target audience expectations
- Pass/Fail based on grade level alignment
- Configurable tolerance for grade level matching

#### Accurate (30%)
- Assesses content freshness from multiple date sources
- Checks meta tags, schema markup, time elements, and HTTP headers
- Ratings: High (< 6 months), Medium (< 1 year), Low (> 1 year)

#### Structured (10%)
- Evaluates semantic HTML structure
- Checks heading hierarchy, semantic elements, data structures
- Analyzes schema.org markup and metadata
- Ratings: Excellent, Good, Fair, Poor, Very Poor

#### Polished (10%)
- AI-powered grammar and style analysis
- Checks spelling, punctuation, and language quality
- Calculates error rates and provides detailed feedback
- Ratings: Excellent, Good, Fair, Poor, Very Poor

## Dashboard Integration

Results are automatically formatted for the master dashboard:

```bash
python graspevaluator.py --batch --dashboard
```

The dashboard displays:
- Interactive GRASP score visualization
- Metric breakdown with weights
- Historical trend analysis
- Improvement recommendations

## Output Files

Results are saved in timestamped directories:

```
results/
└── 2024-01-15/
    ├── grasp_evaluation_results.json    # Detailed results
    ├── dashboard-data.json               # Dashboard format
    └── grasp_evaluator.log              # Execution log
```

## API Requirements

- **OpenAI API**: Required for Grounded and Polished metrics
- **Rate Limits**: Respects API rate limits with built-in batching
- **Fallbacks**: Rule-based alternatives when AI is unavailable

## Troubleshooting

### Common Issues

1. **Missing OpenAI API Key**
   ```
   Error: OPENAI_API_KEY not found in environment variables
   ```
   Solution: Add your API key to the `.env` file

2. **Rate Limiting**
   ```
   Error: Rate limit exceeded
   ```
   Solution: Reduce batch size or add delays in configuration

3. **Content Too Long**
   ```
   Warning: Content truncated for analysis
   ```
   Solution: Increase max_content_length in configuration

### Debug Mode
```bash
python graspevaluator.py --url https://example.com --verbose
```

## Contributing

This tool is part of the Airbais suite. For contributions:

1. Follow the existing code patterns
2. Add tests for new features
3. Update documentation
4. Ensure dashboard compatibility

## License

Part of the Airbais Tools suite. See main project license.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the configuration examples
- Consult the technical deep dive documentation