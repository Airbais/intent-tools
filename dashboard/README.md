# AI Tools Master Dashboard

A centralized dashboard for viewing results from multiple AI tools in the Airbais suite.

## 🏗️ Architecture

```
tools/
├── dashboard/                    # Master Dashboard (this directory)
│   ├── assets/
│   │   ├── dashboard.css        # Modern styling with light/dark mode
│   │   └── theme-toggle.js      # Theme switching functionality
│   ├── dashboard.py             # Main dashboard application
│   ├── data_loader.py           # Multi-tool data loader
│   ├── run_dashboard.py         # Simple launcher script
│   └── README.md               # This file
├── intentcrawler/               # IntentCrawler tool
│   ├── src/                    # Original tool code (unchanged)
│   ├── results/               # Tool-specific results
│   └── ...                    # Tool remains fully independent
└── [future-tools]/             # Additional tools will go here
```

## 🚀 Quick Start

1. **Install Dependencies** (same as intentcrawler):
   ```bash
   pip install dash plotly pandas
   ```

2. **Run the Dashboard**:
   ```bash
   cd tools/dashboard
   python3 run_dashboard.py
   ```

3. **Access Dashboard**: Open http://127.0.0.1:8050

## ✨ Features

### 🎛️ Multi-Tool Support
- **Auto-Discovery**: Automatically finds all tools with results data
- **Tool Selection**: Dropdown to choose which tool's results to view
- **Run Selection**: Choose specific dates/runs for each tool
- **Unified Interface**: Consistent UI across all tools

### 🎨 Modern Design
- **Airbais Design System**: Professional orange/gray color scheme
- **Light/Dark Mode**: Toggle with persistent preference
- **Responsive Layout**: Works on desktop and mobile
- **Interactive Charts**: Plotly-powered visualizations

### 🔌 Extensible Architecture
- **Tool Independence**: Each tool works standalone
- **Standard Data Format**: JSON-based results format
- **Smart Type Detection**: Automatically identifies tool types
- **Easy Integration**: Add new tools by following the pattern

## 📊 Supported Tool Types

### IntentCrawler
- **Overview Stats**: Pages analyzed, intents discovered, sections
- **Intent Distribution**: Bar chart of intent types by page count
- **Site Structure**: Section-based intent analysis
- **Details Table**: Complete intent breakdown

### Future Tools
The dashboard is designed to support additional tool types:
- Sentiment Analyzer
- Performance Monitor
- Content Optimizer
- SEO Analyzer

## 🔧 Adding New Tools

1. **Tool Structure**: Create your tool in `tools/your-tool/`
2. **Results Format**: Save results as `results/YYYY-MM-DD/dashboard-data.json`
3. **Data Format**: Include basic metadata and tool-specific data
4. **Auto-Discovery**: Dashboard will automatically find and load your tool

### Example Tool Data Format
```json
{
  "tool_specific_data": { ... },
  "summary_stats": { ... },
  "_metadata": {
    "tool_name": "your-tool",
    "run_date": "2025-06-30",
    "tool_type": "your-tool-type"
  }
}
```

## 🛠️ Technical Details

### Data Loader (`data_loader.py`)
- **Tool Discovery**: Scans `tools/*/results/` for available data
- **Format Detection**: Identifies tool types by data structure
- **Data Standardization**: Normalizes different data formats
- **Caching**: Efficient loading and caching of results

### Dashboard (`dashboard.py`)
- **Modular Design**: Tool-specific rendering based on detected type
- **Real-time Updates**: Dynamic content based on tool/run selection
- **Error Handling**: Graceful handling of missing or invalid data
- **Theme System**: CSS custom properties for theming

## 🔄 Migration Notes

### Backwards Compatibility
- **IntentCrawler**: Remains fully functional in its original location
- **No Breaking Changes**: All existing workflows continue to work
- **Gradual Migration**: Use either dashboard as needed
- **Data Preservation**: All existing results remain accessible

### File Structure
- **Original**: `intentcrawler/src/dashboard.py` (still works)
- **New**: `dashboard/dashboard.py` (master dashboard)
- **Data**: Same location (`intentcrawler/results/`) 
- **Assets**: Copied and enhanced in `dashboard/assets/`

## 🎯 Benefits

1. **Centralized View**: One dashboard for all AI tools
2. **Consistent UX**: Same professional interface across tools
3. **Easy Tool Addition**: Standardized integration pattern
4. **Independent Tools**: Each tool remains self-contained
5. **Future-Proof**: Scalable architecture for tool suite growth

## 🚦 Status

- ✅ **Architecture**: Complete and tested
- ✅ **IntentCrawler Integration**: Fully working
- ✅ **Theme System**: Light/dark mode implemented
- ✅ **Data Loading**: Multi-tool support ready
- 🔄 **Tool Addition**: Ready for new tools
- 📋 **Documentation**: Complete

## 🔗 Related Files

- `intentcrawler/src/dashboard.py` - Original tool-specific dashboard
- `intentcrawler/results/` - Data source for intentcrawler
- `dashboard/assets/` - Shared styling and theme system

---

*Part of the Airbais AI Tools Suite - Professional tools for AI-powered analysis*