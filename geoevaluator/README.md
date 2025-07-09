# GEO Evaluator

A comprehensive tool for analyzing website content optimization for Generative Engine Optimization (GEO). Evaluates how well websites are optimized for Large Language Models (LLMs) to understand and reference brand content appropriately.

## Overview

The GEO Evaluator analyzes websites across 5 key categories:

1. **Structural HTML Analysis (25% Weight)** - Semantic markup, heading hierarchy, content landmarks
2. **Content Organization & Readability (30% Weight)** - Paragraph structure, scannability, FAQ formatting
3. **Token Efficiency (20% Weight)** - Content-to-markup ratio, information density, clutter analysis
4. **LLM-Specific Technical Implementation (15% Weight)** - llms.txt, structured data, meta optimization
5. **Content Accessibility & Clarity (10% Weight)** - Alt text, link context, language clarity

## Features

- **Comprehensive Website Analysis**: Crawls websites respecting robots.txt and sitemaps
- **Weighted Scoring Algorithm**: Produces scores from 0-100 with letter grades (Excellent to Very Poor)
- **Individual Page Scoring**: Detailed analysis of each page with category-specific scores
- **Actionable Recommendations**: Prioritized optimization suggestions with impact estimates
- **Affected Pages Tracking**: See exactly which pages need attention for each recommendation
- **Dashboard Integration**: Seamless integration with the master tools dashboard
- **Auto-Launch Dashboard**: Dashboard automatically opens when using --dashboard flag
- **Multiple Output Formats**: JSON, HTML reports, and dashboard-compatible data
- **Respectful Crawling**: Configurable delays, timeout handling, and robots.txt compliance

## Installation

1. **Install Dependencies**:
   ```bash
   cd geoevaluator
   pip install -r requirements.txt
   ```

2. **Verify Installation**:
   ```bash
   python geoevaluator.py --version
   ```

## Quick Start

### Basic Analysis
```bash
# Analyze Airbais website with default settings
python geoevaluator.py --url https://airbais.com --name "Airbais"
```

### Using Configuration File
```bash
# Create example configuration
python geoevaluator.py config.yaml

# Customize config.yaml for your website, then run:
python geoevaluator.py config.yaml
```

### Dashboard Integration
```bash
# Run analysis and launch dashboard automatically
python geoevaluator.py config.yaml --dashboard

# The dashboard will open automatically at http://127.0.0.1:8050
# Or run dashboard manually later:
cd ../dashboard
python run_dashboard.py
```

## Configuration

### Configuration File Format

Create a YAML configuration file for customized analysis:

```yaml
website:
  url: "https://your-website.com"
  name: "Your Brand Name"
  max_pages: 50              # Maximum pages to analyze
  crawl_depth: 3             # Maximum link depth
  excluded_paths:            # Paths to exclude
    - "/admin"
    - "/api"

analysis:
  weights:                   # Category weights (must sum to 1.0)
    structural_html: 0.25
    content_organization: 0.30
    token_efficiency: 0.20
    llm_technical: 0.15
    accessibility: 0.10
  
  thresholds:
    semantic_html_excellent: 0.80
    semantic_html_good: 0.60
    readability_optimal_min: 15
    readability_optimal_max: 20

crawling:
  delay_seconds: 1.0         # Respectful crawling delay
  timeout_seconds: 30        # Request timeout
  respect_robots_txt: true   # Follow robots.txt
  follow_sitemaps: true      # Use sitemap.xml

output:
  formats: ["json", "dashboard"]  # Output formats
  export_path: "./results"        # Output directory
  include_recommendations: true   # Include optimization tips
```

### Command Line Options

```bash
# Basic options
python geoevaluator.py --url URL --name "Brand Name"
python geoevaluator.py config.yaml

# Analysis options
python geoevaluator.py --url URL --max-pages 100 --crawl-depth 2

# Output options
python geoevaluator.py config.yaml --output-dir ./custom-results
python geoevaluator.py config.yaml --formats json html dashboard

# Crawling options
python geoevaluator.py config.yaml --delay 2.0 --timeout 60

# Utility options
python geoevaluator.py config.yaml --dry-run    # Validate config
python geoevaluator.py config.yaml --verbose    # Debug logging
```

## Output

Results are saved in timestamped directories:

```
results/
└── 2025-07-05/
    ├── dashboard-data.json         # Dashboard integration
    ├── detailed_scores.json        # Complete analysis results
    ├── geo_analysis_report.html    # Human-readable report
    └── optimization_recommendations.json  # Actionable insights
```

### Dashboard Integration

The tool automatically integrates with the master dashboard:

1. **Run Analysis**: Execute analysis with `--dashboard` flag
2. **Launch Dashboard**: Navigate to `/dashboard` and run `python dashboard.py`
3. **View Results**: Select "Geoevaluator" from the tool dropdown

Dashboard displays:
- Overall GEO optimization score and grade
- Category-by-category breakdown with visual indicators
- Top optimization recommendations with affected pages
- Industry benchmarks and performance tier
- Individual page scores with drill-down capability
- Side-by-side analysis summary and benchmarks (responsive layout)

## Understanding Scores

