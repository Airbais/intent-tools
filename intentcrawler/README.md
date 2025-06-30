# IntentCrawler - Website Intent Analysis Tool

A professional Python tool that crawls websites and analyzes the user intents conveyed to LLMs and AI agents. Part of the Airbais AI Tools Suite, IntentCrawler extracts content, discovers intents dynamically using multiple ML techniques, and provides modern interactive dashboards for visualization.

## ✨ Features

- **🕷️ Intelligent Web Crawling**: Respectful crawling with robots.txt compliance and rate limiting
- **🗺️ Sitemap Support**: Automatically discovers and parses XML sitemaps
- **🧹 Content Processing**: Extracts clean content from web pages
- **🧠 Enhanced Dynamic Intent Discovery:**
  - User Intent Analysis (default) - focuses on what users want to accomplish
  - Latent Dirichlet Allocation (LDA) for topic modeling
  - Sentence embeddings with clustering
  - Configurable fallback keywords
  - Automatic intent naming and merging
- **📝 llmstxt Format**: Outputs summaries in the standardized llmstxt format
- **🏗️ Site Structure Analysis**: Maps website hierarchy
- **📊 Modern Interactive Dashboard**: Professional web-based dashboard with Airbais design system
- **🌙 Light/Dark Mode**: Responsive design with theme persistence
- **📅 Date-based Results**: Organized by date with automatic cleanup
- **🔗 Master Dashboard Integration**: Works with centralized multi-tool dashboard
- **📤 Structured Exports**: JSON outputs for LLM tool integration

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

## Usage

### 🚀 Quick Start

Basic analysis:
```bash
python intentcrawler.py https://example.com
```

With dashboard:
```bash
python intentcrawler.py https://example.com --dashboard
```

View latest results:
```bash
python intentcrawler.py --dashboard-only
```

View results from specific date:
```bash
python intentcrawler.py --dashboard-date 2024-06-26
```

List available results:
```bash
python intentcrawler.py --list-results
```

### 📊 Dashboard Options

**Local Dashboard** (tool-specific):
```bash
python intentcrawler.py --dashboard-only
```

**Master Dashboard** (all tools):
```bash
cd ../dashboard
python run_dashboard.py
```

## Configuration

Edit `config.yaml` to customize:

### Crawler Settings
```yaml
crawler:
  max_pages: 1000
  rate_limit: 2
  respect_robots: true
  use_sitemap: true
```

### Intent Extraction
```yaml
intents:
  extraction_method: 'user_intent'  # Default: user-focused analysis
  # Alternative methods: 'dynamic', 'enhanced', 'original'
  use_embeddings: true               # Use sentence transformers
  use_lda: true                     # Use topic modeling  
  lda_topics: 10                    # Number of LDA topics
  embeddings_model: 'sentence-transformers/all-MiniLM-L6-v2'
  fallback_keywords: true           # Use keywords as fallback
  similarity_threshold: 0.7         # For merging similar intents
  custom_keywords:                  # Configurable keywords
    product_discovery: ['products', 'catalog', 'browse']
    support: ['help', 'support', 'faq']
    integration: ['api', 'developer', 'sdk']
```

### Output Organization
```yaml
output:
  base_directory: 'results'
  date_format: '%Y-%m-%d'
  keep_past_results: 7  # Days to keep (-1 for all)
  overwrite_today: true
```

## Output Structure

Results are organized by date:
```
results/
├── 2024-06-26/           # Today's results
│   ├── llmstxt/
│   │   ├── llms.txt
│   │   └── pages/
│   ├── intent-report.json
│   ├── dashboard-data.json
│   ├── intent-summary.md
│   └── llm-export.json
└── 2024-06-25/           # Yesterday's results
    └── ...
```

## Enhanced Intent Discovery

The tool uses three complementary approaches:

1. **LDA Topic Modeling**: 
   - Discovers latent topics across all content
   - Configurable number of topics
   - Automatically generates intent names from top words

2. **Embedding-based Clustering**: 
   - Uses sentence transformers for semantic understanding
   - DBSCAN clustering for dynamic cluster discovery
   - Groups semantically similar pages

3. **Keyword Fallback**: 
   - Configurable keywords for known intents
   - Used when ML methods need supplementation
   - Maintains baseline intent detection

