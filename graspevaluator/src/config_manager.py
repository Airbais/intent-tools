"""
Configuration management for GRASP evaluator
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv


class ConfigManager:
    """Manages configuration for GRASP evaluator"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load environment variables
        load_dotenv()
        
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        current_dir = Path(__file__).parent.parent
        return str(current_dir / "config" / "grasp_config.yaml")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            # Return default configuration
            return self._get_default_config()
        except Exception as e:
            raise Exception(f"Error loading config from {self.config_path}: {e}")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'evaluator': {
                'name': 'GRASP Content Quality Evaluator'
            },
            'targets': [
                {'url': 'https://airbais.com'}
            ],
            'grounded': {
                'intents': [
                    "How can I determine if my website content is GEO optimized?",
                    "How do I contact Airbais?",
                    "What tools does Airbais offer?",
                    "How do I get started using Airbais tools?",
                    "How do Airbais tools help my business?",
                    "What is the mission of Airbais?",
                    "How is GEO different from SEO?"
                ]
            },
            'readable': {
                'target_audience': 'general_public'
            },
            'accurate': {
                'freshness_thresholds': {
                    'high': 180,
                    'medium': 365
                }
            },
            'structured': {
                'check_headings': True,
                'check_semantic_elements': True,
                'check_schema_markup': True
            },
            'polished': {
                'check_grammar': True,
                'check_spelling': True,
                'check_style': True,
                'use_llm': True
            }
        }
    
    def get_intents(self) -> List[str]:
        """Get customer intents for grounded evaluation"""
        return self.config.get('grounded', {}).get('intents', [])
    
    def get_target_audience(self) -> str:
        """Get target audience for readable evaluation"""
        return self.config.get('readable', {}).get('target_audience', 'general_public')
    
    def get_freshness_thresholds(self) -> Dict[str, int]:
        """Get freshness thresholds for accurate evaluation"""
        return self.config.get('accurate', {}).get('freshness_thresholds', {
            'high': 180,
            'medium': 365
        })
    
    def get_structured_config(self) -> Dict:
        """Get structured evaluation configuration"""
        return self.config.get('structured', {
            'check_headings': True,
            'check_semantic_elements': True,
            'check_schema_markup': True
        })
    
    def get_polished_config(self) -> Dict:
        """Get polished evaluation configuration"""
        return self.config.get('polished', {
            'check_grammar': True,
            'check_spelling': True,
            'check_style': True,
            'use_llm': True
        })
    
    def get_target_urls(self) -> List[str]:
        """Get target URLs for evaluation"""
        targets = self.config.get('targets', [])
        return [target.get('url') for target in targets if target.get('url')]
    
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key from environment"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return api_key
    
    def save_config(self, output_path: Optional[str] = None):
        """Save current configuration to file"""
        if output_path is None:
            output_path = self.config_path
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)