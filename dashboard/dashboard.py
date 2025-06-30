"""
Master Dashboard for Multiple AI Tools
Centralized dashboard that can display results from any tool in the suite
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
from typing import Dict, List, Optional
import logging
from pathlib import Path

from data_loader import ToolDataLoader

class MasterDashboard:
    def __init__(self, tools_root_path: str = None):
        # Get the assets folder path
        current_dir = Path(__file__).parent
        assets_folder = str(current_dir / 'assets')
        
        self.app = dash.Dash(__name__, assets_folder=assets_folder)
        self.data_loader = ToolDataLoader(tools_root_path)
        self.current_data = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize available tools and runs
        self.available_tools = self.data_loader.discover_tools()
        self.available_data = self.data_loader.get_available_data()
        
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        # Get available tools for dropdown
        tool_options = []
        for tool in self.available_tools:
            tool_options.append({'label': tool.title().replace('_', ' '), 'value': tool})
        
        # If no tools available, show a message
        if not tool_options:
            tool_options = [{'label': 'No tools found', 'value': 'none'}]
        
        self.app.layout = html.Div([
            # Theme Toggle Button
            html.Div([
                html.Span("🌙", className="theme-icon", id="theme-icon"),
                html.Span("Dark", id="theme-text")
            ], className="theme-toggle", id="theme-toggle"),
            
            # Header
            html.Div([
                html.H1("AI Tools Master Dashboard"),
                html.P("Centralized view of all AI tool results", className="dashboard-subtitle")
            ], className="dashboard-header fade-in"),
            
            # Tool Selection
            html.Div([
                html.Div([
                    html.H3("Tool Selection", className="section-title"),
                    html.P("Select a tool and run to analyze", className="text-muted")
                ], className="section-header"),
                html.Div([
                    html.Div([
                        html.Label("Tool:", className="form-label"),
                        dcc.Dropdown(
                            id="tool-dropdown",
                            options=tool_options,
                            value=self.available_tools[0] if self.available_tools else 'none',
                            placeholder="Select a tool...",
                            className="tool-dropdown"
                        )
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        html.Label("Run Date:", className="form-label"),
                        dcc.Dropdown(
                            id="run-dropdown",
                            placeholder="Select a run...",
                            className="run-dropdown"
                        )
                    ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'})
                ], style={'marginBottom': '20px'}),
                
                html.Div(id="tool-info", className="mt-3")
            ], className="export-section fade-in"),
            
            # Overview Stats
            html.Div(id="overview-stats", className="stats-container fade-in"),
            
            # Main Content Area (will be populated based on tool type)
            html.Div(id="main-content", className="fade-in")
            
        ], className="container-fluid")
    
    def setup_callbacks(self):
        # Tool selection callback
        @self.app.callback(
            [Output('run-dropdown', 'options'),
             Output('run-dropdown', 'value'),
             Output('tool-info', 'children')],
            Input('tool-dropdown', 'value')
        )
        def update_run_dropdown(selected_tool):
            if not selected_tool or selected_tool == 'none':
                return [], None, html.P("No tool selected", className="text-muted")
            
            runs = self.data_loader.get_tool_runs(selected_tool)
            
            if not runs:
                return [], None, html.Div([
                    html.P(f"No data found for {selected_tool}", className="text-muted"),
                    html.Small("Make sure the tool has been run and has results in its results/ folder")
                ])
            
            run_options = [{'label': f"{run[0]} ({run[1].strftime('%B %d, %Y')})", 'value': run[0]} for run in runs]
            
            tool_info = html.Div([
                html.P(f"Found {len(runs)} runs for {selected_tool.title()}", className="text-success"),
                html.Small(f"Latest run: {runs[0][1].strftime('%B %d, %Y')}", className="text-muted")
            ])
            
            return run_options, runs[0][0] if runs else None, tool_info
        
        # Data loading callback
        @self.app.callback(
            [Output('overview-stats', 'children'),
             Output('main-content', 'children')],
            [Input('tool-dropdown', 'value'),
             Input('run-dropdown', 'value')]
        )
        def update_dashboard_content(selected_tool, selected_run):
            if not selected_tool or not selected_run or selected_tool == 'none':
                return self._empty_stats(), self._empty_content()
            
            # Load the data
            data = self.data_loader.load_tool_data(selected_tool, selected_run)
            if not data:
                return self._empty_stats(), html.Div([
                    html.P("Failed to load data", className="text-danger"),
                    html.Small("Check that the data file exists and is valid JSON")
                ])
            
            self.current_data = data
            metadata = data.get('_metadata', {})
            tool_type = metadata.get('tool_type', 'unknown')
            
            # Generate content based on tool type
            stats = self._generate_stats(data, tool_type)
            content = self._generate_content(data, tool_type)
            
            return stats, content
        
        # Theme toggle callbacks (same as before)
        @self.app.callback(
            [Output('theme-icon', 'children'),
             Output('theme-text', 'children')],
            Input('theme-toggle', 'n_clicks'),
            prevent_initial_call=True
        )
        def toggle_theme(n_clicks):
            if n_clicks and n_clicks % 2 == 1:
                return "☀️", "Light"
            else:
                return "🌙", "Dark"
        
        self.app.clientside_callback(
            """
            function(n_clicks) {
                const html = document.documentElement;
                const currentTheme = html.getAttribute('data-theme') || 'light';
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                return window.dash_clientside.no_update;
            }
            """,
            Output('theme-toggle', 'style'),
            Input('theme-toggle', 'n_clicks'),
            prevent_initial_call=True
        )
    
    def _empty_stats(self):
        return html.Div([
            html.Div([
                html.Div("--", className="stat-number"),
                html.Div("Select Tool", className="stat-label")
            ], className="stat-card")
        ])
    
    def _empty_content(self):
        return html.Div([
            html.Div([
                html.H3("Welcome to the AI Tools Dashboard"),
                html.P("Select a tool and run from the dropdowns above to view results."),
                html.Hr(),
                html.H4("Available Tools:"),
                html.Ul([
                    html.Li(tool.title().replace('_', ' ')) for tool in self.available_tools
                ] if self.available_tools else [html.Li("No tools found")])
            ], className="card")
        ])
    
    def _generate_stats(self, data: Dict, tool_type: str) -> List:
        """Generate overview statistics based on tool type"""
        
        if tool_type == 'intentcrawler':
            total_pages = data.get('total_pages_analyzed', 0)
            total_intents = data.get('total_intents_discovered', 0)
            total_sections = len(data.get('by_section', {}))
            
            return [
                html.Div([
                    html.Div(str(total_pages), className="stat-number"),
                    html.Div("Pages Analyzed", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_intents), className="stat-number"),
                    html.Div("Intents Discovered", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_sections), className="stat-number"),
                    html.Div("Site Sections", className="stat-label")
                ], className="stat-card")
            ]
        
        # Default stats for unknown tools
        return [
            html.Div([
                html.Div("✓", className="stat-number"),
                html.Div("Data Loaded", className="stat-label")
            ], className="stat-card")
        ]
    
    def _generate_content(self, data: Dict, tool_type: str) -> html.Div:
        """Generate main content based on tool type"""
        
        if tool_type == 'intentcrawler':
            return self._generate_intentcrawler_content(data)
        
        # Default content for unknown tools
        return html.Div([
            html.Div([
                html.H3("Raw Data View"),
                html.P(f"Tool type: {tool_type}"),
                html.Pre(json.dumps(data, indent=2)[:1000] + "..." if len(str(data)) > 1000 else json.dumps(data, indent=2),
                        style={'background': 'var(--gray-100)', 'padding': '1rem', 'border-radius': '0.5rem', 'overflow': 'auto'})
            ], className="card")
        ])
    
    def _generate_intentcrawler_content(self, data: Dict) -> html.Div:
        """Generate content specific to intentcrawler results"""
        
        intents = data.get('discovered_intents', [])
        sections = data.get('by_section', {})
        
        # Intent Distribution Chart
        if intents:
            df = pd.DataFrame([
                {
                    'intent': intent.get('primary_intent', 'Unknown'),
                    'pages': intent.get('page_count', 0),
                    'confidence': intent.get('confidence', 0)
                }
                for intent in intents
            ])
            
            intent_chart = dcc.Graph(
                figure=px.bar(
                    df, 
                    x='intent', 
                    y='pages',
                    color='confidence',
                    labels={'pages': 'Number of Pages', 'intent': 'Intent Type'},
                    color_continuous_scale=['#FFA940', '#F78D1F', '#D97706']
                ).update_layout(
                    xaxis_tickangle=-45,
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=30, b=0)
                )
            )
        else:
            intent_chart = html.P("No intent data available")
        
        # Site Structure Chart
        if sections:
            section_names = list(sections.keys())
            intent_counts = [len(section_intents) for section_intents in sections.values()]
            
            structure_chart = dcc.Graph(
                figure=go.Figure().add_trace(go.Bar(
                    x=section_names,
                    y=intent_counts,
                    marker_color='#F78D1F',
                    hovertemplate='<b>%{x}</b><br>Intents: %{y}<extra></extra>'
                )).update_layout(
                    xaxis_title="Site Sections",
                    yaxis_title="Number of Intents",
                    xaxis_tickangle=-45,
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=30, b=0)
                )
            )
        else:
            structure_chart = html.P("No section data available")
        
        return html.Div([
            # Intent Distribution
            html.Div([
                html.H3("Intent Distribution", className="chart-title"),
                intent_chart
            ], className="chart-container"),
            
            # Site Structure
            html.Div([
                html.H3("Site Structure Analysis", className="chart-title"),
                structure_chart
            ], className="chart-container"),
            
            # Intent Details Table
            html.Div([
                html.H3("Discovered Intents"),
                self._create_intents_table(intents)
            ], className="card")
        ])
    
    def _create_intents_table(self, intents: List[Dict]) -> html.Table:
        """Create a table of discovered intents"""
        
        if not intents:
            return html.P("No intents discovered")
        
        table_rows = []
        for intent in intents:
            table_rows.append(html.Tr([
                html.Td(intent.get('primary_intent', 'Unknown')),
                html.Td(f"{intent.get('confidence', 0):.2f}"),
                html.Td(', '.join(intent.get('keywords', [])[:3])),
                html.Td(str(intent.get('page_count', 0)))
            ]))
        
        header = html.Thead([
            html.Tr([
                html.Th("Intent"),
                html.Th("Confidence"),
                html.Th("Keywords"),
                html.Th("Pages")
            ])
        ])
        
        body = html.Tbody(table_rows)
        
        return html.Table([header, body], className="table table-striped")
    
    def run(self, debug: bool = True, port: int = 8050, host: str = '127.0.0.1'):
        self.logger.info(f"Starting master dashboard on http://{host}:{port}")
        self.logger.info(f"Available tools: {', '.join(self.available_tools) if self.available_tools else 'None'}")
        self.app.run(debug=debug, port=port, host=host)

def main():
    """Main entry point for the master dashboard"""
    dashboard = MasterDashboard()
    dashboard.run()

if __name__ == '__main__':
    main()