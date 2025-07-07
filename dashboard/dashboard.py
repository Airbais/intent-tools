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
        
        elif tool_type == 'llmevaluator':
            metrics = data.get('aggregate_metrics', {})
            total_prompts = metrics.get('total_prompts', 0)
            brand_mentions = metrics.get('total_brand_mentions', 0)
            avg_sentiment = metrics.get('average_sentiment', 0)
            mention_rate = metrics.get('mention_rate', 0)
            
            return [
                html.Div([
                    html.Div(str(total_prompts), className="stat-number"),
                    html.Div("Prompts Evaluated", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(brand_mentions), className="stat-number"),
                    html.Div("Brand Mentions", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(f"{avg_sentiment:.2f}", className="stat-number"),
                    html.Div("Avg Sentiment", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(f"{mention_rate:.1f}", className="stat-number"),
                    html.Div("Mentions/Prompt", className="stat-label")
                ], className="stat-card")
            ]
        
        elif tool_type == 'geoevaluator':
            overall_score = data.get('overall_score', {})
            total_score = overall_score.get('total_score', 0)
            grade = overall_score.get('grade', 'Unknown')
            pages_analyzed = data.get('_metadata', {}).get('pages_analyzed', 0)
            recommendations = len(data.get('recommendations', []))
            
            return [
                html.Div([
                    html.Div(f"{total_score:.1f}", className="stat-number"),
                    html.Div("Overall Score", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(grade, className="stat-number"),
                    html.Div("Grade", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(pages_analyzed), className="stat-number"),
                    html.Div("Pages Analyzed", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(recommendations), className="stat-number"),
                    html.Div("Recommendations", className="stat-label")
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
        elif tool_type == 'llmevaluator':
            return self._generate_llmevaluator_content(data)
        elif tool_type == 'geoevaluator':
            return self._generate_geoevaluator_content(data)
        
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
    
    def _generate_llmevaluator_content(self, data: Dict) -> html.Div:
        """Generate content specific to llmevaluator results"""
        
        brand_info = data.get('brand_info', {})
        metrics = data.get('aggregate_metrics', {})
        evaluation_results = data.get('evaluation_results', [])
        insights = data.get('insights', [])
        metadata = data.get('_metadata', {})
        
        # Check if this is multi-LLM format
        is_multi_llm = metadata.get('format') == 'multi_llm'
        
        # Brand Information Summary with enhanced metrics
        brand_summary_content = [
            html.P([html.Strong("Brand: "), brand_info.get('name', 'Unknown')]),
            html.P([html.Strong("Website: "), html.A(brand_info.get('website', ''), href=brand_info.get('website', ''), target="_blank")])
        ]
        
        if is_multi_llm:
            # Multi-LLM format - add contextual metrics
            llms = metadata.get('llms', [])
            if llms:
                llm_info = f"{len(llms)} LLMs: " + ", ".join([f"{llm['name']} ({llm['model']})" for llm in llms])
                brand_summary_content.append(html.P([html.Strong("LLMs: "), llm_info]))
            
            # Add contextual metrics
            total_mentions = metrics.get('total_brand_mentions', 0)
            total_evaluations = metrics.get('total_prompts', 0) * len(llms) if llms else 0
            avg_sentiment = metrics.get('average_sentiment', 0)
            mention_rate = metrics.get('mention_rate', 0)
            
            brand_summary_content.extend([
                html.P([html.Strong("Total Evaluations: "), f"{total_evaluations} responses ({metrics.get('total_prompts', 0)} prompts × {len(llms)} LLMs)"]),
                html.P([html.Strong("Brand Mentions: "), f"{total_mentions} out of {total_evaluations} responses ({(total_mentions/total_evaluations*100):.1f}%)" if total_evaluations > 0 else "0"]),
                html.P([html.Strong("Average Sentiment: "), f"{avg_sentiment:.2f} (scale: -1.0 negative to +1.0 positive)"]),
                html.P([html.Strong("Mentions per Prompt: "), f"{mention_rate:.2f}"])
            ])
            
            # Show evaluation date from metadata
            if 'comparative_metrics' in data:
                timestamp = data.get('metadata', {}).get('timestamp', '')
                if timestamp:
                    eval_date = timestamp.split('T')[0]
                    brand_summary_content.append(html.P([html.Strong("Evaluation Date: "), eval_date]))
        else:
            # Old single-LLM format
            total_mentions = metrics.get('total_brand_mentions', 0)
            total_prompts = metrics.get('total_prompts', 0)
            avg_sentiment = metrics.get('average_sentiment', 0)
            
            brand_summary_content.extend([
                html.P([html.Strong("LLM Provider: "), f"{brand_info.get('llm_provider', 'Unknown')} ({brand_info.get('llm_model', 'Unknown')})"]),
                html.P([html.Strong("Brand Mentions: "), f"{total_mentions} out of {total_prompts} responses ({(total_mentions/total_prompts*100):.1f}%)" if total_prompts > 0 else "0"]),
                html.P([html.Strong("Average Sentiment: "), f"{avg_sentiment:.2f} (scale: -1.0 negative to +1.0 positive)"]),
                html.P([html.Strong("Evaluation Date: "), brand_info.get('evaluation_date', '').split('T')[0] if brand_info.get('evaluation_date') else 'Unknown'])
            ])
        
        brand_summary = html.Div([
            html.H3("Brand Evaluation Summary"),
            html.Div(brand_summary_content, style={'padding': '1rem'})
        ], className="card")
        
        # Sentiment Distribution Chart
        sentiment_chart = None
        sentiment_dist = metrics.get('sentiment_distribution', {})
        if sentiment_dist:
            df_sentiment = pd.DataFrame([
                {'sentiment': sentiment, 'count': count}
                for sentiment, count in sentiment_dist.items()
            ])
            
            sentiment_chart = dcc.Graph(
                figure=px.pie(
                    df_sentiment,
                    values='count',
                    names='sentiment',
                    title="Brand Sentiment Distribution",
                    color_discrete_sequence=['#059669', '#DC2626', '#6B7280', '#9CA3AF']
                ).update_layout(
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=40, b=0)
                )
            )
        
        # Category Performance Chart
        category_chart = None
        categories = metrics.get('categories', {})
        if categories:
            df_categories = pd.DataFrame([
                {
                    'category': category,
                    'prompts': cat_data.get('prompts', 0),
                    'mentions': cat_data.get('mentions', 0),
                    'sentiment': cat_data.get('sentiment', 0)
                }
                for category, cat_data in categories.items()
            ])
            
            category_chart = dcc.Graph(
                figure=px.bar(
                    df_categories,
                    x='category',
                    y=['prompts', 'mentions'],
                    title="Performance by Category",
                    labels={'value': 'Count', 'variable': 'Metric'},
                    color_discrete_sequence=['#3B82F6', '#10B981']
                ).update_layout(
                    xaxis_tickangle=-45,
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=40, b=0),
                    barmode='group'
                )
            )
        
        # Summary Charts for Multi-LLM
        summary_charts = []
        
        if is_multi_llm:
            original_data = data.get('llm_metrics', {})
            if original_data:
                # Brand Mentions Overview Chart
                mentions_data = []
                for llm_name, llm_metrics in original_data.items():
                    mentions = llm_metrics.get('total_brand_mentions', 0)
                    prompts = llm_metrics.get('total_prompts', 0)
                    mentions_data.append({
                        'LLM': llm_name,
                        'Brand Mentions': mentions,
                        'No Mentions': prompts - mentions
                    })
                
                df_mentions = pd.DataFrame(mentions_data)
                mentions_chart = dcc.Graph(
                    figure=px.bar(
                        df_mentions,
                        x='LLM',
                        y=['Brand Mentions', 'No Mentions'],
                        title="Brand Mentions vs No Mentions by LLM",
                        labels={'value': 'Number of Responses', 'variable': 'Response Type'},
                        color_discrete_sequence=['#10B981', '#E5E7EB']
                    ).update_layout(
                        font=dict(family="Inter, sans-serif"),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=40, b=0),
                        barmode='stack'
                    )
                )
                
                # Sentiment Comparison Chart  
                sentiment_data = []
                for llm_name, llm_metrics in original_data.items():
                    sentiment = llm_metrics.get('average_sentiment', 0)
                    sentiment_data.append({
                        'LLM': llm_name,
                        'Sentiment Score': sentiment
                    })
                
                df_sentiment_comp = pd.DataFrame(sentiment_data)
                sentiment_comparison_chart = dcc.Graph(
                    figure=px.bar(
                        df_sentiment_comp,
                        x='LLM',
                        y='Sentiment Score',
                        title="Average Sentiment Score by LLM",
                        labels={'Sentiment Score': 'Sentiment Score (-1.0 to +1.0)'},
                        color='Sentiment Score',
                        color_continuous_scale=['#DC2626', '#6B7280', '#059669'],
                        range_color=[-1, 1]
                    ).update_layout(
                        font=dict(family="Inter, sans-serif"),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                )
                
                summary_charts = [
                    html.Div([
                        html.H3("Brand Mentions Overview"),
                        mentions_chart
                    ], className="card"),
                    html.Div([
                        html.H3("Sentiment Comparison"),
                        sentiment_comparison_chart
                    ], className="card")
                ]
        
        # Multi-LLM specific charts
        llm_comparison_chart = None
        comparative_metrics_section = None
        
        if is_multi_llm:
            # LLM Comparison Chart
            original_data = data.get('llm_metrics', {})
            if original_data:
                llm_comparison_data = []
                for llm_name, llm_metrics in original_data.items():
                    llm_comparison_data.append({
                        'LLM': llm_name,
                        'Mention Rate': llm_metrics.get('mention_rate', 0),
                        'Sentiment Score': llm_metrics.get('average_sentiment', 0),
                        'Total Mentions': llm_metrics.get('total_brand_mentions', 0)
                    })
                
                df_comparison = pd.DataFrame(llm_comparison_data)
                
                llm_comparison_chart = dcc.Graph(
                    figure=px.bar(
                        df_comparison,
                        x='LLM',
                        y=['Mention Rate', 'Sentiment Score'],
                        title="LLM Performance Comparison",
                        labels={'value': 'Score', 'variable': 'Metric'},
                        color_discrete_sequence=['#8B5CF6', '#F59E0B']
                    ).update_layout(
                        font=dict(family="Inter, sans-serif"),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(l=0, r=0, t=40, b=0),
                        barmode='group'
                    )
                )
            
            # LLM Performance Comparison Table
            original_data = data.get('llm_metrics', {})
            if original_data:
                # Create comparison table
                llm_comparison_rows = []
                for llm_name, llm_metrics in original_data.items():
                    mentions = llm_metrics.get('total_brand_mentions', 0)
                    prompts = llm_metrics.get('total_prompts', 0)
                    sentiment = llm_metrics.get('average_sentiment', 0)
                    mention_rate = llm_metrics.get('mention_rate', 0)
                    
                    # Sentiment description
                    if sentiment > 0.3:
                        sentiment_desc = "Positive"
                        sentiment_color = "#059669"
                    elif sentiment < -0.3:
                        sentiment_desc = "Negative" 
                        sentiment_color = "#DC2626"
                    else:
                        sentiment_desc = "Neutral"
                        sentiment_color = "#6B7280"
                    
                    llm_comparison_rows.append(
                        html.Tr([
                            html.Td(llm_name, style={'font-weight': 'bold'}),
                            html.Td(f"{mentions}"),
                            html.Td(f"{mentions}/{prompts} ({(mentions/prompts*100):.1f}%)" if prompts > 0 else "0"),
                            html.Td([
                                html.Span(f"{sentiment:.2f}", style={'color': sentiment_color, 'font-weight': 'bold'}),
                                html.Br(),
                                html.Small(sentiment_desc, style={'color': sentiment_color})
                            ]),
                            html.Td(f"{mention_rate:.2f}")
                        ])
                    )
                
                comparison_table = html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("LLM"),
                            html.Th("Total Mentions"),
                            html.Th("Mention Rate"),
                            html.Th("Avg Sentiment"),
                            html.Th("Mentions/Prompt")
                        ])
                    ]),
                    html.Tbody(llm_comparison_rows)
                ], className="table table-striped", style={'margin-top': '1rem'})
                
                comparative_metrics_section = html.Div([
                    html.H3("LLM Performance Comparison"),
                    html.P("Direct comparison of how each LLM performed on brand evaluation:", 
                           style={'margin-bottom': '1rem', 'color': '#6B7280'}),
                    comparison_table
                ], className="card")
        
        # Key Insights
        insights_content = []
        if is_multi_llm and isinstance(insights, dict):
            # Handle multi-LLM insights format
            if 'overall' in insights:
                insights_content.extend([html.Li(insight) for insight in insights['overall'][:3]])
            if 'comparative' in insights:
                insights_content.extend([html.Li(f"Comparative: {insight}") for insight in insights['comparative'][:2]])
        elif isinstance(insights, list):
            # Handle old format
            insights_content = [html.Li(insight) for insight in insights[:5]]
        
        insights_section = html.Div([
            html.H3("Key Insights"),
            html.Ul(insights_content)
        ], className="card") if insights_content else None
        
        # Evaluation Results Table  
        results_table = html.Div([
            html.H3("Evaluation Results"),
            self._create_evaluation_results_table(evaluation_results)
        ], className="card") if evaluation_results else None
        
        # Combine all sections
        sections = [brand_summary]
        
        # Add summary charts for multi-LLM
        if summary_charts:
            sections.extend(summary_charts)
        
        # Add multi-LLM specific sections
        if comparative_metrics_section:
            sections.append(comparative_metrics_section)
        
        if llm_comparison_chart:
            sections.append(html.Div([
                html.H3("LLM Performance Comparison"),
                llm_comparison_chart
            ], className="card"))
        
        if sentiment_chart:
            sections.append(html.Div([
                html.H3("Sentiment Analysis"),
                sentiment_chart
            ], className="card"))
        
        if category_chart:
            sections.append(html.Div([
                html.H3("Category Performance"),
                category_chart
            ], className="card"))
        
        if insights_section:
            sections.append(insights_section)
        
        if results_table:
            sections.append(results_table)
        
        return html.Div(sections)
    
    def _create_evaluation_results_table(self, results: List[Dict]) -> html.Table:
        """Create a table of evaluation results"""
        
        if not results:
            return html.P("No evaluation results found.")
        
        # Check if we have LLM information to show
        has_llm_info = any(result.get('llm_name') for result in results)
        
        # Table header
        header_columns = ["Category", "Prompt"]
        if has_llm_info:
            header_columns.append("LLM")
        header_columns.extend(["Brand Mentions", "Sentiment", "Response Excerpt"])
        
        header = html.Thead([
            html.Tr([html.Th(col) for col in header_columns])
        ])
        
        # Table rows
        table_rows = []
        for result in results[:20]:  # Limit to first 20 results
            analysis = result.get('response_analysis', {})
            
            # Build row cells dynamically
            row_cells = [
                html.Td(result.get('category', 'Unknown')),
                html.Td(result.get('prompt', '')[:100] + "..." if len(result.get('prompt', '')) > 100 else result.get('prompt', ''))
            ]
            
            # Add LLM column if we have LLM info
            if has_llm_info:
                llm_name = result.get('llm_name', 'Unknown')
                row_cells.append(html.Td(llm_name))
            
            # Add remaining columns
            row_cells.extend([
                html.Td(str(analysis.get('brand_mentions', 0))),
                html.Td([
                    html.Span(
                        analysis.get('sentiment_label', 'Unknown'),
                        style={
                            'color': '#059669' if analysis.get('sentiment_label') == 'positive' 
                                    else '#DC2626' if analysis.get('sentiment_label') == 'negative'
                                    else '#9CA3AF' if analysis.get('sentiment_label') == 'not_mentioned'
                                    else '#6B7280'
                        }
                    ),
                    html.Br(),
                    html.Small(f"({analysis.get('sentiment_score', 0):.2f})")
                ]),
                html.Td(result.get('response_excerpt', '')[:150] + "..." if len(result.get('response_excerpt', '')) > 150 else result.get('response_excerpt', ''))
            ])
            
            table_rows.append(html.Tr(row_cells))
        
        body = html.Tbody(table_rows)
        
        return html.Table([header, body], className="table table-striped")
    
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
    
    def _generate_geoevaluator_content(self, data: Dict) -> html.Div:
        """Generate content specific to geoevaluator results"""
        
        overall_score = data.get('overall_score', {})
        category_scores = overall_score.get('category_scores', {})
        recommendations = data.get('recommendations', [])
        page_scores = data.get('page_scores', [])
        benchmarks = data.get('benchmarks', {})
        metadata = data.get('_metadata', {})
        
        # Overall Score Summary
        total_score = overall_score.get('total_score', 0)
        grade = overall_score.get('grade', 'Unknown')
        website_url = metadata.get('website_url', '')
        website_name = metadata.get('website_name', '')
        
        summary_content = [
            html.H3("GEO Analysis Summary"),
            html.P([html.Strong("Website: "), html.A(website_name or website_url, href=website_url, target="_blank")]),
            html.P([html.Strong("Overall Score: "), f"{total_score}/100 ({grade})"]),
            html.P([html.Strong("Pages Analyzed: "), str(metadata.get('pages_analyzed', 0))]),
            html.P([html.Strong("Analysis Date: "), metadata.get('timestamp', '').split('T')[0] if metadata.get('timestamp') else 'Unknown'])
        ]
        
        summary_section = html.Div(summary_content, className="card")
        
        # Category Scores Chart
        if category_scores:
            categories = list(category_scores.keys())
            scores = list(category_scores.values())
            
            # Create readable category names
            category_display_names = {
                'structural_html': 'Structural HTML',
                'content_organization': 'Content Organization',
                'token_efficiency': 'Token Efficiency',
                'llm_technical': 'LLM Technical',
                'accessibility': 'Accessibility'
            }
            
            display_categories = [category_display_names.get(cat, cat.replace('_', ' ').title()) for cat in categories]
            
            category_chart = dcc.Graph(
                figure=px.bar(
                    x=display_categories,
                    y=scores,
                    title="Category Scores",
                    labels={'x': 'Categories', 'y': 'Score (0-100)'},
                    color=scores,
                    color_continuous_scale=['#DC2626', '#F59E0B', '#10B981'],
                    range_color=[0, 100]
                ).update_layout(
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=40, b=0),
                    xaxis_tickangle=-45
                )
            )
            
            category_section = html.Div([
                html.H3("Category Performance"),
                category_chart
            ], className="card")
        else:
            category_section = None
        
        # Recommendations Section
        if recommendations:
            rec_items = []
            for rec in recommendations:
                priority_color = {
                    'high': '#DC2626',
                    'medium': '#F59E0B', 
                    'low': '#10B981'
                }.get(rec.get('priority', 'medium'), '#6B7280')
                
                # Check if there are affected pages to show
                affected_pages = rec.get('affected_pages', [])
                
                rec_content = [
                    html.H4(rec.get('title', 'Recommendation'), 
                           style={'color': priority_color, 'margin-bottom': '0.5rem'}),
                    html.P(rec.get('description', ''), 
                          style={'margin-bottom': '0.5rem'}),
                    html.Div([
                        html.Span(f"Priority: {rec.get('priority', 'unknown').title()}", 
                                 style={'color': priority_color, 'font-weight': 'bold'}),
                        html.Span(f" | Impact: {rec.get('estimated_impact', 'unknown').title()}", 
                                 style={'margin-left': '10px'}),
                        html.Span(f" | Pages Affected: {rec.get('pages_affected', 0)}", 
                                 style={'margin-left': '10px'})
                    ], className='text-muted', style={'font-size': '0.9em'})
                ]
                
                # Add affected pages section if available
                if affected_pages:
                    pages_list = []
                    for page in affected_pages[:10]:  # Show up to 10 pages
                        page_info = f"{page.get('title', 'Untitled')} ({page.get('url', 'No URL')})"
                        if 'word_count' in page:
                            page_info += f" - {page['word_count']} words"
                        elif 'content_ratio' in page:
                            page_info += f" - {page['content_ratio']} content ratio"
                        
                        pages_list.append(html.Li([
                            html.A(page.get('title', 'Untitled')[:50] + ('...' if len(page.get('title', '')) > 50 else ''), 
                                   href=page.get('url', '#'), target="_blank",
                                   style={'color': 'var(--primary-orange)', 'text-decoration': 'none'}),
                            html.Span(f" - {page.get('word_count', page.get('content_ratio', 'N/A'))}", 
                                     style={'color': 'var(--text-muted)', 'font-size': '0.9em'})
                        ], style={'margin': '0.25rem 0'}))
                    
                    if len(affected_pages) > 10:
                        pages_list.append(html.Li(f"... and {len(affected_pages) - 10} more pages", 
                                                 style={'color': 'var(--text-muted)', 'font-style': 'italic'}))
                    
                    rec_content.extend([
                        html.Hr(style={'margin': '0.75rem 0', 'border-color': 'var(--border-color)'}),
                        html.H5("Affected Pages:", style={'margin': '0.5rem 0', 'color': 'var(--text-primary)'}),
                        html.Ul(pages_list, style={'margin': '0', 'padding-left': '1.5rem'})
                    ])
                
                rec_item = html.Div(rec_content, className='recommendation-item', style={
                    'border-left': f'4px solid {priority_color}',
                    'padding': '1rem',
                    'margin': '0.5rem 0',
                    'background': 'var(--bg-hover)',
                    'border-radius': 'var(--radius-md)'
                })
                rec_items.append(rec_item)
            
            recommendations_section = html.Div([
                html.H3("Recommendations"),
                html.Div(rec_items)
            ], className="card")
        else:
            recommendations_section = None
        
        # Industry Benchmarks
        if benchmarks:
            bench_content = [
                html.H3("Industry Benchmarks"),
                html.P([html.Strong("Performance Tier: "), benchmarks.get('performance_tier', 'Unknown')]),
                html.P([html.Strong("Percentile Rank: "), f"{benchmarks.get('percentile_rank', 0)}th percentile"]),
                html.P([html.Strong("vs Industry Average: "), f"+{benchmarks.get('vs_industry_average', 0):.1f} points" if benchmarks.get('vs_industry_average', 0) >= 0 else f"{benchmarks.get('vs_industry_average', 0):.1f} points"]),
                html.P([html.Strong("Top Quartile Threshold: "), f"{benchmarks.get('top_quartile_threshold', 0)}/100"]),
                html.P([html.Strong("Industry Leader Threshold: "), f"{benchmarks.get('leader_threshold', 0)}/100"])
            ]
            
            benchmarks_section = html.Div(bench_content, className="card")
        else:
            benchmarks_section = None
        
        # Page Scores Table (top 10 pages)
        if page_scores:
            page_table_rows = []
            for page in page_scores[:10]:  # Show top 10 pages
                page_table_rows.append(html.Tr([
                    html.Td(html.A(page.get('title', 'Untitled')[:50] + ("..." if len(page.get('title', '')) > 50 else ""), 
                                   href=page.get('url', ''), target="_blank")),
                    html.Td(f"{page.get('overall_score', 0):.1f}"),
                    html.Td(f"{page.get('category_scores', {}).get('structural_html', 0):.1f}"),
                    html.Td(f"{page.get('category_scores', {}).get('content_organization', 0):.1f}"),
                    html.Td(f"{page.get('category_scores', {}).get('token_efficiency', 0):.1f}"),
                    html.Td(f"{page.get('category_scores', {}).get('llm_technical', 0):.1f}"),
                    html.Td(f"{page.get('category_scores', {}).get('accessibility', 0):.1f}")
                ]))
            
            page_table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Page Title"),
                        html.Th("Overall"),
                        html.Th("HTML"),
                        html.Th("Content"),
                        html.Th("Tokens"),
                        html.Th("LLM Tech"),
                        html.Th("A11y")
                    ])
                ]),
                html.Tbody(page_table_rows)
            ], className="table table-striped")
            
            pages_section = html.Div([
                html.H3("Page Scores"),
                page_table
            ], className="card")
        else:
            pages_section = None
        
        # Combine all sections
        sections = []
        
        # Create a responsive row for summary and benchmarks
        if summary_section and benchmarks_section:
            # Both sections exist - put them side by side
            sections.append(
                html.Div([
                    html.Div(summary_section, style={
                        'flex': '1',
                        'min-width': '300px',
                        'padding-right': '0.5rem'
                    }),
                    html.Div(benchmarks_section, style={
                        'flex': '1', 
                        'min-width': '300px',
                        'padding-left': '0.5rem'
                    })
                ], style={
                    'display': 'flex',
                    'flex-wrap': 'wrap',
                    'gap': '0',
                    'margin-bottom': '1rem'
                })
            )
        else:
            # Only one section exists - display normally
            if summary_section:
                sections.append(summary_section)
            if benchmarks_section:
                sections.append(benchmarks_section)
        
        if category_section:
            sections.append(category_section)
        
        if recommendations_section:
            sections.append(recommendations_section)
        
        if pages_section:
            sections.append(pages_section)
        
        return html.Div(sections)
    
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