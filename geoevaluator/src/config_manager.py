"""
Configuration management for the GEO Evaluator
"""

import yaml
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from utils import validate_url


class ConfigurationManager:
    """Manages configuration loading, validation, and defaults for GEO Evaluator."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'website': {
                'url': '',
                'name': '',
                'max_pages': 50,
                'crawl_depth': 3,
                'excluded_paths': ['/admin', '/api', '/wp-admin'],
                'included_extensions': ['.html', '.htm', '.php', '.asp', '.aspx', ''],
                'follow_redirects': True
            },
            'analysis': {
                'weights': {
                    'structural_html': 0.25,
                    'content_organization': 0.30,
                    'token_efficiency': 0.20,
                    'llm_technical': 0.15,
                    'accessibility': 0.10
                },
                'thresholds': {
                    'semantic_html_excellent': 0.80,
                    'semantic_html_good': 0.60,
                    'semantic_html_fair': 0.40,
                    'readability_optimal_min': 15,
                    'readability_optimal_max': 20,
                    'content_markup_ratio_excellent': 0.70,
                    'content_markup_ratio_good': 0.50,
                    'content_markup_ratio_fair': 0.30
                },
                'llms_txt': {
                    'required': True,
                    'validate_format': True,
                    'check_completeness': True
                },
                'schema_markup': {
                    'organization_required': True,
                    'webpage_recommended': True,
                    'article_recommended': True,
                    'faq_recommended': True
                }
            },
            'crawling': {
                'delay_seconds': 1.0,
                'timeout_seconds': 30,
                'max_retries': 3,
                'user_agent': 'GEO-Evaluator/1.0 (+https://airbais.com/tools)',
                'respect_robots_txt': True,
                'follow_sitemaps': True,
                'max_file_size_mb': 10
            },
            'output': {
                'formats': ['json', 'dashboard'],
                'include_recommendations': True,
                'detail_level': 'comprehensive',
                'export_path': './results',
                'generate_html_report': True,
                'include_page_details': True
            }
        }
    
    def load_from_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            
            if not file_config:
                file_config = {}
            
            # Merge with defaults
            config = self._merge_with_defaults(file_config)
            
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except FileNotFoundError:
            raise ValueError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def create_from_args(self, args) -> Dict[str, Any]:
        """Create configuration from command line arguments."""
        
        config = self.get_default_config()
        
        # Apply CLI arguments
        if args.url:
            config['website']['url'] = args.url
        
        if args.name:
            config['website']['name'] = args.name
        
        if hasattr(args, 'max_pages') and args.max_pages:
            config['website']['max_pages'] = args.max_pages
        
        if hasattr(args, 'crawl_depth') and args.crawl_depth:
            config['website']['crawl_depth'] = args.crawl_depth
        
        if hasattr(args, 'output_dir') and args.output_dir:
            config['output']['export_path'] = args.output_dir
        
        if hasattr(args, 'formats') and args.formats:
            config['output']['formats'] = args.formats
        
        if hasattr(args, 'delay') and args.delay:
            config['crawling']['delay_seconds'] = args.delay
        
        if hasattr(args, 'timeout') and args.timeout:
            config['crawling']['timeout_seconds'] = args.timeout
        
        # Set website name from URL if not provided
        if not config['website']['name'] and config['website']['url']:
            from utils import extract_domain
            domain = extract_domain(config['website']['url'])
            config['website']['name'] = domain.replace('www.', '').replace('.com', '').title()
        
        return config
    
    def apply_cli_overrides(self, config: Dict[str, Any], args) -> Dict[str, Any]:
        """Apply CLI argument overrides to existing config."""
        
        # Override with CLI arguments if provided
        if hasattr(args, 'max_pages') and args.max_pages:
            config['website']['max_pages'] = args.max_pages
        
        if hasattr(args, 'crawl_depth') and args.crawl_depth:
            config['website']['crawl_depth'] = args.crawl_depth
        
        if hasattr(args, 'output_dir') and args.output_dir:
            config['output']['export_path'] = args.output_dir
        
        if hasattr(args, 'formats') and args.formats:
            config['output']['formats'] = args.formats
        
        if hasattr(args, 'delay') and args.delay:
            config['crawling']['delay_seconds'] = args.delay
        
        if hasattr(args, 'timeout') and args.timeout:
            config['crawling']['timeout_seconds'] = args.timeout
        
        # Dashboard mode
        if hasattr(args, 'dashboard') and args.dashboard:
            if 'dashboard' not in config['output']['formats']:
                config['output']['formats'].append('dashboard')
        
        return config
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        
        errors = []
        warnings = []
        
        # Validate website configuration
        website_config = config.get('website', {})
        
        # URL validation
        url = website_config.get('url', '')
        if not url:
            errors.append("Website URL is required")
        else:
            url_validation = validate_url(url)
            if not url_validation['valid']:
                errors.extend(url_validation['errors'])
        
        # Name validation
        if not website_config.get('name', ''):
            warnings.append("Website name not specified - will be derived from URL")
        
        # Numeric validations
        max_pages = website_config.get('max_pages', 0)
        if not isinstance(max_pages, int) or max_pages <= 0:
            errors.append("max_pages must be a positive integer")
        elif max_pages > 1000:
            warnings.append("max_pages > 1000 may result in very long analysis times")
        
        crawl_depth = website_config.get('crawl_depth', 0)
        if not isinstance(crawl_depth, int) or crawl_depth < 0:
            errors.append("crawl_depth must be a non-negative integer")
        elif crawl_depth > 5:
            warnings.append("crawl_depth > 5 may result in excessive crawling")
        
        # Validate analysis weights
        analysis_config = config.get('analysis', {})
        weights = analysis_config.get('weights', {})
        
        required_weights = ['structural_html', 'content_organization', 'token_efficiency', 
                           'llm_technical', 'accessibility']
        
        weight_sum = 0
        for weight_name in required_weights:
            weight_value = weights.get(weight_name, 0)
            if not isinstance(weight_value, (int, float)) or weight_value < 0:
                errors.append(f"Weight '{weight_name}' must be a non-negative number")
            else:
                weight_sum += weight_value
        
        if abs(weight_sum - 1.0) > 0.01:  # Allow small floating point errors
            errors.append(f"Analysis weights must sum to 1.0 (current sum: {weight_sum:.3f})")
        
        # Validate crawling configuration
        crawling_config = config.get('crawling', {})
        
        delay = crawling_config.get('delay_seconds', 0)
        if not isinstance(delay, (int, float)) or delay < 0:
            errors.append("delay_seconds must be a non-negative number")
        elif delay > 10:
            warnings.append("delay_seconds > 10 may result in very slow crawling")
        
        timeout = crawling_config.get('timeout_seconds', 0)
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append("timeout_seconds must be a positive integer")
        
        # Validate output configuration
        output_config = config.get('output', {})
        
        formats = output_config.get('formats', [])
        if not isinstance(formats, list) or not formats:
            errors.append("At least one output format must be specified")
        else:
            valid_formats = ['json', 'html', 'dashboard']
            for fmt in formats:
                if fmt not in valid_formats:
                    errors.append(f"Invalid output format: {fmt}. Valid formats: {valid_formats}")
        
        export_path = output_config.get('export_path', '')
        if not export_path:
            errors.append("export_path must be specified")
        else:
            # Check if path is writable
            try:
                path_obj = Path(export_path)
                path_obj.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = path_obj / '.test_write'
                test_file.write_text('test')
                test_file.unlink()
                
            except Exception as e:
                errors.append(f"Cannot write to export_path '{export_path}': {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def save_config(self, config: Dict[str, Any], output_path: str) -> None:
        """Save configuration to YAML file."""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=True)
            
            self.logger.info(f"Configuration saved to {output_path}")
            
        except Exception as e:
            raise ValueError(f"Error saving configuration: {e}")
    
    def create_example_config(self, output_path: str, url: str = "https://gofastmcp.com", 
                             name: str = "FastMCP") -> None:
        """Create an example configuration file."""
        
        config = self.get_default_config()
        config['website']['url'] = url
        config['website']['name'] = name
        
        # Add some comments to the YAML
        config_text = f"""# GEO Evaluator Configuration
