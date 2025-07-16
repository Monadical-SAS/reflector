"""
OpenAI LLM implementation with prefix-based configuration.
Allows task-specific LLM configurations like OpenAILLM("SUMMARY").
"""

import httpx
from typing import Any, Dict, Optional

from reflector.llm.base import LLM
from reflector.settings import settings


class OpenAILLM(LLM):
    """
    OpenAI LLM with prefix-based configuration support.
    
    Usage:
        llm = OpenAILLM("SUMMARY")  # Uses SUMMARY_MODEL, SUMMARY_LLM_URL, etc.
        llm = OpenAILLM("TITLE")    # Uses TITLE_MODEL, TITLE_LLM_URL, etc.
    """
    
    def __init__(self, model_name: Optional[str] = None, config_prefix: Optional[str] = None, **overrides):
        """
        Initialize OpenAI LLM with prefix-based configuration.
        
        Args:
            model_name: Model name (matches LLM base class interface)
            config_prefix: Prefix for configuration keys (e.g., "SUMMARY")
            **overrides: Additional configuration overrides
        """
        # Initialize base class first
        super().__init__()
        
        # Set config prefix and load configuration
        self.config_prefix = config_prefix
        self.config = self._load_config(config_prefix, overrides) if config_prefix else {}
        
        # Use provided model_name or fall back to config
        self.model_name = model_name or self.config.get('model') or self.config.get('llm_model')
        
        # Set up HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.config.get('llm_timeout', 300),
            headers=self._get_headers()
        )
        
    def _load_config(self, prefix: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load configuration with prefix support, following Storage pattern.
        
        Looks for settings like:
        - SUMMARY_MODEL -> config['model']
        - SUMMARY_LLM_URL -> config['llm_url']
        - SUMMARY_LLM_API_KEY -> config['llm_api_key']
        """
        config = {}
        config_prefix = f"{prefix}_"
        
        # Gather all settings that start with the prefix
        for key, value in settings:
            if key.startswith(config_prefix):
                # Convert SUMMARY_LLM_URL -> llm_url
                config_name = key[len(config_prefix):].lower()
                config[config_name] = value
        
        # Apply overrides
        config.update(overrides)
        
        # Set defaults for missing required settings
        self._set_defaults(config)
        
        return config
    
    def _set_defaults(self, config: Dict[str, Any]):
        """Set default values for missing configuration."""
        if 'llm_url' not in config:
            config['llm_url'] = getattr(settings, 'LLM_URL', 'https://api.openai.com/v1')
        
        if 'llm_timeout' not in config:
            config['llm_timeout'] = getattr(settings, 'LLM_TIMEOUT', 300)
        
        if 'llm_temperature' not in config:
            config['llm_temperature'] = getattr(settings, 'LLM_TEMPERATURE', 0.7)
        
        if 'llm_max_tokens' not in config:
            config['llm_max_tokens'] = getattr(settings, 'LLM_MAX_TOKENS', 1024)
        
        if 'llm_use_structured_output' not in config:
            config['llm_use_structured_output'] = False
    
    def _get_model_name(self) -> str:
        """Get the currently set model name."""
        return self.model_name
    
    def _set_model_name(self, model_name: str) -> bool:
        """Update the model name."""
        self.model_name = model_name
        return True
    
    def _get_tokenizer(self):
        """Return the tokenizer instance used by LLM."""
        return None  # OpenAI doesn't expose tokenizer
    
    def has_structured_output(self) -> bool:
        """Check if implementation supports structured output."""
        return self.config.get('llm_use_structured_output', False)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
        }
        
        if 'llm_api_key' in self.config:
            headers['Authorization'] = f"Bearer {self.config['llm_api_key']}"
        
        return headers
    
    async def _generate(self, prompt: str, gen_schema=None, gen_cfg=None, logger=None, **kwargs) -> str:
        """
        Generate text using OpenAI-compatible API.
        
        Args:
            prompt: The input prompt
            gen_schema: JSON schema for structured output (optional)
            gen_cfg: Generation configuration (optional)
            logger: Logger instance (optional)
            **kwargs: Additional parameters
            
        Returns:
            Generated text
        """
        # Build request payload
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': self.config.get('llm_temperature', 0.7),
            'max_tokens': self.config.get('llm_max_tokens', 1024),
        }
        
        # Add structured output if supported and requested
        if gen_schema and self.config.get('llm_use_structured_output', False):
            payload['response_format'] = {
                'type': 'json_schema',
                'json_schema': gen_schema
            }
        
        # Apply generation configuration overrides
        if gen_cfg:
            if hasattr(gen_cfg, 'temperature') and gen_cfg.temperature is not None:
                payload['temperature'] = gen_cfg.temperature
            if hasattr(gen_cfg, 'max_tokens') and gen_cfg.max_tokens is not None:
                payload['max_tokens'] = gen_cfg.max_tokens
        
        # Make API request
        url = f"{self.config['llm_url'].rstrip('/')}/chat/completions"
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise ValueError("No choices in response")
                
        except Exception as e:
            if logger:
                logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _completion(self, messages: list, **kwargs) -> dict:
        """
        Use /v1/chat/completion OpenAI compatible endpoint.
        """
        payload = {
            'model': self.model_name,
            'messages': messages,
            'temperature': self.config.get('llm_temperature', 0.7),
            'max_tokens': self.config.get('llm_max_tokens', 1024),
        }
        
        # Apply any additional kwargs
        payload.update(kwargs)
        
        # Make API request
        url = f"{self.config['llm_url'].rstrip('/')}/chat/completions"
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


# Register the new LLM backend
LLM.register("openai_configurable", OpenAILLM)