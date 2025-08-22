"""Factory for creating LLM clients based on configuration."""

from typing import Union
from loguru import logger

from ..core.config import settings
from .ollama_client import OllamaClient
from .vllm_client import VLLMClient


class LLMFactory:
    """Factory for creating appropriate LLM clients based on configuration."""
    
    @staticmethod
    def create_client() -> Union[OllamaClient, VLLMClient]:
        """Create an LLM client based on the current configuration.
        
        Returns:
            Configured LLM client instance
            
        Raises:
            ValueError: If the provider is unsupported
        """
        provider = settings.llm.provider.lower()
        
        if provider == "ollama":
            logger.info(f"Creating OLLAMA client with model: {settings.llm.ollama_model}")
            return OllamaClient(
                base_url=settings.llm.ollama_base_url,
                model=settings.llm.ollama_model,
                timeout=settings.llm.timeout
            )
        elif provider == "vllm":
            logger.info(f"Creating VLLM client with model: {settings.llm.vllm_model}")
            return VLLMClient(
                base_url=settings.llm.vllm_base_url,
                model=settings.llm.vllm_model,
                api_key=settings.llm.vllm_api_key,
                timeout=settings.llm.timeout
            )
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: ollama, vllm"
            )
    
    @staticmethod
    def get_model_name() -> str:
        """Get the model name for the current provider.
        
        Returns:
            Model name string
        """
        provider = settings.llm.provider.lower()
        
        if provider == "ollama":
            return settings.llm.ollama_model
        elif provider == "vllm":
            return settings.llm.vllm_model
        else:
            return "unknown"
    
    @staticmethod
    def check_health() -> bool:
        """Check if the configured LLM provider is healthy.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            client = LLMFactory.create_client()
            health = client.check_health()
            client.close()
            return health
        except Exception as e:
            logger.error(f"Health check failed for {settings.llm.provider}: {e}")
            return False