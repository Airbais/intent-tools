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
        self.app = dash.Dash(__name__)
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
            html.H1("Website Intent Analysis Dashboard", className="text-center mb-4"),
            html.P(f"Results from: {results_date}", className="text-center text-muted mb-3"),
            
            html.Div([
                html.Div([
                    html.H3("Overview"),
                    html.Div(id="overview-stats")
                ], className="col-md-6"),
                
                html.Div([
                    html.H3("Data Export"),
                    html.Button("Export JSON", id="export-json-btn", className="btn btn-primary me-2"),
                    html.Button("Export Summary", id="export-summary-btn", className="btn btn-secondary"),
                    html.Div(id="export-status", className="mt-2")
                ], className="col-md-6")
            ], className="row mb-4"),
            
            html.Div([
                html.H3("Intent Distribution"),
                dcc.Graph(id="intent-distribution-chart")
            ], className="mb-4"),
            
            html.Div([
                html.H3("Intents by Section"),
                dcc.Dropdown(
                    id="section-dropdown",
                    placeholder="Select a section...",
                    className="mb-3"
                ),
                dcc.Graph(id="section-intent-chart")
            ], className="mb-4"),
            
            html.Div([
                html.H3("Intent Details"),
                html.Div(id="intent-details-table")
            ], className="mb-4"),
            
            html.Div([
                html.H3("Site Structure"),
                dcc.Graph(id="site-structure-chart")
            ], className="mb-4")
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
            
            return html.Div([
                html.Div([
                    html.H4(str(total_pages), className="text-primary"),
                    html.P("Total Pages")
                ], className="text-center mb-3"),
                
                html.Div([
                    html.H4(str(total_intents), className="text-success"),
                    html.P("Discovered Intents")
                ], className="text-center mb-3"),
                
                html.Div([
                    html.H4(str(total_sections), className="text-info"),
                    html.P("Site Sections")
                ], className="text-center mb-3")
            ])
        
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
                title="Intent Distribution Across Pages",
                labels={'pages': 'Number of Pages', 'intent': 'Intent Type'}
            )
            
            fig.update_layout(xaxis_tickangle=-45)
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
                title=f"Intent Distribution in {selected_section.title()} Section"
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
                marker_color='lightblue'
            ))
            
            fig.update_layout(
                title="Site Structure: Intents by Section",
                xaxis_title="Site Sections",
                yaxis_title="Number of Intents",
                xaxis_tickangle=-45
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
                    html.P("JSON export would be triggered here", className="text-success"),
                    html.Small("In a full implementation, this would download the JSON data")
                ])
            elif button_id == 'export-summary-btn':
                return html.Div([
                    html.P("Summary export would be triggered here", className="text-success"),
                    html.Small("In a full implementation, this would generate a PDF summary")
                ])
            
            return ""
    
    def run(self, debug: bool = True, port: int = 8050, host: str = '127.0.0.1'):
        self.logger.info(f"Starting dashboard on http://{host}:{port}")
        self.app.run(debug=debug, port=port, host=host)