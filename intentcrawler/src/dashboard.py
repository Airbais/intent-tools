import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
from typing import Dict, List
import logging

class IntentDashboard:
    def __init__(self, data_file: str = None):
        # Get the assets folder path
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_folder = os.path.join(os.path.dirname(current_dir), 'assets')
        
        self.app = dash.Dash(__name__, assets_folder=assets_folder)
        self.data_file = data_file
        self.data = None
        self.logger = logging.getLogger(__name__)
        
        if data_file:
            self.load_data(data_file)
        
        self.setup_layout()
        self.setup_callbacks()
    
    def load_data(self, data_file: str):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load data from {data_file}: {e}")
            self.data = {}
    
    def setup_layout(self):
        # Extract date from data file path if available
        results_date = "Unknown"
        if self.data_file:
            path_parts = os.path.normpath(self.data_file).split(os.sep)
            # Look for date pattern in path
            for part in path_parts:
                if len(part) == 10 and part.count('-') == 2:  # YYYY-MM-DD format
                    results_date = part
                    break
        
        self.app.layout = html.Div([
            # Theme Toggle Button
            html.Div([
                html.Span("🌙", className="theme-icon", id="theme-icon"),
                html.Span("Dark", id="theme-text")
            ], className="theme-toggle", id="theme-toggle"),
            
            # Header
            html.Div([
                html.H1("Website Intent Analysis Dashboard"),
                html.P(f"Results from: {results_date}", className="dashboard-subtitle")
            ], className="dashboard-header fade-in"),
            
            # Overview Stats
            html.Div(id="overview-stats", className="stats-container fade-in"),
            
            # Export Section
            html.Div([
                html.Div([
                    html.H3("Data Export", className="section-title"),
                    html.P("Export your analysis data in various formats", className="text-muted")
                ], className="section-header"),
                html.Div([
                    html.Button("Export JSON", id="export-json-btn", className="btn btn-primary"),
                    html.Button("Export Summary", id="export-summary-btn", className="btn btn-secondary"),
                ], className="export-buttons"),
                html.Div(id="export-status", className="mt-2")
            ], className="export-section fade-in"),
            
            # Intent Distribution Chart
            html.Div([
                html.H3("Intent Distribution", className="chart-title"),
                dcc.Graph(id="intent-distribution-chart", className="fade-in")
            ], className="chart-container fade-in"),
            
            # Intents by Section
            html.Div([
                html.H3("Intents by Section", className="chart-title"),
                html.Div([
                    dcc.Dropdown(
                        id="section-dropdown",
                        placeholder="Select a section to analyze...",
                        className="section-dropdown"
                    )
                ], style={'marginBottom': '20px'}),
                dcc.Graph(id="section-intent-chart", className="fade-in")
            ], className="chart-container fade-in"),
            
            # Intent Details Table
            html.Div([
                html.Div(id="intent-details-table", className="fade-in")
            ], className="card fade-in"),
            
            # Site Structure Chart
            html.Div([
                html.H3("Site Structure Analysis", className="chart-title"),
                dcc.Graph(id="site-structure-chart", className="fade-in")
            ], className="chart-container fade-in")
        ], className="container-fluid")
    
    def setup_callbacks(self):
        @self.app.callback(
            Output('overview-stats', 'children'),
            Input('overview-stats', 'id')
        )
        def update_overview_stats(_):
            if not self.data:
                return html.P("No data available")
            
            intents = self.data.get('discovered_intents', [])
            total_pages = self.data.get('total_pages_analyzed', 0)
            total_intents = len(intents)
            
            sections = self.data.get('by_section', {})
            total_sections = len(sections)
            
            return [
                html.Div([
                    html.Div(str(total_pages), className="stat-number"),
                    html.Div("Total Pages", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_intents), className="stat-number"),
                    html.Div("Discovered Intents", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_sections), className="stat-number"),
                    html.Div("Site Sections", className="stat-label")
                ], className="stat-card")
            ]
        
        @self.app.callback(
            Output('intent-distribution-chart', 'figure'),
            Input('intent-distribution-chart', 'id')
        )
        def update_intent_distribution(_):
            if not self.data or 'discovered_intents' not in self.data:
                return go.Figure()
            
            intents = self.data['discovered_intents']
            
            df = pd.DataFrame([
                {
                    'intent': intent['primary_intent'],
                    'pages': intent['page_count'],
                    'confidence': intent['confidence']
                }
                for intent in intents
            ])
            
            if df.empty:
                return go.Figure()
            
            fig = px.bar(
                df, 
                x='intent', 
                y='pages',
                color='confidence',
                labels={'pages': 'Number of Pages', 'intent': 'Intent Type'},
                color_continuous_scale=['#FFA940', '#F78D1F', '#D97706']
            )
            
            fig.update_layout(
                xaxis_tickangle=-45,
                font=dict(family="Inter, sans-serif"),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    gridcolor='rgba(0,0,0,0.05)',
                    linecolor='rgba(0,0,0,0.1)'
                ),
                yaxis=dict(
                    gridcolor='rgba(0,0,0,0.05)',
                    linecolor='rgba(0,0,0,0.1)'
                ),
                showlegend=True,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            return fig
        
        @self.app.callback(
            [Output('section-dropdown', 'options'),
             Output('section-dropdown', 'value')],
            Input('section-dropdown', 'id')
        )
        def update_section_dropdown(_):
            if not self.data or 'by_section' not in self.data:
                return [], None
            
            sections = list(self.data['by_section'].keys())
            options = [{'label': section.title(), 'value': section} for section in sections]
            
            return options, sections[0] if sections else None
        
        @self.app.callback(
            Output('section-intent-chart', 'figure'),
            Input('section-dropdown', 'value')
        )
        def update_section_intent_chart(selected_section):
            if not self.data or not selected_section or 'by_section' not in self.data:
                return go.Figure()
            
            section_data = self.data['by_section'].get(selected_section, [])
            
            if not section_data:
                return go.Figure()
            
            df = pd.DataFrame(section_data)
            
            intent_counts = df['intent'].value_counts()
            
            fig = px.pie(
                values=intent_counts.values,
                names=intent_counts.index,
                color_discrete_sequence=['#F78D1F', '#FFA940', '#D97706', '#FFD93D', '#FF6B35', '#F59E0B', '#DC2626', '#EF4444']
            )
            
            fig.update_layout(
                font=dict(family="Inter, sans-serif"),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=True,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            return fig
        
        @self.app.callback(
            Output('intent-details-table', 'children'),
            Input('section-dropdown', 'value')
        )
        def update_intent_details_table(selected_section):
            if not self.data:
                return html.P("No data available")
            
            if selected_section and 'by_section' in self.data:
                section_data = self.data['by_section'].get(selected_section, [])
                title = f"Intent Details for {selected_section.title()} Section"
            else:
                section_data = self.data.get('discovered_intents', [])
                title = "All Discovered Intents"
            
            if not section_data:
                return html.P("No intents found for this section")
            
            table_rows = []
            
            if selected_section:
                for item in section_data:
                    table_rows.append(html.Tr([
                        html.Td(item.get('intent', 'Unknown')),
                        html.Td(f"{item.get('confidence', 0):.2f}"),
                        html.Td(', '.join(item.get('keywords', [])[:3])),
                        html.Td(item.get('page_title', 'Unknown'))
                    ]))
            else:
                for intent in section_data:
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
                    html.Th("Pages" if not selected_section else "Page Title")
                ])
            ])
            
            body = html.Tbody(table_rows)
            
            table = html.Table([header, body], className="table table-striped")
            
            return html.Div([
                html.H4(title),
                table
            ])
        
        @self.app.callback(
            Output('site-structure-chart', 'figure'),
            Input('site-structure-chart', 'id')
        )
        def update_site_structure_chart(_):
            if not self.data or 'by_section' not in self.data:
                return go.Figure()
            
            sections = self.data['by_section']
            
            section_names = list(sections.keys())
            intent_counts = [len(section_intents) for section_intents in sections.values()]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=section_names,
                y=intent_counts,
                name='Intents per Section',
                marker_color='#F78D1F',
                marker_line_width=0,
                hovertemplate='<b>%{x}</b><br>Intents: %{y}<extra></extra>'
            ))
            
            fig.update_layout(
                xaxis_title="Site Sections",
                yaxis_title="Number of Intents",
                xaxis_tickangle=-45,
                font=dict(family="Inter, sans-serif"),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    gridcolor='rgba(0,0,0,0.05)',
                    linecolor='rgba(0,0,0,0.1)'
                ),
                yaxis=dict(
                    gridcolor='rgba(0,0,0,0.05)',
                    linecolor='rgba(0,0,0,0.1)'
                ),
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                hoverlabel=dict(
                    bgcolor="#F78D1F",
                    font_size=14,
                    font_family="Inter, sans-serif"
                )
            )
            
            return fig
        
        @self.app.callback(
            Output('export-status', 'children'),
            [Input('export-json-btn', 'n_clicks'),
             Input('export-summary-btn', 'n_clicks')]
        )
        def handle_export(json_clicks, summary_clicks):
            if not json_clicks and not summary_clicks:
                return ""
            
            ctx = dash.callback_context
            if not ctx.triggered:
                return ""
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id == 'export-json-btn':
                return html.Div([
                    html.P("JSON export ready for download", className="status-success"),
                    html.Small("In a full implementation, this would download the JSON data", className="text-muted")
                ])
            elif button_id == 'export-summary-btn':
                return html.Div([
                    html.P("Summary report generated successfully", className="status-success"),
                    html.Small("In a full implementation, this would generate a PDF summary", className="text-muted")
                ])
            
            return ""
        
        # Theme toggle callback
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
        
        # Add client-side callback for theme persistence
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
    
    def run(self, debug: bool = True, port: int = 8050, host: str = '127.0.0.1'):
        self.logger.info(f"Starting dashboard on http://{host}:{port}")
        self.app.run(debug=debug, port=port, host=host)