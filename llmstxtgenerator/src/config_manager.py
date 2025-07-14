import yaml
import os
from typing import Dict, Any, List, Optional


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.validate_config(config)
        return config
    
    def validate_config(self, config: Dict[str, Any]):
        required_sections = ['website', 'generation', 'analysis', 'output', 'crawling']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        if 'url' not in config['website']:
            raise ValueError("Website URL is required in configuration")
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any):
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    @property
    def website_url(self) -> str:
        return self.get('website.url', '')
    
    @property
    def website_name(self) -> Optional[str]:
        return self.get('website.name')
    
    @property
    def website_description(self) -> Optional[str]:
        return self.get('website.description')
    
    @property
    def max_pages(self) -> int:
        return self.get('generation.max_pages', 100)
    
    @property
    def max_depth(self) -> int:
        return self.get('generation.max_depth', 3)
    
    @property
    def include_patterns(self) -> List[str]:
        return self.get('generation.include_patterns', ['.*'])
    
    @property
    def exclude_patterns(self) -> List[str]:
        return self.get('generation.exclude_patterns', [])
    
    @property
    def min_pages_per_section(self) -> int:
        return self.get('generation.min_pages_per_section', 2)
    
    @property
    def ignore_segments(self) -> List[str]:
        return self.get('generation.ignore_segments', ['p', 'c', 's', 'id', 'category', 'page'])
    
    @property
    def max_links_per_section(self) -> int:
        return self.get('generation.max_links_per_section', 20)
    
    @property
    def use_ai_descriptions(self) -> bool:
        return self.get('analysis.use_ai_descriptions', True)
    
    @property
    def ai_model(self) -> str:
        return self.get('analysis.ai_model', 'gpt-4o-mini')
    
    @property
    def output_directory(self) -> str:
        return self.get('output.directory', 'results')
    
    @property
    def output_formats(self) -> List[str]:
        return self.get('output.formats', ['txt'])
    
    @property
    def user_agent(self) -> str:
        return self.get('crawling.user_agent', 'LLMS.txt Generator Bot')
    
    @property
    def request_delay(self) -> float:
        return self.get('crawling.delay', 0.5)
    
    @property
    def request_timeout(self) -> int:
        return self.get('crawling.timeout', 30)