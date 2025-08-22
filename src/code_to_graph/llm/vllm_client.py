"""VLLM client for remote LLM integration."""

import json
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from loguru import logger


class VLLMResponse(BaseModel):
    """Response model for VLLM API."""
    
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class VLLMClient:
    """Client for interacting with VLLM hosted LLMs."""
    
    def __init__(
        self,
        base_url: str = "https://vllm.com",
        model: str = "/app/models/qwen3:14b",
        api_key: Optional[str] = None,
        timeout: int = 300,  # Increased to 5 minutes for large models
    ):
        """Initialize VLLM client.
        
        Args:
            base_url: VLLM server base URL
            model: Model name (default: /app/models/qwen3:14b)
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
        # Set up headers for authentication
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.Client(timeout=timeout, headers=self.headers)
        logger.info(f"Initialized VLLM client: {base_url}, model: {model}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> VLLMResponse:
        """Generate text using VLLM API.
        
        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            VLLMResponse object
            
        Raises:
            httpx.RequestError: If request fails
            ValueError: If response is invalid
        """
        # Combine system prompt and user prompt if system prompt is provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = 2048  # Default max tokens
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.post(
                    f"{self.base_url}/v1/completions",
                    json=payload
                )
                response.raise_for_status()
                
                if stream:
                    # Handle streaming response
                    full_response = ""
                    response_id = None
                    created = None
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                if not response_id:
                                    response_id = chunk.get("id")
                                    created = chunk.get("created")
                                
                                choices = chunk.get("choices", [])
                                if choices and "text" in choices[0]:
                                    full_response += choices[0]["text"]
                            except json.JSONDecodeError:
                                continue
                    
                    return VLLMResponse(
                        id=response_id or "generated",
                        created=created or 0,
                        model=self.model,
                        choices=[{"text": full_response, "index": 0, "finish_reason": "stop"}]
                    )
                else:
                    # Handle non-streaming response
                    data = response.json()
                    return VLLMResponse(**data)
                    
        except httpx.RequestError as e:
            logger.error(f"VLLM request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse VLLM response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"VLLM generation failed: {e}")
            raise
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> VLLMResponse:
        """Synchronous version of generate method.
        
        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            VLLMResponse object
        """
        # Combine system prompt and user prompt if system prompt is provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "stream": False,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = 2048  # Default max tokens
        
        try:
            response = self.client.post(
                f"{self.base_url}/v1/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"VLLM generation completed: {self.model}")
            return VLLMResponse(**data)
            
        except httpx.RequestError as e:
            logger.error(f"VLLM request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse VLLM response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"VLLM generation failed: {e}")
            raise
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from VLLM server.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json()
            models = data.get("data", [])
            logger.info(f"Found {len(models)} VLLM models")
            return models
            
        except Exception as e:
            logger.error(f"Failed to list VLLM models: {e}")
            return []
    
    def check_health(self) -> bool:
        """Check if VLLM server is healthy.
        
        Returns:
            True if server is responding, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                return True
            # Try alternate health endpoint
            response = self.client.get(f"{self.base_url}/v1/models")
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()