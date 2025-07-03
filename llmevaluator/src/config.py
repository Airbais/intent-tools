"""
Configuration Manager for LLM Evaluator
Handles loading and parsing of markdown configuration files
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import yaml
import markdown
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BrandInfo:
    name: str
    website: str
    aliases: List[str] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)

@dataclass
class Prompt:
    text: str
    category: str
    id: Optional[str] = None

@dataclass
class EvaluationSettings:
    llm_provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 500
    cache_responses: bool = True
    sentiment_method: str = "hybrid"

@dataclass
class LLMProviderConfig:
    name: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    models: List[str] = field(default_factory=list)

class ConfigurationManager:
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path) if config_path else None
        self.brand_info: Optional[BrandInfo] = None
        self.prompts: List[Prompt] = []
        self.settings: EvaluationSettings = EvaluationSettings()
        self.llm_providers: Dict[str, LLMProviderConfig] = self._load_default_providers()
        
        if self.config_path and self.config_path.exists():
            self.load_configuration()
    
    def _load_default_providers(self) -> Dict[str, LLMProviderConfig]:
        """Load default LLM provider configurations"""
        providers = {}
        
        # OpenAI Configuration
        providers['openai'] = LLMProviderConfig(
            name='openai',
            endpoint=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
            api_key=os.getenv('OPENAI_API_KEY'),
            models=['gpt-4', 'gpt-4-turbo-preview', 'gpt-3.5-turbo']
        )
        
        # Anthropic Configuration
        providers['anthropic'] = LLMProviderConfig(
            name='anthropic',
            endpoint=os.getenv('ANTHROPIC_API_BASE', 'https://api.anthropic.com'),
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            models=['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
        )
        
        return providers
    
    def load_configuration(self, config_path: Optional[str] = None) -> None:
        """Load configuration from markdown file"""
        if config_path:
            self.config_path = Path(config_path)
        
        if not self.config_path or not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self._parse_markdown_config(content)
        self.logger.info(f"Loaded configuration from {self.config_path}")
    
    def _parse_markdown_config(self, content: str) -> None:
        """Parse markdown configuration content"""
        lines = content.split('\n')
        current_section = None
        current_category = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for main sections
            if line.startswith('## Brand Information'):
                current_section = 'brand'
                self.brand_info = self._parse_brand_section(lines, i + 1)
            elif line.startswith('## Evaluation Prompts'):
                current_section = 'prompts'
                self.prompts = self._parse_prompts_section(lines, i + 1)
            elif line.startswith('## Evaluation Settings'):
                current_section = 'settings'
                self._parse_settings_section(lines, i + 1)
            elif line.startswith('## LLM Providers'):
                current_section = 'providers'
                self._parse_providers_section(lines, i + 1)
            
            i += 1
    
    def _parse_brand_section(self, lines: List[str], start_idx: int) -> BrandInfo:
        """Parse brand information section"""
        brand_data = {}
        i = start_idx
        
        while i < len(lines) and not lines[i].strip().startswith('##'):
            line = lines[i].strip()
            
            if line.startswith('- '):
                # Parse key-value pairs
                match = re.match(r'- \*?\*?(\w+)\*?\*?: (.+)', line)
                if match:
                    key, value = match.groups()
                    key = key.lower().replace(' ', '_')
                    
                    if key in ['aliases', 'competitors']:
                        # Parse list values
                        value = self._parse_list_value(value)
                    
                    brand_data[key] = value
            
            i += 1
        
        return BrandInfo(
            name=brand_data.get('name', ''),
            website=brand_data.get('website', ''),
            aliases=brand_data.get('aliases', []),
            competitors=brand_data.get('competitors', [])
        )
    
    def _parse_prompts_section(self, lines: List[str], start_idx: int) -> List[Prompt]:
        """Parse evaluation prompts section"""
        prompts = []
        current_category = None
        i = start_idx
        prompt_id = 1
        
        while i < len(lines) and not lines[i].strip().startswith('## '):
            line = lines[i].strip()
            
            if line.startswith('### Category:'):
                current_category = line.replace('### Category:', '').strip()
            elif re.match(r'^\d+\.', line) and current_category:
                # Extract prompt text
                prompt_text = re.sub(r'^\d+\.\s*', '', line)
                prompts.append(Prompt(
                    text=prompt_text,
                    category=current_category,
                    id=f"prompt_{prompt_id}"
                ))
                prompt_id += 1
            
            i += 1
        
        return prompts
    
    def _parse_settings_section(self, lines: List[str], start_idx: int) -> None:
        """Parse evaluation settings section"""
        settings_data = {}
        i = start_idx
        
        while i < len(lines) and not lines[i].strip().startswith('##'):
            line = lines[i].strip()
            
            if line.startswith('- '):
                match = re.match(r'- \*?\*?(\w+[\w\s]*)\*?\*?: (.+)', line)
                if match:
                    key, value = match.groups()
                    key = key.lower().replace(' ', '_')
                    
                    # Convert values to appropriate types
                    if key == 'temperature':
                        value = float(value)
                    elif key == 'max_tokens':
                        value = int(value)
                    elif key == 'cache_responses':
                        value = value.lower() == 'true'
                    
                    settings_data[key] = value
            
            i += 1
        
        # Update settings with parsed values
        for key, value in settings_data.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
    
    def _parse_providers_section(self, lines: List[str], start_idx: int) -> None:
        """Parse LLM providers configuration section"""
        i = start_idx
        current_provider = None
        
        while i < len(lines) and not lines[i].strip().startswith('##'):
            line = lines[i].strip()
            
            if line.startswith('### '):
                # New provider
                provider_name = line.replace('###', '').strip().lower()
                current_provider = provider_name
                if provider_name not in self.llm_providers:
                    self.llm_providers[provider_name] = LLMProviderConfig(name=provider_name)
            elif line.startswith('- ') and current_provider:
                match = re.match(r'- \*?\*?(\w+)\*?\*?: (.+)', line)
                if match:
                    key, value = match.groups()
                    key = key.lower()
                    
                    if key == 'endpoint':
                        self.llm_providers[current_provider].endpoint = value
                    elif key == 'api_key':
                        # Check if it's an environment variable reference
                        if value.startswith('$'):
                            env_var = value[1:]
                            value = os.getenv(env_var)
                        self.llm_providers[current_provider].api_key = value
                    elif key == 'models':
                        self.llm_providers[current_provider].models = self._parse_list_value(value)
            
            i += 1
    
    def _parse_list_value(self, value: str) -> List[str]:
        """Parse a list value from markdown"""
        # Remove brackets if present
        value = value.strip('[]')
        # Split by comma and clean up
        items = [item.strip().strip('"\'') for item in value.split(',')]
        return items
    
    def get_provider_config(self, provider_name: str) -> Optional[LLMProviderConfig]:
        """Get configuration for a specific LLM provider"""
        return self.llm_providers.get(provider_name)
    
    def validate_configuration(self) -> List[str]:
        """Validate the loaded configuration and return any issues"""
        issues = []
        
        if not self.brand_info or not self.brand_info.name:
            issues.append("Brand name is required")
        
        if not self.prompts:
            issues.append("At least one evaluation prompt is required")
        
        # Check if selected provider is configured
        provider = self.get_provider_config(self.settings.llm_provider)
        if not provider:
            issues.append(f"LLM provider '{self.settings.llm_provider}' is not configured")
        elif not provider.api_key:
            issues.append(f"API key for '{self.settings.llm_provider}' is not set")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'brand_info': {
                'name': self.brand_info.name,
                'website': self.brand_info.website,
                'aliases': self.brand_info.aliases,
                'competitors': self.brand_info.competitors
            } if self.brand_info else None,
            'prompts': [
                {
                    'id': p.id,
                    'text': p.text,
                    'category': p.category
                } for p in self.prompts
            ],
            'settings': {
                'llm_provider': self.settings.llm_provider,
                'model': self.settings.model,
                'temperature': self.settings.temperature,
                'max_tokens': self.settings.max_tokens,
                'cache_responses': self.settings.cache_responses,
                'sentiment_method': self.settings.sentiment_method
            }
        }