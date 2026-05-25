# -*- coding: utf-8 -*-
"""
DeepSeek LLM Service Client
کلاینت سرویس DeepSeek LLM
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import time
import json

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """درخواست تولید متن"""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False


@dataclass
class GenerationResponse:
    """پاسخ تولید متن"""
    text: str
    usage: Dict[str, int]
    success: bool
    error: Optional[str] = None
    finish_reason: Optional[str] = None


class DeepSeekClient:
    """کلاینت DeepSeek LLM Service"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8008",
                 timeout: int = 60,
                 max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_delay = 0.2  # 200ms between requests
        self.last_request_time = 0
        
        logger.info(f"DeepSeekClient initialized: {self.base_url}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """اطمینان از وجود session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Enhanced-RAG-System/1.0"
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def close(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _rate_limit(self):
        """Rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def generate_text(self, 
                           prompt: str,
                           system_prompt: Optional[str] = None,
                           max_tokens: int = 1024,
                           temperature: float = 0.7,
                           top_p: float = 0.9) -> GenerationResponse:
        """تولید متن"""
        await self._ensure_session()
        await self._rate_limit()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        request_data = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=request_data
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract response
                        choices = result.get("choices", [])
                        if choices:
                            choice = choices[0]
                            text = choice.get("message", {}).get("content", "")
                            finish_reason = choice.get("finish_reason", "stop")
                            
                            return GenerationResponse(
                                text=text,
                                usage=result.get("usage", {}),
                                success=True,
                                finish_reason=finish_reason
                            )
                        else:
                            return GenerationResponse(
                                text="",
                                usage={},
                                success=False,
                                error="No choices in response"
                            )
                    
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"
                        logger.error(error_msg)
                        last_error = error_msg
                        
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        
                        return GenerationResponse(
                            text="",
                            usage={},
                            success=False,
                            error=error_msg
                        )
            
            except asyncio.TimeoutError:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.error(error_msg)
                last_error = error_msg
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except Exception as e:
                error_msg = f"Request failed: {str(e)}"
                logger.error(error_msg)
                last_error = error_msg
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        # All retries failed
        return GenerationResponse(
            text="",
            usage={},
            success=False,
            error=last_error or "All retries failed"
        )
    
    async def generate_stream(self, 
                             prompt: str,
                             system_prompt: Optional[str] = None,
                             max_tokens: int = 1024,
                             temperature: float = 0.7,
                             top_p: float = 0.9) -> AsyncGenerator[str, None]:
        """تولید متن به صورت streaming"""
        await self._ensure_session()
        await self._rate_limit()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        request_data = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data
            ) as response:
                
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            
                            if data == '[DONE]':
                                break
                            
                            try:
                                chunk_data = json.loads(data)
                                choices = chunk_data.get("choices", [])
                                
                                if choices:
                                    choice = choices[0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")
                                    
                                    if content:
                                        yield content
                                
                            except json.JSONDecodeError:
                                continue
                else:
                    error_text = await response.text()
                    logger.error(f"Streaming request failed: HTTP {response.status}: {error_text}")
                    yield f"Error: HTTP {response.status}"
        
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    async def health_check(self) -> bool:
        """بررسی سلامت سرویس"""
        try:
            await self._ensure_session()
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "session_active": self.session is not None and not self.session.closed
        }


# Global DeepSeek client instance
deepseek_client = DeepSeekClient()
