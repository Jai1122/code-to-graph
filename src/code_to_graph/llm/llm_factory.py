"""Factory for creating VLLM clients."""

from loguru import logger

from ..core.config import settings
from .vllm_client import VLLMClient


class LLMFactory:
    """Factory for creating VLLM clients."""
    
    @staticmethod
    def create_client() -> VLLMClient:
        """Create a VLLM client based on the current configuration.
        
        Returns:
            Configured VLLM client instance
            
        Raises:
            ValueError: If VLLM is not configured properly
        """
        if settings.llm.provider.lower() != "vllm":
            raise ValueError(
                f"Only VLLM provider is supported. Current provider: {settings.llm.provider}"
            )
        
        logger.info(f"Creating VLLM client with model: {settings.llm.vllm_model}")
        return VLLMClient(
            base_url=settings.llm.vllm_base_url,
            model=settings.llm.vllm_model,
            api_key=settings.llm.vllm_api_key,
            timeout=settings.llm.timeout
        )
    
    @staticmethod
    def get_model_name() -> str:
        """Get the VLLM model name.
        
        Returns:
            VLLM model name string
        """
        return settings.llm.vllm_model
    
    @staticmethod
    def check_health() -> bool:
        """Check if the VLLM provider is healthy.
        
        Returns:
            True if VLLM is healthy, False otherwise
        """
        try:
            client = LLMFactory.create_client()
            health = client.check_health()
            client.close()
            return health
        except Exception as e:
            logger.error(f"VLLM health check failed: {e}")
            return False