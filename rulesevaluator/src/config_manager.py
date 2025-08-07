"""Configuration management for Rules Evaluator"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            config_path: Path to configuration file (defaults to config.yaml)
        """
        self.config_path = config_path or "config.yaml"
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._substitute_env_vars()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        load_dotenv()  # Load environment variables
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def _substitute_env_vars(self) -> None:
        """Substitute environment variables in configuration"""
        def _substitute_recursive(obj):
            if isinstance(obj, dict):
                return {k: _substitute_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_substitute_recursive(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                env_var = obj[2:-1]
                value = os.getenv(env_var)
                if value is None:
                    logger.warning(f"Environment variable {env_var} not found")
                return value
            return obj
        
        self.config = _substitute_recursive(self.config)
    
    def _validate_config(self) -> None:
        """Validate configuration requirements"""
        required_sections = ['content', 'rag', 'ai_providers', 'rules', 'scoring', 'output']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate content settings
        content_type = self.config['content'].get('type')
        if content_type not in ['website', 'local', 'cloud']:
            raise ValueError(f"Invalid content type: {content_type}")
        
        # Validate AI providers
        if not self.config['ai_providers'].get('response_provider'):
            raise ValueError("No response provider configured")
        if not self.config['ai_providers'].get('evaluation_provider'):
            raise ValueError("No evaluation provider configured")
        
        # Validate scoring weights
        weights = self.config['scoring']['weights']
        total_weight = sum(weights.values())
        if not (99 <= total_weight <= 101):  # Allow small rounding errors
            raise ValueError(f"Scoring weights must sum to 100, got {total_weight}")
        
        # Validate rules file
        rules_file = self.config['rules'].get('file_path')
        if not rules_file:
            raise ValueError("Rules file path not specified")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'content.website.url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_content_config(self) -> Dict[str, Any]:
        """Get content-specific configuration based on content type"""
        content_type = self.config['content']['type']
        type_specific_config = self.config['content'].get(content_type, {})
        
        logger.debug(f"Content type: {content_type}")
        logger.debug(f"Type-specific config: {type_specific_config}")
        
        base_config = {
            'type': content_type,
            **type_specific_config
        }
        
        logger.debug(f"Final content config: {base_config}")
        return base_config
    
    def get_ai_provider(self, provider_type: str = 'response') -> Dict[str, Any]:
        """Get AI provider configuration
        
        Args:
            provider_type: 'response' or 'evaluation'
            
        Returns:
            First provider configuration
        """
        providers = self.config['ai_providers'].get(f'{provider_type}_provider', [])
        if not providers:
            raise ValueError(f"No {provider_type} provider configured")
        return providers[0]
    
    def get_output_dir(self) -> Path:
        """Get output directory path, creating if necessary"""
        output_dir = Path(self.config['output']['results_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def get_cache_dir(self) -> Path:
        """Get cache directory path, creating if necessary"""
        if self.config['general']['enable_cache']:
            cache_dir = Path(self.config['general']['cache_dir'])
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir
        return None
    
    def get_chromadb_path(self) -> Path:
        """Get ChromaDB persistence directory path"""
        db_path = Path(self.config['rag']['persist_directory'])
        db_path.mkdir(parents=True, exist_ok=True)
        return db_path