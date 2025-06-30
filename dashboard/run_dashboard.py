#!/usr/bin/env python3
"""
Master Dashboard Launcher
Simple script to start the multi-tool dashboard
"""

import sys
import os
from pathlib import Path

# Add the dashboard directory to Python path
dashboard_dir = Path(__file__).parent
sys.path.insert(0, str(dashboard_dir))

from dashboard import MasterDashboard

def main():
    print("🚀 Starting AI Tools Master Dashboard...")
    print("📁 Scanning for available tools...")
    
    dashboard = MasterDashboard()
    
    # Show discovered tools
    if dashboard.available_tools:
        print(f"✅ Found {len(dashboard.available_tools)} tools:")
        for tool in dashboard.available_tools:
            runs = len(dashboard.available_data.get(tool, []))
            print(f"   • {tool.title().replace('_', ' ')}: {runs} runs available")
    else:
        print("⚠️  No tools found. Make sure tools have 'results' folders with data.")
    
    print("\n🌐 Dashboard will be available at: http://127.0.0.1:8050")
    print("💡 Use the dropdowns to select a tool and run date")
    print("🎨 Click the theme toggle (🌙/☀️) to switch light/dark mode")
    print("\nPress Ctrl+C to stop the dashboard\n")
    
    try:
        dashboard.run(debug=False)  # Set to False for production
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped. Thanks for using AI Tools!")

if __name__ == '__main__':
    main()