# Generated example configuration

website:
  url: "{url}"
  name: "{name}"
  max_pages: 50              # Maximum number of pages to analyze
  crawl_depth: 3             # Maximum link depth from starting URL
  excluded_paths:            # Paths to exclude from analysis
    - "/admin"
    - "/api"
    - "/wp-admin"
  follow_redirects: true     # Follow HTTP redirects

analysis:
  weights:                   # Scoring weights (must sum to 1.0)
    structural_html: 0.25    # HTML structure and semantic markup
    content_organization: 0.30  # Content readability and organization
    token_efficiency: 0.20   # Content-to-markup ratio and density
    llm_technical: 0.15      # LLM-specific optimizations
    accessibility: 0.10      # Content accessibility and clarity
  
  thresholds:
    semantic_html_excellent: 0.80  # Threshold for excellent semantic HTML usage
    semantic_html_good: 0.60       # Threshold for good semantic HTML usage
    readability_optimal_min: 15    # Optimal minimum words per sentence
    readability_optimal_max: 20    # Optimal maximum words per sentence
  
  llms_txt:
    required: true           # Require llms.txt file presence
    validate_format: true    # Validate llms.txt format
    check_completeness: true # Check llms.txt completeness

crawling:
  delay_seconds: 1.0         # Delay between requests (be respectful!)
  timeout_seconds: 30        # Request timeout
  user_agent: "GEO-Evaluator/1.0"
  respect_robots_txt: true   # Respect robots.txt directives
  follow_sitemaps: true      # Use sitemap.xml for URL discovery

output:
  formats:                   # Output formats to generate
    - "json"                 # Machine-readable results
    - "dashboard"            # Dashboard integration
  export_path: "./results"   # Directory for output files
  include_recommendations: true  # Include optimization recommendations
  detail_level: "comprehensive"  # Level of detail in reports
"""
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(config_text)
            
            self.logger.info(f"Example configuration created at {output_path}")
            
        except Exception as e:
            raise ValueError(f"Error creating example configuration: {e}")
    
    def _merge_with_defaults(self, file_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge file configuration with defaults."""
        
        default_config = self.get_default_config()
        
        # Deep merge function
        def deep_merge(default: Dict, override: Dict) -> Dict:
            result = default.copy()
            
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            
            return result
        
        return deep_merge(default_config, file_config)