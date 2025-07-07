"""
Prompt Executor with Caching
Handles executing prompts against LLMs with caching and progress tracking
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import diskcache
from tqdm import tqdm

from .config import Prompt, EvaluationSettings, LLMConfig
from .llm_interface import LLMInterface

@dataclass
class PromptResult:
    prompt_id: str
    prompt_text: str
    category: str
    response: str
    llm_name: str
    provider: str
    model: str
    timestamp: str
    cached: bool = False
    error: Optional[str] = None

@dataclass
class MultiLLMPromptResult:
    prompt_id: str
    prompt_text: str
    category: str
    llm_results: Dict[str, PromptResult]  # key: llm.name

class PromptExecutor:
    def __init__(self, llm_interface: LLMInterface, cache_dir: str = "./cache", 
                 cache_expire_hours: int = 24):
        self.llm_interface = llm_interface
        self.logger = logging.getLogger(__name__)
        
        # Set up caching
        cache_path = Path(cache_dir).absolute()
        cache_path.mkdir(parents=True, exist_ok=True)
        self.cache = diskcache.Cache(str(cache_path))
        self.cache_expire_seconds = cache_expire_hours * 3600
        
        self.logger.info(f"Initialized cache at {cache_path} with {cache_expire_hours}h expiration")
    
    def _generate_cache_key(self, prompt: str, provider: str, model: str, 
                           temperature: float, max_tokens: int) -> str:
        """Generate a unique cache key for a prompt"""
        key_data = {
            'prompt': prompt,
            'provider': provider,
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        try:
            return self.cache.get(cache_key)
        except Exception as e:
            self.logger.warning(f"Cache retrieval error: {e}")
            return None
    
    def _cache_response(self, cache_key: str, response: str) -> None:
        """Cache a response with expiration"""
        try:
            self.cache.set(cache_key, response, expire=self.cache_expire_seconds)
        except Exception as e:
            self.logger.warning(f"Cache storage error: {e}")
    
    def execute_single_prompt(self, prompt: Prompt, llm_config: LLMConfig, 
                            settings: EvaluationSettings, use_cache: bool = True) -> PromptResult:
        """Execute a single prompt against a single LLM and return the result"""
        # Set the provider for this LLM
        self.llm_interface.set_provider(llm_config.provider)
        provider = llm_config.provider
        model = llm_config.model
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            prompt.text, provider, model, 
            llm_config.temperature, llm_config.max_tokens
        )
        
        # Check cache if enabled
        cached_response = None
        if use_cache and settings.cache_responses:
            cached_response = self._get_cached_response(cache_key)
        
        if cached_response is not None:
            self.logger.debug(f"Using cached response for prompt: {prompt.id} with {llm_config.name}")
            return PromptResult(
                prompt_id=prompt.id,
                prompt_text=prompt.text,
                category=prompt.category,
                response=cached_response,
                llm_name=llm_config.name,
                provider=provider,
                model=model,
                timestamp=datetime.now().isoformat(),
                cached=True
            )
        
        # Generate new response
        try:
            self.logger.info(f"Executing prompt {prompt.id} with {llm_config.name}: {prompt.text[:50]}...")
            response = self.llm_interface.generate(
                prompt=prompt.text,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                provider=llm_config.provider,
                model=llm_config.model
            )
            
            # Cache the response
            if use_cache and settings.cache_responses:
                self._cache_response(cache_key, response)
            
            return PromptResult(
                prompt_id=prompt.id,
                prompt_text=prompt.text,
                category=prompt.category,
                response=response,
                llm_name=llm_config.name,
                provider=provider,
                model=model,
                timestamp=datetime.now().isoformat(),
                cached=False
            )
        
        except Exception as e:
            self.logger.error(f"Error executing prompt {prompt.id}: {e}")
            return PromptResult(
                prompt_id=prompt.id,
                prompt_text=prompt.text,
                category=prompt.category,
                response="",
                llm_name=llm_config.name,
                provider=provider,
                model=model,
                timestamp=datetime.now().isoformat(),
                cached=False,
                error=str(e)
            )
    
    def execute_prompt_multi_llm(self, prompt: Prompt, llms: List[LLMConfig],
                                settings: EvaluationSettings, use_cache: bool = True) -> MultiLLMPromptResult:
        """Execute a single prompt against multiple LLMs"""
        result = MultiLLMPromptResult(
            prompt_id=prompt.id,
            prompt_text=prompt.text,
            category=prompt.category,
            llm_results={}
        )
        
        for llm in llms:
            llm_result = self.execute_single_prompt(prompt, llm, settings, use_cache)
            result.llm_results[llm.name] = llm_result
        
        return result
    
    def execute_batch(self, prompts: List[Prompt], settings: EvaluationSettings,
                     show_progress: bool = True) -> List[MultiLLMPromptResult]:
        """Execute a batch of prompts against all configured LLMs"""
        results = []
        llms = settings.llms
        
        if not llms:
            raise ValueError("No LLMs configured in settings")
        
        # Calculate total operations for progress bar
        total_operations = len(prompts) * len(llms)
        
        # Create progress bar if requested
        if show_progress:
            pbar = tqdm(total=total_operations, desc="Executing prompts")
        
        for prompt in prompts:
            prompt_result = MultiLLMPromptResult(
                prompt_id=prompt.id,
                prompt_text=prompt.text,
                category=prompt.category,
                llm_results={}
            )
            
            for llm in llms:
                if show_progress:
                    pbar.set_description(f"Prompt {prompt.id} - LLM: {llm.name}")
                
                llm_result = self.execute_single_prompt(prompt, llm, settings, 
                                                       use_cache=settings.cache_responses)
                prompt_result.llm_results[llm.name] = llm_result
                
                if show_progress:
                    status = "cached" if llm_result.cached else "generated"
                    pbar.set_postfix({"status": status, "llm": llm.name})
                    pbar.update(1)
            
            results.append(prompt_result)
        
        if show_progress:
            pbar.close()
        
        # Log summary
        total_prompts = len(results)
        total_llm_calls = sum(len(r.llm_results) for r in results)
        cached_calls = sum(1 for r in results for lr in r.llm_results.values() if lr.cached)
        error_calls = sum(1 for r in results for lr in r.llm_results.values() if lr.error)
        
        self.logger.info(f"Batch execution complete: {total_prompts} prompts, "
                        f"{len(llms)} LLMs, {total_llm_calls} total calls, "
                        f"{cached_calls} cached, {error_calls} errors")
        
        return results
    
    def clear_cache(self) -> None:
        """Clear all cached responses"""
        try:
            self.cache.clear()
            self.logger.info("Cache cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def execute_batch_single_llm(self, prompts: List[Prompt], llm_config: LLMConfig,
                                settings: EvaluationSettings, show_progress: bool = True) -> List[PromptResult]:
        """Execute a batch of prompts with a single LLM (backward compatibility)"""
        results = []
        
        # Create progress bar if requested
        iterator = tqdm(prompts, desc=f"Executing prompts with {llm_config.name}") if show_progress else prompts
        
        for prompt in iterator:
            result = self.execute_single_prompt(prompt, llm_config, settings)
            results.append(result)
            
            if show_progress and isinstance(iterator, tqdm):
                # Update progress bar description
                status = "cached" if result.cached else "generated"
                iterator.set_postfix({"status": status, "prompt": prompt.id})
        
        # Log summary
        total = len(results)
        cached = sum(1 for r in results if r.cached)
        errors = sum(1 for r in results if r.error)
        
        self.logger.info(f"Batch execution complete for {llm_config.name}: {total} prompts, "
                        f"{cached} cached, {errors} errors")
        
        return results
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        try:
            return {
                'size': len(self.cache),
                'volume': self.cache.volume(),
                'directory': str(self.cache.directory)
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}