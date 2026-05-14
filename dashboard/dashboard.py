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
        
        self.app = dash.Dash(
            __name__, 
            assets_folder=assets_folder,
            title="Airbais Dashboard",
            meta_tags=[
                {"name": "viewport", "content": "width=device-width, initial-scale=1"}
            ]
        )
        
        self.data_loader = ToolDataLoader(tools_root_path)
        self.current_data = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize available tools and runs
        self.available_tools = self.data_loader.discover_tools()
        self.tools_with_display_names = self.data_loader.get_tools_with_display_names()
        self.available_data = self.data_loader.get_available_data()
        
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        # Get available tools for dropdown with display names
        tool_options = []
        for tool_name, display_name in self.tools_with_display_names:
            tool_options.append({'label': display_name, 'value': tool_name})
        
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
                    # html.P("Select a tool and run to analyze", className="text-muted")
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
            
            # Get display name for the selected tool
            display_name = self.data_loader.get_tool_display_name(selected_tool)
            
            tool_info = html.Div([
                html.P(f"Found {len(runs)} runs for {display_name}", className="text-success"),
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
                    html.Li(display_name) for tool_name, display_name in self.tools_with_display_names
                ] if self.tools_with_display_names else [html.Li("No tools found")])
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
        
        elif tool_type == 'llmstxtgenerator':
            generation_summary = data.get('generation_summary', {})
            pages_crawled = generation_summary.get('pages_crawled', 0)
            sections_detected = generation_summary.get('sections_detected', 0)
            total_links = generation_summary.get('total_links_generated', 0)
            files_generated = generation_summary.get('files_generated', 0)
            
            return [
                html.Div([
                    html.Div(str(pages_crawled), className="stat-number"),
                    html.Div("Pages Crawled", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(sections_detected), className="stat-number"),
                    html.Div("Sections Found", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_links), className="stat-number"),
                    html.Div("Links Generated", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(files_generated), className="stat-number"),
                    html.Div("Files Created", className="stat-label")
                ], className="stat-card")
            ]
        
        elif tool_type == 'graspevaluator':
            grasp_score = data.get('grasp_score', 0)
            letter_grade = data.get('letter_grade', 'F')
            metrics = data.get('metrics', {})
            enhanced_recommendations = data.get('enhanced_recommendations', [])
            basic_recommendations = data.get('recommendations', [])
            recommendations = len(enhanced_recommendations) if enhanced_recommendations else len(basic_recommendations)
            
            # Count metrics by rating (use normalized_score for comparison)
            excellent_count = sum(1 for metric, details in metrics.items() 
                                if isinstance(details, dict) and details.get('normalized_score', 0) >= 90)
            
            return [
                html.Div([
                    html.Div(f"{grasp_score:.1f}", className="stat-number"),
                    html.Div("GRASP Score", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(letter_grade, className="stat-number"),
                    html.Div("Grade", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(excellent_count), className="stat-number"),
                    html.Div("High-Scoring Metrics", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(recommendations), className="stat-number"),
                    html.Div("Recommendations", className="stat-label")
                ], className="stat-card")
            ]
        
        elif tool_type == 'rulesevaluator':
            summary = data.get('summary', {})
            total_prompts = summary.get('total_prompts', 0)
            prompts_passed = summary.get('prompts_passed', 0)
            overall_pass_rate = summary.get('overall_pass_rate', 0)
            average_score = summary.get('average_score', 0)
            critical_failures = summary.get('critical_failures', 0)
            
            # Get database stats
            db_stats = data.get('metrics', {}).get('database_stats', {})
            total_chunks = db_stats.get('total_chunks', 0)
            
            return [
                html.Div([
                    html.Div(str(total_prompts), className="stat-number"),
                    html.Div("Prompts Evaluated", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(f"{overall_pass_rate:.1f}%", className="stat-number"),
                    html.Div("Pass Rate", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(f"{average_score:.1f}", className="stat-number"),
                    html.Div("Average Score", className="stat-label")
                ], className="stat-card"),
                
                html.Div([
                    html.Div(str(total_chunks), className="stat-number"),
                    html.Div("Knowledge Chunks", className="stat-label")
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
        elif tool_type == 'llmstxtgenerator':
            return self._generate_llmstxtgenerator_content(data)
        elif tool_type == 'graspevaluator':
            return self._generate_graspevaluator_content(data)
        elif tool_type == 'rulesevaluator':
            return self._generate_rulesevaluator_content(data)
        
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
    
    def _generate_llmstxtgenerator_content(self, data: Dict) -> html.Div:
        """Generate content specific to llmstxtgenerator results"""
        
        metadata = data.get('_metadata', {})
        generation_summary = data.get('generation_summary', {})
        site_analysis = data.get('site_analysis', {})
        files_generated = data.get('files_generated', {})
        
        website_url = metadata.get('website_url', '')
        website_name = metadata.get('website_name', '')
        
        sections = []
        
        # Generation Summary
        summary_content = [
            html.H3("Generation Summary"),
            html.P([html.Strong("Website: "), html.A(website_name or website_url, href=website_url, target="_blank")]),
            html.P([html.Strong("Pages Crawled: "), str(generation_summary.get('pages_crawled', 0))]),
            html.P([html.Strong("Sections Detected: "), str(generation_summary.get('sections_detected', 0))]),
            html.P([html.Strong("Total Links Generated: "), str(generation_summary.get('total_links_generated', 0))]),
            html.P([html.Strong("Success Rate: "), f"{generation_summary.get('success_rate', 0):.1f}%"]),
            html.P([html.Strong("Max Depth Reached: "), str(generation_summary.get('max_depth_reached', 0))])
        ]
        
        # Generated Files
        files_content = [html.H3("Generated Files")]
        
        file_status = [
            ("LLMS.txt File", files_generated.get('llms_txt', False)),
            ("Markdown Version", files_generated.get('llms_md', False)),
            ("JSON Data", files_generated.get('llms_json', False)),
            ("Generation Report", files_generated.get('generation_report', False))
        ]
        
        for file_name, status in file_status:
            status_icon = "✅" if status else "❌"
            files_content.append(html.P([
                html.Span(status_icon, style={'margin-right': '0.5rem'}),
                html.Strong(file_name),
                html.Span(" - Generated" if status else " - Not Generated", 
                         style={'color': 'green' if status else 'red'})
            ]))
        
        # Configuration Used
        config = metadata.get('configuration', {})
        config_content = [
            html.H3("Configuration Used"),
            html.P([html.Strong("Max Pages: "), str(config.get('max_pages', 'N/A'))]),
            html.P([html.Strong("Max Depth: "), str(config.get('max_depth', 'N/A'))]),
            html.P([html.Strong("AI Descriptions: "), "Enabled" if config.get('ai_descriptions', False) else "Disabled"]),
            html.P([html.Strong("Output Formats: "), ", ".join(config.get('output_formats', []))])
        ]
        
        # Create responsive horizontal layout for these three sections
        horizontal_sections = html.Div([
            html.Div(summary_content, className="card", style={'flex': '1', 'min-width': '300px'}),
            html.Div(files_content, className="card", style={'flex': '1', 'min-width': '300px'}),
            html.Div(config_content, className="card", style={'flex': '1', 'min-width': '300px'})
        ], style={
            'display': 'flex',
            'gap': '1rem',
            'margin-bottom': '1rem',
            'flex-wrap': 'wrap'
        })
        
        sections.append(horizontal_sections)
        
        # Site Structure Analysis
        section_counts = site_analysis.get('section_counts', {})
        if section_counts:
            # Create a bar chart for sections
            fig_sections = go.Figure(data=[
                go.Bar(x=list(section_counts.keys()), 
                       y=list(section_counts.values()),
                       marker_color='#F78D1F')
            ])
            fig_sections.update_layout(
                title="Links Generated by Section",
                xaxis_title="Section",
                yaxis_title="Number of Links",
                template="plotly_white",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1C1917"),
                title_font=dict(color="#1C1917"),
                xaxis=dict(color="#1C1917"),
                yaxis=dict(color="#1C1917")
            )
            
            sections.append(html.Div([
                html.H3("Site Structure Analysis"),
                dcc.Graph(figure=fig_sections)
            ], className="card"))
        
        # Content Categories
        content_categories = site_analysis.get('content_categories', {})
        if content_categories:
            # Create a pie chart for content categories
            fig_categories = go.Figure(data=[
                go.Pie(labels=list(content_categories.keys()), 
                       values=list(content_categories.values()),
                       marker=dict(colors=['#F78D1F', '#FFA940', '#D97706', '#A8A29E', '#78716C']))
            ])
            fig_categories.update_layout(
                title="Content Distribution by Category",
                template="plotly_white",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#1C1917"),
                title_font=dict(color="#1C1917")
            )
            
            sections.append(html.Div([
                html.H3("Content Categories"),
                dcc.Graph(figure=fig_categories)
            ], className="card"))
        
        
        # Sections Detail
        sections_data = site_analysis.get('sections', {})
        if sections_data:
            sections_detail = [html.H3("Generated Sections Detail")]
            
            for section_name, links in sections_data.items():
                if links:
                    section_content = [
                        html.H4(f"{section_name.capitalize()} ({len(links)} links)"),
                        html.Ul([
                            html.Li([
                                html.A(link.get('title', 'Untitled'), 
                                      href=link.get('url', '#'), 
                                      target="_blank",
                                      style={'color': 'var(--primary-orange)', 'text-decoration': 'none'}),
                                html.Span(f" - {link.get('description', 'No description')[:100]}{'...' if len(link.get('description', '')) > 100 else ''}", 
                                         style={'color': 'var(--text-muted)', 'font-size': '0.9em'})
                            ], style={'margin': '0.25rem 0'})
                            for link in links[:10]  # Show first 10 links
                        ])
                    ]
                    
                    if len(links) > 10:
                        section_content.append(html.P(f"... and {len(links) - 10} more links", 
                                                     style={'color': 'var(--text-muted)', 'font-style': 'italic'}))
                    
                    sections_detail.extend(section_content)
                    sections_detail.append(html.Hr())
            
            sections.append(html.Div(sections_detail, className="card"))
        
        return html.Div(sections)
    
    def _generate_graspevaluator_content(self, data: Dict) -> html.Div:
        """Generate content specific to GRASP evaluator results"""
        
        sections = []
        
        # Overall Score Display
        grasp_score = data.get('grasp_score', 0)
        letter_grade = data.get('letter_grade', 'F')
        url = data.get('url', 'Unknown URL')
        
        # Score card with visual indicator
        score_color = self._get_score_color(grasp_score)
        
        sections.append(html.Div([
            html.H3("GRASP Content Quality Score"),
            html.Div([
                html.Div([
                    html.Div(letter_grade, className="grade-letter", 
                            style={'font-size': '4rem', 'font-weight': 'bold', 'color': score_color}),
                    html.Div(f"{grasp_score:.1f} out of 100", className="score-number",
                            style={'font-size': '1.5rem', 'color': score_color, 'margin-top': '0.5rem'}),
                ], style={'text-align': 'center', 'padding': '2rem'}),
                html.Div([
                    html.Strong("Evaluated URL: "),
                    html.A(url, href=url, target="_blank", 
                          style={'color': 'var(--primary-orange)'})
                ], style={'text-align': 'center', 'margin-top': '1rem'})
            ])
        ], className="card"))
        
        # Metrics Breakdown
        metrics = data.get('metrics', {})
        breakdown = data.get('breakdown', {})
        
        if metrics:
            # Create metrics visualization
            metric_names = []
            metric_scores = []
            metric_weights = []
            metric_descriptions = []
            
            for metric_name, metric_data in metrics.items():
                if isinstance(metric_data, dict):
                    metric_names.append(metric_name.upper())
                    score = metric_data.get('score', 0)
                    weight = metric_data.get('weight', 0)
                    description = metric_data.get('description', '')
                    
                    # Use normalized_score if available, otherwise calculate it
                    if 'normalized_score' in metric_data:
                        normalized_score = metric_data['normalized_score']
                    else:
                        # Fallback calculation for compatibility
                        if metric_name == 'grounded':
                            normalized_score = min(100, max(0, score * 10))
                        elif metric_name == 'readable':
                            if isinstance(score, bool):
                                normalized_score = 100 if score else 0
                            else:
                                normalized_score = score
                        elif metric_name == 'accurate':
                            if isinstance(score, str):
                                score_map = {'High': 100, 'Medium': 50, 'Low': 0}
                                normalized_score = score_map.get(score, 0)
                            else:
                                normalized_score = score
                        else:  # structured, polished
                            if isinstance(score, str):
                                rating_map = {'Excellent': 100, 'Very Good': 90, 'Good': 80, 'Fair': 60, 'Poor': 40, 'Very Poor': 20}
                                normalized_score = rating_map.get(score, 0)
                            else:
                                normalized_score = score
                    
                    metric_scores.append(normalized_score)
                    metric_weights.append(weight)
                    metric_descriptions.append(description)
            
            if metric_names:
                # Create bar chart for metrics
                fig_metrics = go.Figure()
                
                # Add bars with colors based on score
                colors = [self._get_score_color(score) for score in metric_scores]
                
                fig_metrics.add_trace(go.Bar(
                    x=metric_names,
                    y=metric_scores,
                    text=[f"{score:.1f}/100<br>({weight}% weight)" for score, weight in zip(metric_scores, metric_weights)],
                    textposition='auto',
                    marker_color=colors,
                    hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}/100<br>Weight: %{customdata}%<extra></extra>',
                    customdata=metric_weights
                ))
                
                fig_metrics.update_layout(
                    title="GRASP Metrics Breakdown",
                    xaxis_title="Metrics",
                    yaxis_title="Score (0-100)",
                    yaxis_range=[0, 100],
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='var(--text-color)',
                    showlegend=False
                )
                
                sections.append(html.Div([
                    html.H3("Metrics Breakdown"),
                    dcc.Graph(figure=fig_metrics)
                ], className="card"))
        
        # Detailed Metric Explanations
        metric_explanations = {
            'grounded': 'Measures how well content supports answering customer intents and questions',
            'readable': 'Evaluates if content reading level matches target audience expectations',
            'accurate': 'Assesses content freshness as a proxy for accuracy and relevance',
            'structured': 'Analyzes HTML semantic structure for optimal LLM consumption',
            'polished': 'Checks grammar, spelling, and overall language quality'
        }
        
        if metrics:
            metric_details = [html.H3("Metric Details")]
            
            for metric_name, metric_data in metrics.items():
                if isinstance(metric_data, dict):
                    score = metric_data.get('score', 0)
                    description = metric_data.get('description', '')
                    weight = metric_data.get('weight', 0)
                    
                    # Get display score and color
                    normalized_score = metric_data.get('normalized_score', 0)
                    
                    if metric_name == 'grounded':
                        display_score = f"{score:.1f}/10"
                        score_color = self._get_score_color(normalized_score)
                    elif metric_name == 'readable':
                        if isinstance(score, bool):
                            display_score = "Pass" if score else "Fail"
                            score_color = '#28a745' if score else '#dc3545'
                        else:
                            display_score = f"{score:.1f}"
                            score_color = self._get_score_color(normalized_score)
                    else:  # accurate, structured, polished
                        display_score = str(score)
                        score_color = self._get_score_color(normalized_score)
                    
                    metric_details.append(html.Div([
                        html.Div([
                            html.H4([
                                metric_name.upper(),
                                html.Span(f" ({weight}% weight)", style={'font-size': '0.8em', 'color': 'var(--text-muted)'})
                            ], style={'margin-bottom': '0.5rem'}),
                            html.Div(display_score, style={
                                'font-size': '1.5rem', 
                                'font-weight': 'bold', 
                                'color': score_color,
                                'margin-bottom': '0.5rem'
                            }),
                            html.P(description, style={'color': 'var(--text-muted)'}),
                            html.P(metric_explanations.get(metric_name, ''), style={'font-size': '0.9em'})
                        ])
                    ], className="metric-detail", style={
                        'border-left': f'4px solid {score_color}',
                        'padding-left': '1rem',
                        'margin': '1rem 0'
                    }))
            
            sections.append(html.Div(metric_details, className="card"))
        
        # Enhanced Recommendations
        enhanced_recommendations = data.get('enhanced_recommendations', [])
        basic_recommendations = data.get('recommendations', [])
        
        if enhanced_recommendations:
            rec_sections = []
            
            # Group recommendations by priority
            priority_groups = {
                'critical': {'items': [], 'color': '#DC2626', 'label': 'Critical Issues'},
                'high': {'items': [], 'color': '#EA580C', 'label': 'High Priority'},
                'medium': {'items': [], 'color': '#F59E0B', 'label': 'Medium Priority'},
                'low': {'items': [], 'color': '#10B981', 'label': 'Low Priority'}
            }
            
            for rec in enhanced_recommendations:
                priority = rec.get('priority', 'medium')
                if priority in priority_groups:
                    priority_groups[priority]['items'].append(rec)
            
            # Create sections for each priority level
            for priority, group in priority_groups.items():
                if not group['items']:
                    continue
                    
                priority_items = []
                for rec in group['items']:
                    # Build recommendation card
                    rec_card = html.Div([
                        # Header with issue and category
                        html.Div([
                            html.Span(rec.get('category', 'General').replace('_', ' ').title(), 
                                    className="badge",
                                    style={'background': group['color'], 'color': 'white', 'margin-right': '0.5rem'}),
                            html.Strong(rec.get('issue', 'No issue description'))
                        ], style={'margin-bottom': '0.5rem'}),
                        
                        # Impact
                        html.Div([
                            html.Strong("Impact: "),
                            rec.get('impact', 'No impact description')
                        ], className="text-muted", style={'margin-bottom': '0.5rem'}),
                        
                        # Action
                        html.Div([
                            html.Strong("Action: "),
                            rec.get('action', 'No action specified')
                        ], style={'margin-bottom': '1rem'}),
                        
                        # Implementation details (if available)
                        self._render_implementation_details(rec.get('implementation', {})),
                        
                        # Specifics (if available)
                        self._render_specifics(rec.get('specifics', {}))
                        
                    ], className="recommendation-card", style={
                        'border-left': f'4px solid {group["color"]}',
                        'padding': '1rem',
                        'margin-bottom': '1rem',
                        'background': 'var(--gray-50)',
                        'border-radius': '0.5rem'
                    })
                    
                    priority_items.append(rec_card)
                
                # Add priority section
                rec_sections.append(html.Div([
                    html.H4([
                        html.Span(group['label'], style={'color': group['color']}),
                        html.Span(f" ({len(group['items'])})", style={'color': '#6B7280'})
                    ], style={'margin-bottom': '1rem'}),
                    html.Div(priority_items)
                ]))
            
            sections.append(html.Div([
                html.H3("Detailed Improvement Recommendations"),
                html.Div(rec_sections)
            ], className="card"))
            
        elif basic_recommendations:
            # Fallback to basic recommendations if enhanced ones aren't available
            rec_items = []
            for i, rec in enumerate(basic_recommendations, 1):
                rec_items.append(html.Li([
                    html.Strong(f"{i}. "),
                    rec
                ], style={'margin': '0.5rem 0'}))
            
            sections.append(html.Div([
                html.H3("Improvement Recommendations"),
                html.Ul(rec_items, style={'padding-left': '1rem'})
            ], className="card"))
        
        return html.Div(sections)
    
    def _render_implementation_details(self, implementation: Dict) -> html.Div:
        """Render implementation details for enhanced recommendations"""
        if not implementation:
            return html.Div()
        
        details = []
        
        # Effort and timeline
        if implementation.get('effort') or implementation.get('timeline'):
            effort_timeline = []
            if implementation.get('effort'):
                effort_timeline.append(html.Span([
                    html.Strong("Effort: "),
                    implementation['effort'].title()
                ], style={'margin-right': '1rem'}))
            
            if implementation.get('timeline'):
                effort_timeline.append(html.Span([
                    html.Strong("Timeline: "),
                    implementation['timeline']
                ]))
            
            details.append(html.Div(effort_timeline, style={'margin-bottom': '0.5rem', 'font-size': '0.9rem'}))
        
        # Steps
        if implementation.get('steps'):
            steps_list = []
            for i, step in enumerate(implementation['steps'], 1):
                steps_list.append(html.Li(step, style={'margin': '0.25rem 0'}))
            
            details.append(html.Div([
                html.Strong("Implementation Steps:"),
                html.Ol(steps_list, style={'margin': '0.5rem 0', 'padding-left': '1.5rem'})
            ], style={'margin-bottom': '0.5rem'}))
        
        # Other implementation fields
        for key, value in implementation.items():
            if key in ['effort', 'timeline', 'steps']:
                continue
            
            if isinstance(value, list) and value:
                details.append(html.Div([
                    html.Strong(f"{key.replace('_', ' ').title()}: "),
                    html.Ul([html.Li(item) for item in value], style={'margin': '0.25rem 0', 'padding-left': '1.5rem'})
                ], style={'margin-bottom': '0.5rem', 'font-size': '0.9rem'}))
            elif isinstance(value, str):
                details.append(html.Div([
                    html.Strong(f"{key.replace('_', ' ').title()}: "),
                    value
                ], style={'margin-bottom': '0.25rem', 'font-size': '0.9rem'}))
        
        if details:
            return html.Div([
                html.Div("Implementation Details", style={'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                html.Div(details, className="implementation-details", style={
                    'background': 'white',
                    'padding': '0.75rem',
                    'border-radius': '0.25rem',
                    'border': '1px solid #E5E7EB'
                })
            ], style={'margin-bottom': '1rem'})
        
        return html.Div()
    
    def _render_specifics(self, specifics: Dict) -> html.Div:
        """Render specifics section for enhanced recommendations"""
        if not specifics:
            return html.Div()
        
        details = []
        
        for key, value in specifics.items():
            if isinstance(value, list) and value:
                details.append(html.Div([
                    html.Strong(f"{key.replace('_', ' ').title()}: "),
                    html.Ul([html.Li(str(item)) for item in value], style={'margin': '0.25rem 0', 'padding-left': '1.5rem'})
                ], style={'margin-bottom': '0.5rem'}))
            elif isinstance(value, (str, int, float)):
                details.append(html.Div([
                    html.Strong(f"{key.replace('_', ' ').title()}: "),
                    str(value)
                ], style={'margin-bottom': '0.25rem'}))
        
        if details:
            return html.Div([
                html.Div("Specifics", style={'font-weight': 'bold', 'margin-bottom': '0.5rem'}),
                html.Div(details, className="specifics-box", style={
                    'background': '#F9FAFB',
                    'padding': '0.75rem',
                    'border-radius': '0.25rem',
                    'font-size': '0.9rem'
                })
            ], style={'margin-bottom': '1rem'})
        
        return html.Div()
    
    def _generate_rulesevaluator_content(self, data: Dict) -> html.Div:
        """Generate content specific to Rules Evaluator results"""
        
        sections = []
        
        # Evaluation Summary
        summary = data.get('summary', {})
        metadata = data.get('_metadata', {})
        
        total_prompts = summary.get('total_prompts', 0)
        prompts_passed = summary.get('prompts_passed', 0)
        overall_pass_rate = summary.get('overall_pass_rate', 0)
        average_score = summary.get('average_score', 0)
        critical_failures = summary.get('critical_failures', 0)
        evaluation_passed = summary.get('evaluation_passed', False)
        
        # Status color based on pass rate
        status_color = '#28A745' if evaluation_passed else '#DC2626'
        status_text = "✅ PASSED" if evaluation_passed else "❌ FAILED"
        
        # Evaluation Summary Card
        summary_content = [
            html.H3("Rules Evaluation Summary"),
            html.Div([
                html.Div([
                    html.Div(status_text, style={
                        'font-size': '1.5rem',
                        'font-weight': 'bold',
                        'color': status_color,
                        'text-align': 'center',
                        'margin-bottom': '1rem'
                    }),
                    html.Div(f"{overall_pass_rate:.1f}% Pass Rate", style={
                        'font-size': '1.2rem',
                        'text-align': 'center',
                        'color': status_color
                    })
                ], style={'border': f'2px solid {status_color}', 'padding': '1rem', 'border-radius': '0.5rem', 'margin-bottom': '1rem'})
            ]),
            html.P([html.Strong("Total Prompts: "), str(total_prompts)]),
            html.P([html.Strong("Prompts Passed: "), str(prompts_passed)]),
            html.P([html.Strong("Average Score: "), f"{average_score:.1f}/100"]),
            html.P([html.Strong("Critical Failures: "), str(critical_failures)]),
            html.P([html.Strong("Evaluation Date: "), data.get('timestamp', '').split('T')[0] if data.get('timestamp') else 'Unknown'])
        ]
        
        sections.append(html.Div(summary_content, className="card"))
        
        # Rule Type Performance Chart
        metrics = data.get('metrics', {})
        pass_rates_by_type = metrics.get('pass_rates_by_type', {})
        
        if pass_rates_by_type:
            # Filter out rule types with 0 total rules
            total_rules_by_type = metrics.get('total_rules_by_type', {})
            filtered_rates = {}
            
            for rule_type, pass_rate in pass_rates_by_type.items():
                total_rules = total_rules_by_type.get(rule_type, {}).get('total', 0)
                if total_rules > 0:
                    filtered_rates[rule_type] = pass_rate
            
            if filtered_rates:
                rule_types = list(filtered_rates.keys())
                pass_rates = list(filtered_rates.values())
                
                # Get the actual rule counts for labels
                rule_counts = []
                for rule_type in rule_types:
                    rules_data = total_rules_by_type.get(rule_type, {})
                    passed = rules_data.get('passed', 0)
                    total = rules_data.get('total', 0)
                    rule_counts.append(f"{passed}/{total}")
                
                # Create bar chart with custom hover text and annotations
                fig = go.Figure()
                
                # Add bars
                fig.add_trace(go.Bar(
                    x=[rt.title() for rt in rule_types],
                    y=pass_rates,
                    text=[f"{rate:.1f}%<br>{count} rules" for rate, count in zip(pass_rates, rule_counts)],
                    textposition='auto',
                    marker_color=[self._get_score_color(rate) for rate in pass_rates],
                    hovertemplate='<b>%{x}</b><br>Pass Rate: %{y:.1f}%<br>Rules Passed: %{customdata}<extra></extra>',
                    customdata=rule_counts
                ))
                
                fig.update_layout(
                    title="Pass Rates by Rule Type",
                    xaxis_title="Rule Type",
                    yaxis_title="Pass Rate (%)",
                    font=dict(family="Inter, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=40, b=0),
                    yaxis_range=[0, 100],
                    showlegend=False
                )
                
                rule_chart = dcc.Graph(figure=fig)
                
                sections.append(html.Div([
                    html.H3("Rule Type Performance"),
                    rule_chart
                ], className="card"))
        
        # Database and Configuration Information - Side by Side
        db_stats = metrics.get('database_stats', {})
        config = metrics.get('config', {})
        
        if db_stats or config:
            info_row = []
            
            # Knowledge Base Information
            if db_stats:
                db_content = [
                    html.H3("Knowledge Base Information"),
                    html.P([html.Strong("Total Documents: "), str(db_stats.get('total_documents', 0))]),
                    html.P([html.Strong("Content Chunks: "), str(db_stats.get('total_chunks', 0))]),
                    html.P([html.Strong("Embedding Model: "), db_stats.get('embedding_model', 'Unknown')]),
                    html.P([html.Strong("Collection: "), db_stats.get('collection_name', 'Unknown')]),
                    html.P([html.Strong("Chunk Size: "), f"{db_stats.get('chunk_size', 0)} characters"]),
                    html.P([html.Strong("Chunk Overlap: "), f"{db_stats.get('chunk_overlap', 0)} characters"])
                ]
                
                # Add content sources breakdown
                sources = db_stats.get('sources', {})
                if sources:
                    sources_list = []
                    for source_type, count in sources.items():
                        sources_list.append(html.Li(f"{source_type.title()}: {count} chunks"))
                    
                    db_content.extend([
                        html.Hr(),
                        html.Strong("Content Sources:"),
                        html.Ul(sources_list, style={'margin-top': '0.5rem'})
                    ])
                
                info_row.append(html.Div(db_content, className="card", style={
                    'flex': '1',
                    'min-width': '300px',
                    'margin-right': '0.5rem'
                }))
            
            # Configuration Information
            if config:
                config_content = [
                    html.H3("Evaluation Configuration"),
                    html.P([html.Strong("Passing Score Threshold: "), f"{config.get('passing_score', 60)}%"]),
                    html.P([html.Strong("Content Source: "), config.get('content_type', 'Unknown').title()])
                ]
                
                # Add rule weights
                weights = config.get('weights', {})
                if weights:
                    weights_list = []
                    for rule_type, weight in weights.items():
                        weights_list.append(html.Li(f"{rule_type.title()}: {weight}%"))
                    
                    config_content.extend([
                        html.Hr(),
                        html.Strong("Rule Type Weights:"),
                        html.Ul(weights_list, style={'margin-top': '0.5rem'})
                    ])
                
                info_row.append(html.Div(config_content, className="card", style={
                    'flex': '1',
                    'min-width': '300px',
                    'margin-left': '0.5rem'
                }))
            
            # Add the row with both cards
            sections.append(html.Div(info_row, style={
                'display': 'flex',
                'gap': '0',
                'margin-bottom': '1rem',
                'flex-wrap': 'wrap'
            }))
        
        # Detailed Prompt Analysis
        prompt_data = data.get('data', {}).get('prompt_evaluations', [])
        if prompt_data:
            prompt_analysis = [html.H3("Detailed Prompt Analysis")]
            
            for prompt_result in prompt_data:
                prompt_num = prompt_result.get('prompt_number', 0)
                score = prompt_result.get('score', 0)
                passed = prompt_result.get('passed', False)
                prompt_text = prompt_result.get('prompt_text', '')
                summary_text = prompt_result.get('summary', '')
                rules_passed = prompt_result.get('rules_passed', 0)
                total_rules = prompt_result.get('total_rules', 0)
                critical_failed = prompt_result.get('critical_failed', False)
                
                result_color = '#28A745' if passed else '#DC2626'
                result_icon = "✅" if passed else "❌"
                
                # Create a more detailed analysis card
                prompt_card = html.Div([
                    # Header with status and score
                    html.Div([
                        html.Div([
                            html.H4(f"Prompt {prompt_num}", style={'margin': '0'}),
                            html.Div(result_icon, style={'font-size': '1.5rem', 'margin-left': '1rem'})
                        ], style={'display': 'flex', 'align-items': 'center'}),
                        html.Div([
                            html.Div(f"{min(100, score):.0f}/100", style={
                                'font-size': '2rem',
                                'font-weight': 'bold',
                                'color': result_color,
                                'text-align': 'right'
                            }),
                            html.Div("FAILED" if not passed else "PASSED", style={
                                'font-size': '0.9rem',
                                'color': result_color,
                                'text-align': 'right',
                                'font-weight': 'bold'
                            })
                        ])
                    ], style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center', 'margin-bottom': '1rem'}),
                    
                    # Prompt text
                    html.Div([
                        html.Strong("Prompt:"),
                        html.P(prompt_text, style={'margin': '0.5rem 0', 'font-style': 'italic'})
                    ], style={
                        'margin-bottom': '1rem', 
                        'padding': '0.75rem', 
                        'background': 'var(--bg-hover)', 
                        'border-radius': '0.25rem',
                        'border': '1px solid var(--border-color)'
                    }),
                    
                    # Rules performance
                    html.Div([
                        html.Div([
                            html.Strong("Rules Performance:"),
                            html.Span(f" {rules_passed} of {total_rules} rules satisfied", 
                                     style={'margin-left': '0.5rem'})
                        ], style={'margin-bottom': '0.5rem'}),
                        
                        # Progress bar
                        html.Div([
                            html.Div(style={
                                'width': f"{(rules_passed/total_rules*100) if total_rules > 0 else 0}%",
                                'height': '8px',
                                'background': result_color,
                                'border-radius': '4px',
                                'transition': 'width 0.3s ease'
                            })
                        ], style={
                            'width': '100%',
                            'height': '8px',
                            'background': 'var(--bg-hover)',
                            'border-radius': '4px',
                            'margin-bottom': '1rem',
                            'border': '1px solid var(--border-color)'
                        })
                    ]),
                    
                    # Critical failure warning if applicable
                    html.Div([
                        html.Div([
                            html.Span("⚠️", style={'font-size': '1.2rem', 'margin-right': '0.5rem'}),
                            html.Strong("Critical Rule Failed", style={'color': '#DC2626'})
                        ], style={'display': 'flex', 'align-items': 'center'})
                    ], style={'margin-bottom': '1rem', 'padding': '0.5rem', 'background': '#FEE2E2', 'border-radius': '0.25rem', 'border': '1px solid #DC2626'}) if critical_failed else None,
                    
                    # Analysis summary
                    html.Div([
                        html.Strong("Analysis Summary:"),
                        html.P(summary_text, style={'margin': '0.5rem 0', 'line-height': '1.6'})
                    ])
                    
                ], style={
                    'border-left': f'4px solid {result_color}',
                    'padding': '1.5rem',
                    'margin': '1.5rem 0',
                    'background': 'var(--bg-card)',
                    'border-radius': '0.5rem',
                    'box-shadow': '0 1px 3px rgba(0,0,0,0.1)'
                })
                
                prompt_analysis.append(prompt_card)
            
            sections.append(html.Div(prompt_analysis, className="card"))
        
        return html.Div(sections)
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on score"""
        if score >= 90:
            return '#28a745'  # Green
        elif score >= 80:
            return '#20c997'  # Teal
        elif score >= 70:
            return '#ffc107'  # Yellow
        elif score >= 60:
            return '#fd7e14'  # Orange
        else:
            return '#dc3545'  # Red
    
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