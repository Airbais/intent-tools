"""
LLM Interface for Multiple Providers
Provides a unified interface for different LLM providers
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import json
from tenacity import retry, stop_after_attempt, wait_exponential

# Import provider libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None, model: str = None):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None, model: str = "gpt-4"):
        super().__init__(api_key, endpoint, model)
        
        if OPENAI_AVAILABLE and api_key:
            try:
                # Use custom httpx client to avoid proxy configuration issues
                import httpx
                http_client = httpx.Client()
                
                client_kwargs = {
                    "api_key": api_key,
                    "http_client": http_client
                }
                if endpoint:
                    client_kwargs["base_url"] = endpoint
                
                self.client = openai.OpenAI(**client_kwargs)
                self.logger.info("OpenAI client initialized successfully with custom http_client")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Generate a response using OpenAI API"""
        if not self.is_available():
            raise RuntimeError("OpenAI provider is not available")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            self.logger.error(f"Error generating response from OpenAI: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        return OPENAI_AVAILABLE and self.client is not None

class AnthropicProvider(LLMProvider):
    """Anthropic API provider"""
    
    def __init__(self, api_key: str, endpoint: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key, endpoint, model)
        
        if ANTHROPIC_AVAILABLE and api_key:
            try:
                # Initialize Anthropic client with minimal parameters
                if endpoint:
                    self.client = anthropic.Anthropic(api_key=api_key, base_url=endpoint)
                else:
                    self.client = anthropic.Anthropic(api_key=api_key)
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Generate a response using Anthropic API"""
        if not self.is_available():
            raise RuntimeError("Anthropic provider is not available")
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from the response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return ""
        
        except Exception as e:
            self.logger.error(f"Error generating response from Anthropic: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Anthropic provider is available"""
        return ANTHROPIC_AVAILABLE and self.client is not None

class LLMInterface:
    """Unified interface for multiple LLM providers"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.logger = logging.getLogger(__name__)
        self.current_provider: Optional[str] = None
    
    def add_provider(self, name: str, provider: LLMProvider) -> None:
        """Add a new LLM provider"""
        self.providers[name] = provider
        self.logger.info(f"Added LLM provider: {name}")
    
    def set_provider(self, name: str) -> None:
        """Set the current active provider"""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        
        if not self.providers[name].is_available():
            raise RuntimeError(f"Provider '{name}' is not available")
        
        self.current_provider = name
        self.logger.info(f"Set current provider to: {name}")
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 500, 
                 provider: Optional[str] = None) -> str:
        """Generate a response using the specified or current provider"""
        provider_name = provider or self.current_provider
        
        if not provider_name:
            raise RuntimeError("No provider selected")
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        provider_obj = self.providers[provider_name]
        self.logger.info(f"Generating response using {provider_name}")
        
        return provider_obj.generate(prompt, temperature, max_tokens)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [name for name, provider in self.providers.items() if provider.is_available()]
    
    @classmethod
    def create_from_config(cls, config) -> 'LLMInterface':
        """Create LLM interface from configuration"""
        interface = cls()
        
        # Add OpenAI provider if configured
        if 'openai' in config.llm_providers:
            provider_config = config.llm_providers['openai']
            if provider_config.api_key:
                provider = OpenAIProvider(
                    api_key=provider_config.api_key,
                    endpoint=provider_config.endpoint,
                    model=config.settings.model if config.settings.llm_provider == 'openai' else 'gpt-4'
                )
                interface.add_provider('openai', provider)
        
        # Add Anthropic provider if configured
        if 'anthropic' in config.llm_providers:
            provider_config = config.llm_providers['anthropic']
            if provider_config.api_key:
                provider = AnthropicProvider(
                    api_key=provider_config.api_key,
                    endpoint=provider_config.endpoint,
                    model=config.settings.model if config.settings.llm_provider == 'anthropic' else 'claude-3-sonnet-20240229'
                )
                interface.add_provider('anthropic', provider)
        
        # Set the default provider
        if config.settings.llm_provider in interface.providers:
            interface.set_provider(config.settings.llm_provider)
        
        return interface