Intent names are automatically generated based on:
- Common action verbs (learn, buy, compare, etc.)
- Question patterns (how to, what is, why, etc.)
- Domain-specific terminology
- Statistical analysis of representative phrases

## 📊 Dashboard Features

### Modern Design System
- **🎨 Airbais Design**: Professional orange/gray color scheme with Inter font
- **🌙 Light/Dark Mode**: Toggle with persistent preferences
- **📱 Responsive**: Works on desktop and mobile
- **⚡ Fast Loading**: Optimized for performance

### Analysis Views
- **📈 Overview Stats**: Pages analyzed, intents discovered, sections
- **📊 Intent Distribution**: Interactive bar charts with confidence scores
- **🏗️ Section Analysis**: Intent breakdown by site structure
- **📋 Intent Details**: Detailed tables with keywords and page counts
- **🔍 Site Structure**: Visual representation of content organization
- **💾 Export Options**: JSON and summary exports for further analysis

### Two Dashboard Options
1. **Local Dashboard**: Tool-specific view with full feature set
2. **Master Dashboard**: Multi-tool centralized view (future-ready)

## Intent Discovery Process

1. **Content Extraction**: Clean text from each page
2. **Text Preprocessing**: Remove noise, normalize text
3. **Feature Extraction**: 
   - TF-IDF for keyword importance
   - Embeddings for semantic meaning
   - N-grams for phrase detection
4. **Intent Clustering**:
   - LDA for topic discovery
   - DBSCAN for embedding clusters
   - Keyword matching for known patterns
5. **Intent Merging**: Combine similar intents
6. **Naming & Scoring**: Generate descriptive names

## Example Results

```json
{
  "discovered_intents": [
    {
      "primary_intent": "learn_integration",
      "confidence": 0.85,
      "keywords": ["api", "integration", "connect"],
      "representative_phrases": [
        "integrate with your application",
        "api documentation and guides"
      ],
      "page_count": 23,
      "extraction_method": "lda"
    }
  ]
}
```

## Command Line Options

- `--config`: Specify custom config file
- `--output`: Override output directory
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--dashboard`: Launch dashboard after analysis
- `--dashboard-only`: View existing results
- `--dashboard-date`: View specific date's results
- `--list-results`: List all available result dates

## Requirements

- Python 3.8+
- See `requirements.txt` for full dependency list
- Optional: GPU for faster embeddings processing

## Performance Considerations

- **Small sites (<100 pages)**: All methods work well
- **Medium sites (100-500 pages)**: Consider reducing LDA topics
- **Large sites (500-1000 pages)**: May need to disable embeddings
- **Rate limiting**: Respect server resources

## Troubleshooting

**No intents discovered:**
- Check minimum cluster size in config
- Ensure content has sufficient text
- Try enabling fallback keywords

**Slow processing:**
- Reduce number of LDA topics
- Disable embedding extraction
- Increase rate limit delay

**Dashboard not loading:**
- Check if results exist in date folder
- Verify dashboard-data.json is present
- Check console for port conflicts

## 🔗 Integration with AI Tools Suite

IntentCrawler is part of the larger Airbais AI Tools Suite:

- **🏠 Master Dashboard**: Centralized view of all tool results at `../dashboard/`
- **🤝 Standard Data Format**: JSON output compatible with other suite tools
- **🔄 Auto-Discovery**: New tools are automatically detected
- **🎨 Consistent Design**: Shared design system across all tools

### Master Dashboard Benefits
- View results from multiple AI tools in one place
- Tool and date selection dropdowns
- Consistent professional interface
- Future-ready architecture for new tools

## 🚀 Future Enhancements

- **🌍 Multi-language support**: Analyze websites in different languages
- **⏱️ Real-time intent tracking**: Monitor intent changes over time
- **🧪 A/B testing integration**: Compare intent analysis across variants
- **🏷️ Custom intent taxonomies**: Define organization-specific intent categories
- **🔌 API endpoint**: Programmatic access for automated workflows
- **📱 Mobile app**: Native mobile dashboard
- **🤖 AI-powered insights**: LLM-generated recommendations

## Contributing

Key areas for enhancement:
- Additional clustering algorithms
- More sophisticated intent naming
- Enhanced visualization options
- Performance optimizations
- Integration with popular CMS platforms

## License

[Add your license information here]