### Overall Score Ranges
- **90-100**: Excellent LLM Optimization
- **80-89**: Good LLM Optimization  
- **70-79**: Fair LLM Optimization
- **60-69**: Poor LLM Optimization
- **Below 60**: Very Poor LLM Optimization

### Category Explanations

**Structural HTML (25%)**
- Semantic element usage (article, section, main vs div/span)
- Proper heading hierarchy (H1-H6)
- Content landmark implementation
- HTML validation and structure

**Content Organization (30%)**
- Paragraph and sentence structure
- Use of lists and tables for data
- FAQ and Q&A formatting
- Content scannability and breaks

**Token Efficiency (20%)**
- Content-to-markup ratio
- Information density per token
- Navigation and sidebar clutter
- Content extraction efficiency

**LLM Technical (15%)**
- llms.txt file implementation
- Structured data markup (Schema.org)
- Meta information optimization
- Technical SEO for LLMs

**Accessibility (10%)**
- Image alt text quality
- Link context and descriptiveness
- Language clarity and readability
- Media accessibility features

## Optimization Recommendations

The tool provides prioritized recommendations:

### Priority Levels
- **High**: Critical issues affecting LLM understanding
- **Medium**: Important improvements with good ROI
- **Low**: Nice-to-have enhancements

### Common Recommendations
1. **Add llms.txt file** - Essential for LLM optimization
2. **Improve semantic HTML** - Replace generic divs with semantic elements
3. **Optimize heading hierarchy** - Ensure logical H1-H6 structure
4. **Add structured data** - Implement Schema.org markup
5. **Enhance content organization** - Break up long paragraphs, add lists
6. **Improve alt text** - Add descriptive alternative text for images

Each recommendation includes:
- **Affected Pages List**: Clickable links to specific pages needing attention
- **Impact Metrics**: Word count for content issues, ratio percentages for efficiency
- **Priority Level**: High/Medium/Low with color-coded indicators

## Examples

### Analyzing Airbais Website
```bash
# Quick analysis
python geoevaluator.py --url https://airbais.com --name "Airbais"

# Detailed analysis with custom settings
python geoevaluator.py --url https://airbais.com --name "Airbais" \
  --max-pages 25 --crawl-depth 2 --dashboard --verbose
```

### Batch Analysis
```bash
# Create configuration for multiple sites
python geoevaluator.py site1-config.yaml
python geoevaluator.py site2-config.yaml
python geoevaluator.py site3-config.yaml

# Compare results in dashboard
cd ../dashboard && python dashboard.py
```

### Development and Testing
```bash
# Validate configuration
python geoevaluator.py config.yaml --dry-run

# Debug crawling issues
python geoevaluator.py config.yaml --verbose --max-pages 5

# Test specific pages
python geoevaluator.py --url https://example.com/specific-page \
  --max-pages 1 --crawl-depth 0
```

## Troubleshooting

### Common Issues

**No pages crawled**
- Check robots.txt permissions
- Verify website accessibility
- Review excluded paths configuration
- Increase timeout settings

**Low scores despite good content**
- Review category weights for your use case
- Check for excessive navigation/sidebar content
- Ensure semantic HTML usage
- Implement llms.txt file

**Slow crawling**
- Reduce max_pages or crawl_depth
- Increase delay_seconds for respectful crawling
- Check network connectivity
- Verify timeout settings

**Dashboard not showing results**
- Ensure analysis ran with `--dashboard` flag
- Check `results/` directory for `dashboard-data.json`
- Verify dashboard is scanning correct directory
- Check dashboard logs for integration errors

### Debug Mode
```bash
# Enable verbose logging
python geoevaluator.py config.yaml --verbose

# Test configuration
python geoevaluator.py config.yaml --dry-run

# Analyze small sample
python geoevaluator.py config.yaml --max-pages 5 --verbose
```

## Advanced Usage

### Custom Scoring Weights
Adjust category weights based on your priorities:

```yaml
analysis:
  weights:
    structural_html: 0.15        # Reduce if content matters more
    content_organization: 0.40   # Increase for content-heavy sites
    token_efficiency: 0.25       # Increase for efficiency focus
    llm_technical: 0.15          # Keep high for LLM optimization
    accessibility: 0.05          # Adjust based on requirements
```

### Performance Optimization
```yaml
crawling:
  delay_seconds: 0.5           # Faster crawling (be respectful!)
  timeout_seconds: 15          # Shorter timeouts
  max_file_size_mb: 5          # Skip large files

website:
  max_pages: 25                # Smaller analysis scope
  crawl_depth: 2               # Shallower crawling
```

### Integration with CI/CD
```bash
# Automated analysis in build pipeline
python geoevaluator.py config.yaml --formats json
if [ $(jq '.overall_score.total_score' results/*/dashboard-data.json) -lt 80 ]; then
  echo "GEO score below threshold"
  exit 1
fi
```

## Contributing

When extending the GEO Evaluator:

1. **Follow Patterns**: Use existing analyzer and scoring patterns
2. **Dashboard Compatibility**: Ensure new features integrate with dashboard
3. **Configuration**: Add new options to configuration system
4. **Testing**: Test with various website types and sizes
5. **Documentation**: Update README and configuration examples

## License

Part of the Airbais Tools Suite. See main repository for license information.