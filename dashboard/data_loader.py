"""
Multi-Tool Data Loader for Master Dashboard
Handles loading and standardizing data from different AI tools
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import glob
import yaml

class ToolDataLoader:
    def __init__(self, tools_root_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Set the tools root path
        if tools_root_path:
            self.tools_root = Path(tools_root_path)
        else:
            # Auto-detect: this file is in tools/dashboard/, so tools root is parent
            self.tools_root = Path(__file__).parent.parent
        
        self.logger.info(f"Tools root path: {self.tools_root}")
    
    def get_tool_display_name(self, tool_name: str) -> str:
        """Get the display name for a tool from its config file, with fallback to formatted tool name"""
        try:
            # Check for config.yaml in tool root
            config_path = self.tools_root / tool_name / 'config.yaml'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'display_name' in config:
                        return config['display_name']
            
            # Check for config.yaml in config subdirectory (e.g., graspevaluator)
            config_subdir_path = self.tools_root / tool_name / 'config'
            if config_subdir_path.exists():
                for config_file in config_subdir_path.glob('*config*.yaml'):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config and 'display_name' in config:
                            return config['display_name']
        except Exception as e:
            self.logger.debug(f"Could not read config for {tool_name}: {e}")
        
        # Fallback to current formatting logic
        return tool_name.title().replace('_', ' ')
    
    def discover_tools(self) -> List[str]:
        """Discover all available tools by scanning for directories with results folders"""
        tools = []
        
        try:
            for item in self.tools_root.iterdir():
                if item.is_dir() and item.name != 'dashboard':
                    # Check if it has a results folder
                    results_path = item / 'results'
                    if results_path.exists():
                        tools.append(item.name)
                        self.logger.info(f"Discovered tool: {item.name}")
        except Exception as e:
            self.logger.error(f"Error discovering tools: {e}")
        
        return sorted(tools)
    
    def get_tools_with_display_names(self) -> List[Tuple[str, str]]:
        """Get all tools with their display names as (tool_name, display_name) tuples"""
        tools = self.discover_tools()
        return [(tool, self.get_tool_display_name(tool)) for tool in tools]
    
    def get_tool_runs(self, tool_name: str) -> List[Tuple[str, datetime]]:
        """Get all available runs for a specific tool, sorted by date"""
        runs = []
        tool_path = self.tools_root / tool_name / 'results'
        
        if not tool_path.exists():
            return runs
        
        try:
            for run_dir in tool_path.iterdir():
                if run_dir.is_dir():
                    # Try to parse as date
                    try:
                        run_date = datetime.strptime(run_dir.name, '%Y-%m-%d')
                        # Check if it has dashboard data
                        data_file = run_dir / 'dashboard-data.json'
                        if data_file.exists():
                            runs.append((run_dir.name, run_date))
                    except ValueError:
                        # Not a date format, skip
                        continue
        except Exception as e:
            self.logger.error(f"Error getting runs for {tool_name}: {e}")
        
        # Sort by date, newest first
        runs.sort(key=lambda x: x[1], reverse=True)
        return runs
    
    def load_tool_data(self, tool_name: str, run_date: str = None) -> Optional[Dict]:
        """Load data from a specific tool run"""
        
        # If no run_date specified, get the latest
        if not run_date:
            runs = self.get_tool_runs(tool_name)
            if not runs:
                self.logger.warning(f"No runs found for tool: {tool_name}")
                return None
            run_date = runs[0][0]  # Get the latest run
        
        data_file = self.tools_root / tool_name / 'results' / run_date / 'dashboard-data.json'
        
        if not data_file.exists():
            self.logger.error(f"Data file not found: {data_file}")
            return None
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Detect tool type first
            tool_type = self._detect_tool_type(data)
            
            # Add metadata about the tool and run
            data['_metadata'] = {
                'tool_name': tool_name,
                'run_date': run_date,
                'data_file': str(data_file),
                'tool_type': tool_type
            }
            
            # Standardize the data format
            return self._standardize_data(data)
            
        except Exception as e:
            self.logger.error(f"Error loading data from {data_file}: {e}")
            return None
    
    def _detect_tool_type(self, data: Dict) -> str:
        """Detect what type of tool generated this data"""
        
        # Intent Crawler detection
        if 'discovered_intents' in data and 'by_section' in data:
            return 'intentcrawler'
        
        # LLM Evaluator detection - supports both old and new formats
        if 'evaluation_results' in data and 'aggregate_metrics' in data and 'brand_info' in data:
            return 'llmevaluator'
        # New multi-LLM format
        if 'metadata' in data and 'llm_metrics' in data and 'brand_info' in data:
            return 'llmevaluator'
        
        # GEO Evaluator detection
        if 'overall_score' in data and 'analysis_summary' in data and 'recommendations' in data:
            metadata = data.get('metadata', {})
            if metadata.get('tool_name') == 'geoevaluator':
                return 'geoevaluator'
        
        # LLMS.txt Generator detection
        if 'generation_summary' in data and 'site_analysis' in data:
            metadata = data.get('metadata', {})
            if metadata.get('tool_name') == 'llmstxtgenerator':
                return 'llmstxtgenerator'
        
        # GRASP Evaluator detection
        if 'tool' in data and data.get('tool') == 'graspevaluator':
            return 'graspevaluator'
        if 'overall_score' in data and 'metrics' in data and 'breakdown' in data and 'recommendations' in data:
            # Check if it has GRASP-specific metrics
            metrics = data.get('metrics', {})
            if 'grounded' in metrics and 'readable' in metrics and 'accurate' in metrics:
                return 'graspevaluator'
        
        # Future tool types can be detected here
        # Example:
        # if 'sentiment_analysis' in data:
        #     return 'sentimentanalyzer'
        # if 'performance_metrics' in data:
        #     return 'performanceanalyzer'
        
        return 'unknown'
    
    def _standardize_data(self, data: Dict) -> Dict:
        """Standardize data format across different tools"""
        
        tool_type = data.get('_metadata', {}).get('tool_type', 'unknown')
        
        if tool_type == 'intentcrawler':
            return self._standardize_intentcrawler_data(data)
        elif tool_type == 'llmevaluator':
            return self._standardize_llmevaluator_data(data)
        elif tool_type == 'geoevaluator':
            return self._standardize_geoevaluator_data(data)
        elif tool_type == 'llmstxtgenerator':
            return self._standardize_llmstxtgenerator_data(data)
        elif tool_type == 'graspevaluator':
            return self._standardize_graspevaluator_data(data)
        
        # Future tool standardization can be added here
        # elif tool_type == 'sentimentanalyzer':
        #     return self._standardize_sentiment_data(data)
        
        return data
    
    def _standardize_intentcrawler_data(self, data: Dict) -> Dict:
        """Ensure intentcrawler data has all required fields"""
        
        # Set defaults for any missing fields
        standardized = {
            'discovered_intents': data.get('discovered_intents', []),
            'by_section': data.get('by_section', {}),
            'total_pages_analyzed': data.get('total_pages_analyzed', 0),
            'total_intents_discovered': data.get('total_intents_discovered', len(data.get('discovered_intents', []))),
            'extraction_methods_used': data.get('extraction_methods_used', ['unknown']),
            '_metadata': data.get('_metadata', {})
        }
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def _standardize_llmevaluator_data(self, data: Dict) -> Dict:
        """Standardize llmevaluator data format - supports both old and new multi-LLM formats"""
        
        # Check if this is the new multi-LLM format
        if 'metadata' in data and 'llm_metrics' in data:
            # New multi-LLM format
            standardized = {
                'evaluation_results': self._convert_multi_llm_to_standard(data),
                'aggregate_metrics': data.get('aggregate_metrics', {}),
                'brand_info': data.get('brand_info', {}),
                'insights': data.get('insights', {}),
                'evaluation_summary': data.get('evaluation_summary', {}),
                '_metadata': {
                    'tool_type': 'llmevaluator',
                    'format': 'multi_llm',
                    'llms': data.get('metadata', {}).get('llms', []),
                    'comparative_metrics': data.get('comparative_metrics', {})
                }
            }
        else:
            # Old single-LLM format
            standardized = {
                'evaluation_results': data.get('evaluation_results', []),
                'aggregate_metrics': data.get('aggregate_metrics', {}),
                'brand_info': data.get('brand_info', {}),
                'insights': data.get('insights', []),
                'evaluation_summary': data.get('evaluation_summary', {}),
                '_metadata': {
                    'tool_type': 'llmevaluator',
                    'format': 'single_llm'
                }
            }
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def _convert_multi_llm_to_standard(self, data: Dict) -> List[Dict]:
        """Convert multi-LLM detailed results to standard evaluation_results format"""
        evaluation_results = []
        
        detailed_results = data.get('detailed_results', [])
        llm_metrics = data.get('llm_metrics', {})
        
        for prompt_data in detailed_results:
            # For each LLM response to this prompt
            for llm_name, response_data in prompt_data.get('responses', {}).items():
                eval_result = {
                    'prompt': prompt_data.get('prompt', ''),
                    'category': prompt_data.get('category', ''),
                    'llm_name': llm_name,
                    'response_analysis': response_data.get('analysis', {}),
                    'response_excerpt': response_data.get('response', ''),
                    'cached': response_data.get('cached', False),
                    'error': response_data.get('error', None),
                    'timestamp': data.get('metadata', {}).get('timestamp', '')
                }
                evaluation_results.append(eval_result)
        
        return evaluation_results
    
    def _standardize_geoevaluator_data(self, data: Dict) -> Dict:
        """Standardize geoevaluator data format"""
        
        standardized = {
            'overall_score': data.get('overall_score', {}),
            'analysis_summary': data.get('analysis_summary', {}),
            'recommendations': data.get('recommendations', []),
            'page_scores': data.get('page_scores', []),
            'benchmarks': data.get('benchmarks', {}),
            '_metadata': {
                'tool_type': 'geoevaluator',
                'website_url': data.get('metadata', {}).get('website_url', ''),
                'website_name': data.get('metadata', {}).get('website_name', ''),
                'pages_analyzed': data.get('metadata', {}).get('pages_analyzed', 0),
                'timestamp': data.get('metadata', {}).get('timestamp', ''),
                'analysis_duration': data.get('metadata', {}).get('analysis_duration_seconds', 0)
            }
        }
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def _standardize_llmstxtgenerator_data(self, data: Dict) -> Dict:
        """Standardize llmstxtgenerator data format"""
        
        metadata = data.get('metadata', {})
        generation_summary = data.get('generation_summary', {})
        site_analysis = data.get('site_analysis', {})
        
        standardized = {
            'generation_summary': generation_summary,
            'site_analysis': site_analysis,
            'files_generated': data.get('files_generated', {}),
            '_metadata': {
                'tool_type': 'llmstxtgenerator',
                'website_url': metadata.get('website_url', ''),
                'website_name': metadata.get('website_name', ''),
                'timestamp': metadata.get('timestamp', ''),
                'configuration': metadata.get('configuration', {}),
                'tool_version': metadata.get('tool_version', '1.0.0')
            }
        }
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized
    
    def get_available_data(self) -> Dict[str, List[str]]:
        """Get all available tool data organized by tool"""
        available = {}
        
        tools = self.discover_tools()
        for tool in tools:
            runs = self.get_tool_runs(tool)
            available[tool] = [run[0] for run in runs]  # Just the date strings
        
        return available
    
    def get_latest_data_summary(self) -> List[Dict]:
        """Get a summary of the latest run from each tool"""
        summary = []
        
        tools = self.discover_tools()
        for tool in tools:
            runs = self.get_tool_runs(tool)
            if runs:
                latest_run = runs[0][0]
                data = self.load_tool_data(tool, latest_run)
                if data:
                    metadata = data.get('_metadata', {})
                    summary.append({
                        'tool_name': tool,
                        'latest_run': latest_run,
                        'tool_type': metadata.get('tool_type', 'unknown'),
                        'data_available': True,
                        'summary_stats': self._get_summary_stats(data)
                    })
                else:
                    summary.append({
                        'tool_name': tool,
                        'latest_run': latest_run,
                        'tool_type': 'unknown',
                        'data_available': False,
                        'summary_stats': {}
                    })
        
        return summary
    
    def _get_summary_stats(self, data: Dict) -> Dict:
        """Get summary statistics for a dataset"""
        metadata = data.get('_metadata', {})
        tool_type = metadata.get('tool_type', 'unknown')
        
        if tool_type == 'intentcrawler':
            return {
                'total_pages': data.get('total_pages_analyzed', 0),
                'total_intents': data.get('total_intents_discovered', 0),
                'sections': len(data.get('by_section', {}))
            }
        elif tool_type == 'geoevaluator':
            overall_score = data.get('overall_score', {})
            return {
                'total_score': overall_score.get('total_score', 0),
                'grade': overall_score.get('grade', 'Unknown'),
                'pages_analyzed': data.get('_metadata', {}).get('pages_analyzed', 0),
                'recommendations': len(data.get('recommendations', []))
            }
        elif tool_type == 'llmstxtgenerator':
            generation_summary = data.get('generation_summary', {})
            site_analysis = data.get('site_analysis', {})
            return {
                'pages_crawled': generation_summary.get('pages_crawled', 0),
                'sections_detected': generation_summary.get('sections_detected', 0),
                'total_links': generation_summary.get('total_links_generated', 0),
                'files_generated': generation_summary.get('files_generated', 0),
                'success_rate': round(generation_summary.get('success_rate', 0), 1)
            }
        
        elif tool_type == 'graspevaluator':
            aggregate = data.get('aggregate', {})
            return {
                'grasp_score': aggregate.get('average_grasp_score', 0),
                'pages_evaluated': aggregate.get('total_pages', 0),
                'grade_distribution': aggregate.get('grade_distribution', {}),
                'total_words': aggregate.get('total_word_count', 0)
            }
        
        # Default stats for unknown tools
        return {
            'data_size': len(str(data))
        }
    
    def _standardize_graspevaluator_data(self, data: Dict) -> Dict:
        """Standardize GRASP evaluator data format"""
        
        # Calculate letter grade from overall score
        overall_score = data.get('overall_score', 0)
        if overall_score >= 90:
            letter_grade = 'A'
        elif overall_score >= 80:
            letter_grade = 'B'
        elif overall_score >= 70:
            letter_grade = 'C'
        elif overall_score >= 60:
            letter_grade = 'D'
        else:
            letter_grade = 'F'
        
        standardized = {
            'grasp_score': data.get('overall_score', 0),
            'letter_grade': letter_grade,
            'metrics': data.get('metrics', {}),
            'breakdown': data.get('breakdown', {}),
            'recommendations': data.get('recommendations', []),
            'url': data.get('url', ''),
            'timestamp': data.get('timestamp', ''),
            '_metadata': {
                'tool_type': 'graspevaluator',
                'tool_name': 'GRASP Content Quality Evaluator',
                'version': '1.0.0'
            }
        }
        
        # Copy any additional fields
        for key, value in data.items():
            if key not in standardized:
                standardized[key] = value
        
        return standardized

# Convenience function for easy imports
def load_tool_data(tool_name: str, run_date: str = None, tools_root: str = None) -> Optional[Dict]:
    """Quick function to load data from a specific tool"""
    loader = ToolDataLoader(tools_root)
    return loader.load_tool_data(tool_name, run_date)