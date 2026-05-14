"""AI provider abstraction layer"""

import logging
import json
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import openai
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def generate_response(self, prompt: str, context: str) -> str:
        """Generate a response given a prompt and context"""
        pass
    
    @abstractmethod
    def evaluate_response(self, response: str, rules: List[Dict], evaluation_prompt: str) -> Dict:
        """Evaluate a response against rules"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider
        
        Args:
            config: Provider configuration
        """
        self.api_key = config.get('api_key')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = config.get('model', 'gpt-4-turbo-preview')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_response(self, prompt: str, context: str) -> str:
        """Generate a response using OpenAI"""
        try:
            messages = [
                {"role": "system", "content": "You are an assistant that ONLY uses the provided context to answer questions. Do not use any external knowledge or information not explicitly contained in the context. If the context doesn't contain sufficient information to answer the question, state that the context doesn't provide enough information rather than using general knowledge."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def evaluate_response(self, response: str, rules: List[Dict], evaluation_prompt: str) -> Dict:
        """Evaluate response against rules using OpenAI"""
        try:
            # Format rules for evaluation
            rules_text = json.dumps(rules, indent=2)
            
            messages = [
                {"role": "system", "content": evaluation_prompt},
                {"role": "user", "content": f"AI Response to evaluate:\n{response}\n\nRules:\n{rules_text}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent evaluation
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI evaluation response: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI evaluation error: {e}")
            raise


class AnthropicProvider(AIProvider):
    """Anthropic provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider
        
        Args:
            config: Provider configuration
        """
        self.api_key = config.get('api_key')
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = config.get('model', 'claude-3-opus-20240229')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_response(self, prompt: str, context: str) -> str:
        """Generate a response using Anthropic"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="You are an assistant that ONLY uses the provided context to answer questions. Do not use any external knowledge or information not explicitly contained in the context. If the context doesn't contain sufficient information to answer the question, state that the context doesn't provide enough information rather than using general knowledge.",
                messages=[
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def evaluate_response(self, response: str, rules: List[Dict], evaluation_prompt: str) -> Dict:
        """Evaluate response against rules using Anthropic"""
        try:
            # Format rules for evaluation
            rules_text = json.dumps(rules, indent=2)
            
            # Add JSON instruction to evaluation prompt
            enhanced_prompt = evaluation_prompt + "\n\nIMPORTANT: Return your evaluation as valid JSON only, with no additional text."
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for consistent evaluation
                system=enhanced_prompt,
                messages=[
                    {"role": "user", "content": f"AI Response to evaluate:\n{response}\n\nRules:\n{rules_text}"}
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            
            # Try to find JSON in the response
            if response_text.startswith('{'):
                return json.loads(response_text)
            else:
                # Look for JSON block in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic evaluation response: {e}")
            raise
        except Exception as e:
            logger.error(f"Anthropic evaluation error: {e}")
            raise


class GrokProvider(AIProvider):
    """Grok provider implementation (using OpenAI-compatible API)"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Grok provider
        
        Args:
            config: Provider configuration
        """
        self.api_key = config.get('api_key')
        if not self.api_key:
            raise ValueError("Grok API key not provided")
        
        # Grok uses OpenAI-compatible API
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"  # Grok API endpoint
        )
        self.model = config.get('model', 'grok-beta')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_response(self, prompt: str, context: str) -> str:
        """Generate a response using Grok"""
        try:
            messages = [
                {"role": "system", "content": "You are an assistant that ONLY uses the provided context to answer questions. Do not use any external knowledge or information not explicitly contained in the context. If the context doesn't contain sufficient information to answer the question, state that the context doesn't provide enough information rather than using general knowledge."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Grok generation error: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def evaluate_response(self, response: str, rules: List[Dict], evaluation_prompt: str) -> Dict:
        """Evaluate response against rules using Grok"""
        try:
            # Format rules for evaluation
            rules_text = json.dumps(rules, indent=2)
            
            messages = [
                {"role": "system", "content": evaluation_prompt},
                {"role": "user", "content": f"AI Response to evaluate:\n{response}\n\nRules:\n{rules_text}"}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent evaluation
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON from response
            if response_text.startswith('{'):
                return json.loads(response_text)
            else:
                # Look for JSON block in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Grok evaluation response: {e}")
            raise
        except Exception as e:
            logger.error(f"Grok evaluation error: {e}")
            raise


class AIProviderFactory:
    """Factory for creating AI provider instances"""
    
    PROVIDERS = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'grok': GrokProvider
    }
    
    @classmethod
    def create(cls, provider_config: Dict[str, Any]) -> AIProvider:
        """Create an AI provider instance
        
        Args:
            provider_config: Provider configuration
            
        Returns:
            AI provider instance
        """
        provider_name = provider_config.get('name', '').lower()
        
        if provider_name not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls.PROVIDERS[provider_name]
        return provider_class(provider_config)