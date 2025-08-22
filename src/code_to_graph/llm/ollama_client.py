"""OLLAMA client for LLM integration."""

import json
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from loguru import logger


class OllamaResponse(BaseModel):
    """Response model for OLLAMA API."""
    
    model: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaClient:
    """Client for interacting with OLLAMA hosted LLMs."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3:1.7b",
        timeout: int = 300,  # Increased to 5 minutes for large models
    ):
        """Initialize OLLAMA client.
        
        Args:
            base_url: OLLAMA server base URL
            model: Model name (default: qwen3:1.7b)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        logger.info(f"Initialized OLLAMA client: {base_url}, model: {model}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> OllamaResponse:
        """Generate text using OLLAMA API.
        
        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            OllamaResponse object
            
        Raises:
            httpx.RequestError: If request fails
            ValueError: If response is invalid
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                if stream:
                    # Handle streaming response
                    full_response = ""
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            full_response += chunk.get("response", "")
                            if chunk.get("done", False):
                                return OllamaResponse(
                                    model=chunk.get("model", self.model),
                                    response=full_response,
                                    done=True,
                                    **{k: v for k, v in chunk.items() 
                                       if k in OllamaResponse.model_fields}
                                )
                else:
                    # Handle non-streaming response
                    data = response.json()
                    return OllamaResponse(**data)
                    
        except httpx.RequestError as e:
            logger.error(f"OLLAMA request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OLLAMA response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"OLLAMA generation failed: {e}")
            raise
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> OllamaResponse:
        """Synchronous version of generate method.
        
        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            OllamaResponse object
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"OLLAMA generation completed: {len(data.get('response', ''))} chars")
            return OllamaResponse(**data)
            
        except httpx.RequestError as e:
            logger.error(f"OLLAMA request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OLLAMA response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"OLLAMA generation failed: {e}")
            raise
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from OLLAMA server.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            logger.info(f"Found {len(models)} OLLAMA models")
            return models
            
        except Exception as e:
            logger.error(f"Failed to list OLLAMA models: {e}")
            return []
    
    def check_health(self) -> bool:
        """Check if OLLAMA server is healthy.
        
        Returns:
            True if server is responding, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
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