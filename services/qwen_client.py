# -*- coding: utf-8 -*-
"""
Qwen LLM Service Client
کلاینت سرویس Qwen LLM
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import time
import json

logger = logging.getLogger(__name__)

QWEN_DEFAULT_MODEL = "/home/user01/.cache/huggingface/hub/models--Qwen--Qwen3.6-35B-A3B"  # Qwen 3.6 35B running on port 8000

# محدودیت کلی مدل (توکن)
_MODEL_MAX_CTX = 131072
# بافر ایمنی: چقدر از پایان context را خالی نگه می‌داریم
_CTX_SAFETY_BUFFER = 512


def _estimate_tokens(text: str) -> int:
    """
    تخمین تعداد توکن یک متن بدون tokenizer.
    برای فارسی/عربی: هر کاراکتر چندبایتی ≈ 1 توکن (BPE subword tokenizer).
    برای انگلیسی: هر ۳ کاراکتر ≈ 1 توکن.
    ضریب محافظه‌کارانه (overestimate) برای جلوگیری از overflow.
    """
    if not text:
        return 0
    persian_arabic_chars = sum(
        1 for c in text
        if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' or '\u08A0' <= c <= '\u08FF'
    )
    other_chars = len(text) - persian_arabic_chars
    # Persian/Arabic: ~1 token per char; other: ~1 token per 3 chars
    estimated = persian_arabic_chars + (other_chars // 3)
    return max(1, estimated)


def _truncate_to_token_limit(text: str, max_tokens: int) -> str:
    """متن را تا محدودیت توکن برش می‌دهد (از ابتدا حذف می‌کند)."""
    if not text or max_tokens <= 0:
        return ""
    if _estimate_tokens(text) <= max_tokens:
        return text
    # تخمین کاراکتر-به-توکن: ~1 کاراکتر فارسی = 1 توکن، ~3 کاراکتر انگلیسی = 1 توکن
    # برای محافظه‌کاری: از ضریب 1 استفاده می‌کنیم (worst case)
    chars_to_keep = max_tokens  # worst case: 1 char per token
    truncated = "...\n" + text[-chars_to_keep:]
    # اگر هنوز بیش از حد باشد، بیشتر برش بزن
    while _estimate_tokens(truncated) > max_tokens and chars_to_keep > 100:
        chars_to_keep = int(chars_to_keep * 0.85)
        truncated = "...\n" + text[-chars_to_keep:]
    return truncated


def _safe_max_tokens(system_prompt: Optional[str], prompt: str, requested: int) -> int:
    """
    max_tokens را به اندازه‌ای کلیپ کن که مجموع input + output از محدودیت مدل رد نشود.
    """
    input_text = (system_prompt or "") + prompt
    estimated_input = _estimate_tokens(input_text)
    available = _MODEL_MAX_CTX - estimated_input - _CTX_SAFETY_BUFFER
    safe = min(requested, max(64, available))
    if safe < requested:
        logger.warning(
            f"⚠️ [QwenClient] max_tokens capped: {requested} → {safe} "
            f"(estimated input={estimated_input} tokens)"
        )
    return safe


def _truncate_prompt_if_needed(system_prompt: Optional[str], prompt: str, max_output: int = 1024) -> str:
    """
    اگر prompt خیلی بزرگ باشد، آن را برش می‌دهد تا خطای context overflow رخ ندهد.
    Returns the (possibly truncated) prompt.
    """
    sys_tokens = _estimate_tokens(system_prompt or "")
    prompt_tokens = _estimate_tokens(prompt)
    total = sys_tokens + prompt_tokens + max_output + _CTX_SAFETY_BUFFER
    if total <= _MODEL_MAX_CTX:
        return prompt
    # چقدر می‌توانیم prompt داشته باشیم
    allowed_prompt_tokens = _MODEL_MAX_CTX - sys_tokens - max_output - _CTX_SAFETY_BUFFER
    if allowed_prompt_tokens < 100:
        allowed_prompt_tokens = 100
    truncated = _truncate_to_token_limit(prompt, allowed_prompt_tokens)
    logger.warning(
        f"⚠️ [QwenClient] Prompt truncated: {prompt_tokens} → {_estimate_tokens(truncated)} tokens "
        f"(sys={sys_tokens}, max_out={max_output})"
    )
    return truncated


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
    tool_calls: Optional[List[Dict[str, Any]]] = None


class QwenClient:
    """کلاینت Qwen LLM Service"""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 api_key: str = "qwen-dev-2024-abc123def456",
                 timeout: int = 90,   # کاهش از 120 به 90 - جلوگیری از قفل شدن semaphore
                 max_retries: int = 2):  # کاهش از 3 به 2 - سریع‌تر fail شدن
        # Load settings if base_url not provided
        if base_url is None:
            try:
                from config.settings import ServiceConfig
                config = ServiceConfig()
                base_url = config.qwen_url
                logger.info(f"📍 QwenClient using URL from settings: {base_url}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load settings, using default: {e}")
                base_url = "http://localhost:8000"  # Qwen 3.6 35B default port
        
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.model_name = QWEN_DEFAULT_MODEL
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock: Optional[asyncio.Lock] = None  # Lazy initialize
        self._session_event_loop = None  # Track which event loop owns the session
        
        # Rate limiting
        self.rate_limit_delay = 0.2  # 200ms between requests
        self.last_request_time = 0
        
        logger.info(f"QwenClient initialized: {self.base_url}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """اطمینان از وجود session با thread-safety و event loop tracking"""
        # دریافت event loop فعلی
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("No running event loop!")
            return
        
        # Lazy initialize lock در event loop فعلی
        if self._session_lock is None:
            self._session_lock = asyncio.Lock()
        
        # بررسی: آیا event loop تغییر کرده؟
        if self._session_event_loop is not None and self._session_event_loop != current_loop:
            logger.warning(f"⚠️ Event loop changed! Closing old session and creating new one")
            # بستن session قدیمی
            if self.session and not self.session.closed:
                try:
                    await self.session.close()
                except Exception as e:
                    logger.error(f"Error closing old session: {e}")
            self.session = None
            self._session_lock = asyncio.Lock()  # Lock جدید برای event loop جدید
        
        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    timeout = aiohttp.ClientTimeout(
                        total=self.timeout,
                        connect=30,
                        sock_read=self.timeout
                    )
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "Enhanced-RAG-System/1.0",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    connector = aiohttp.TCPConnector(
                        limit=100,
                        limit_per_host=30,
                        ttl_dns_cache=300,
                        keepalive_timeout=60,  # Keep connections alive for 60s
                        force_close=False,  # Reuse connections
                        enable_cleanup_closed=True  # Clean up closed connections
                    )
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        headers=headers,
                        connector=connector
                    )
                    self._session_event_loop = current_loop  # Track event loop
                    logger.info(f"✅ aiohttp session created in event loop {id(current_loop)}")
    
    async def close(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self._session_event_loop = None  # Reset event loop tracking
    
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

        # برش prompt در صورت نیاز
        prompt = _truncate_prompt_if_needed(system_prompt, prompt, max_output=max_tokens)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # کلیپ کردن max_tokens برای جلوگیری از خطای context overflow
        safe_tokens = _safe_max_tokens(system_prompt, prompt, max_tokens)

        # Prepare request
        request_data = {
            "model": QWEN_DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": safe_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False}
        }
        
        # Retry logic
        last_error = None
        response = None
        
        # ========== DISABLED: Pre-request health check (causes 10s delay) ==========
        # بررسی سلامت قبل از request باعث کندی می‌شود (10s timeout)
        # بهتر است که مستقیماً request کنیم و اگر fail شد، fallback کنیم
        # 
        # try:
        #     is_available = await self.is_available()
        #     if not is_available:
        #         logger.warning("⚠️ vLLM service unavailable (health check failed), skipping request")
        #         return GenerationResponse(
        #             text="",
        #             usage={},
        #             success=False,
        #             error="vLLM service unavailable: Health check failed"
        #         )
        # except Exception as health_error:
        #     logger.debug(f"Health check exception (continuing): {health_error}")
        # ============================================================================
        
        try:
            for attempt in range(self.max_retries):
                try:
                    await self._ensure_session()
                    # Use session.post without async with to avoid context manager issues
                    response = await self.session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=request_data
                    )
                    
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
                
                except (aiohttp.ClientError, ConnectionError, OSError, BrokenPipeError) as e:
                    error_type = type(e).__name__
                    error_msg = f"vLLM connection failed ({error_type}): {str(e)}"
                    logger.warning(f"⚠️ {error_msg}")
                    last_error = f"vLLM service unavailable: {error_type}"
                    # اگر اولین تلاش است، session را reset کن و retry کن
                    if attempt == 0:
                        logger.info("🔄 Resetting aiohttp session after connection error, retrying...")
                        try:
                            await self.close()
                        except Exception:
                            pass
                        await asyncio.sleep(1)
                        continue
                    # بعد از retry هم خطا → برگشت مستقیم
                    return GenerationResponse(
                        text="",
                        usage={},
                        success=False,
                        error=last_error
                    )
                except Exception as e:
                    error_msg = f"Request failed: {str(e)}"
                    logger.error(error_msg)
                    last_error = error_msg
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                finally:
                    # Always release response if it exists
                    if response is not None:
                        await response.release()
                        response = None
        
        except Exception as e:
            logger.error(f"Unexpected error in generate_text: {e}")
            return GenerationResponse(
                text="",
                usage={},
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
        
        # All retries failed
        return GenerationResponse(
            text="",
            usage={},
            success=False,
            error=last_error or "All retries failed"
        )
    
    async def generate_response(self, 
                               prompt: str,
                               system_prompt: Optional[str] = None,
                               max_tokens: int = 1024,
                               temperature: float = 0.7,
                               top_p: float = 0.9,
                               response_model: Any = None) -> GenerationResponse:
        """
        تولید پاسخ با پشتیبانی از Pydantic models
        اگر response_model داده شود، پاسخ را parse می‌کند
        """
        # Generate text normally
        result = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )
        
        # If response_model is provided, try to parse the response
        if response_model and result.success:
            try:
                import json
                from pydantic import ValidationError
                
                # Try to parse JSON from response
                text = result.text.strip()
                
                # Remove markdown code blocks if present
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                # Parse JSON
                data = json.loads(text)
                
                # Create Pydantic model instance
                parsed_response = response_model(**data)
                
                # Add parsed response to result
                result.parsed_response = parsed_response
                
            except (json.JSONDecodeError, ValidationError, Exception) as e:
                logger.warning(f"Failed to parse response as {response_model}: {e}")
                # Return default instance if parsing fails
                try:
                    result.parsed_response = response_model()
                except:
                    result.parsed_response = None
        
        return result
    
    async def generate_stream(self, 
                             prompt: str,
                             system_prompt: Optional[str] = None,
                             max_tokens: int = 1024,
                             temperature: float = 0.7,
                             top_p: float = 0.9) -> AsyncGenerator[str, None]:
        """تولید متن به صورت streaming"""
        await self._ensure_session()
        await self._rate_limit()
        
        # برش prompt در صورت نیاز (قبل از همه چیز)
        prompt = _truncate_prompt_if_needed(system_prompt, prompt, max_output=max_tokens)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # کلیپ کردن max_tokens برای جلوگیری از خطای context overflow
        safe_tokens = _safe_max_tokens(system_prompt, prompt, max_tokens)

        # Prepare request
        request_data = {
            "model": QWEN_DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": safe_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False}
        }
        
        # ========== DISABLED: Pre-streaming health check (causes 10s delay) ==========
        # بررسی سلامت قبل از streaming باعث کندی می‌شود (10s timeout)
        # بهتر است که مستقیماً streaming کنیم و اگر fail شد، error yield کنیم
        #
        # try:
        #     is_available = await self.is_available()
        #     if not is_available:
        #         logger.warning("⚠️ vLLM service unavailable (health check failed), skipping streaming")
        #         yield "Error: vLLM service unavailable: Health check failed"
        #         return
        # except Exception as health_error:
        #     logger.debug(f"Health check exception (continuing): {health_error}")
        # ============================================================================
        
        # Retry logic for streaming
        max_retries = self.max_retries
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Ensure session is available
                await self._ensure_session()
                
                # Use async with for proper streaming
                # Per-request timeout: total=90s, sock_read=60s for streaming
                stream_timeout = aiohttp.ClientTimeout(total=self.timeout, connect=10, sock_read=60)
                async with self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=request_data,
                    timeout=stream_timeout
                ) as response:
                    if response.status == 200:
                        try:
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
                                            # Qwen3.6: content = final answer, reasoning = thinking trace
                                            # We only yield content (not reasoning/thinking) to the user
                                            content = delta.get("content") or ""
                                            
                                            if content:
                                                yield content
                                    
                                    except json.JSONDecodeError:
                                        continue
                            # Success - exit retry loop
                            return
                        except (asyncio.CancelledError, GeneratorExit):
                            # کاربر اتصال را قطع کرد - خطا نیست
                            logger.debug("Stream cancelled by client (GeneratorExit/CancelledError)")
                            return
                        except Exception as e:
                            err_msg = str(e)
                            exc_type = type(e).__name__
                            # ClientConnectionError / ClientPayloadError = client disconnected
                            _disconnect_types = (
                                "ClientConnectionError", "ClientPayloadError",
                                "ServerDisconnectedError", "ClientOSError",
                                "ConnectionResetError", "BrokenPipeError",
                            )
                            is_disconnect = (
                                not err_msg or
                                exc_type in _disconnect_types or
                                "disconnect" in err_msg.lower() or
                                "broken pipe" in err_msg.lower() or
                                "connection reset" in err_msg.lower()
                            )
                            if is_disconnect:
                                logger.debug(f"Stream ended by client disconnect ({exc_type})")
                                return
                            logger.error(f"Error processing stream [{exc_type}]: {e}")
                            yield f"Error: {e}"
                            return
                    else:
                        error_text = await response.text()
                        logger.error(f"Streaming request failed: HTTP {response.status}: {error_text}")
                    
                        if response.status == 503 or response.status >= 500:
                            # Server error - retry
                            last_error = f"HTTP {response.status}"
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                logger.warning(f"⚠️ vLLM returned {response.status}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        yield f"Error: HTTP {response.status}"
                        return
            
            except asyncio.TimeoutError:
                last_error = "Request timeout"
                logger.warning(f"⚠️ Streaming timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except (aiohttp.ClientError, ConnectionError, OSError) as e:
                # Connection errors - try to reconnect
                error_type = type(e).__name__
                last_error = f"{error_type}: {str(e)}"
                logger.warning(f"⚠️ vLLM connection failed: {last_error} (attempt {attempt + 1}/{max_retries})")
                
                # Force session recreation on next attempt
                if self.session is not None:
                    try:
                        await self.session.close()
                    except:
                        pass
                    self.session = None
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
            
            except Exception as e:
                logger.error(f"Streaming failed: {e}")
                yield f"Error: {str(e)}"
                return
        
        # All retries exhausted
        logger.error(f"❌ Streaming failed after {max_retries} attempts: {last_error}")
        yield f"Error: vLLM service unavailable after {max_retries} retries: {last_error}"
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        enable_thinking: bool = False,
    ) -> GenerationResponse:
        """
        OpenAI-compatible tool/function calling via vLLM (Qwen3.6 optimized).

        Qwen3.6 parameters:
          - temperature=0.7, top_p=0.9, top_k=20, presence_penalty=1.5 (normal mode)
          - enable_thinking=False by default (faster; set True for complex reasoning)

        When the model decides a tool is needed, the response contains
        ``tool_calls`` instead of textual ``content``.  The caller is
        responsible for executing the tool and feeding the result back.

        Falls back gracefully to a ReAct-style prompt if vLLM was not
        started with ``--enable-auto-tool-choice``.
        """
        await self._ensure_session()
        await self._rate_limit()

        request_data: Dict[str, Any] = {
            "model": QWEN_DEFAULT_MODEL,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "max_tokens": max_tokens,
            # Qwen3.6 recommended sampling params
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 20,
            "presence_penalty": 1.5,
            "stream": False,
            # Disable thinking for tool calling (faster + cleaner JSON output)
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        }

        response = None
        last_error = None

        try:
            for attempt in range(self.max_retries):
                try:
                    await self._ensure_session()
                    response = await self.session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=request_data,
                    )

                    if response.status == 200:
                        result = await response.json()
                        choices = result.get("choices", [])
                        if not choices:
                            return GenerationResponse(
                                text="", usage={}, success=False,
                                error="No choices in tool-calling response",
                            )

                        message = choices[0].get("message", {})
                        # Qwen3.6: content is the final answer; reasoning is the thinking trace
                        text = message.get("content") or ""
                        reasoning = message.get("reasoning") or ""
                        if reasoning and not text:
                            # Fallback: if only reasoning came back (no content), use it
                            text = reasoning
                        finish_reason = choices[0].get("finish_reason", "stop")

                        raw_tool_calls = message.get("tool_calls")
                        parsed_tool_calls = None
                        if raw_tool_calls:
                            parsed_tool_calls = []
                            for tc in raw_tool_calls:
                                fn = tc.get("function", {})
                                args_raw = fn.get("arguments", "{}")
                                if isinstance(args_raw, str):
                                    try:
                                        args_parsed = json.loads(args_raw)
                                    except json.JSONDecodeError:
                                        args_parsed = {"_raw": args_raw}
                                else:
                                    args_parsed = args_raw
                                parsed_tool_calls.append({
                                    "id": tc.get("id", ""),
                                    "function": {
                                        "name": fn.get("name", ""),
                                        "arguments": args_parsed,
                                    },
                                })

                        return GenerationResponse(
                            text=text,
                            usage=result.get("usage", {}),
                            success=True,
                            finish_reason=finish_reason,
                            tool_calls=parsed_tool_calls,
                        )

                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited (tools), waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 400:
                        error_text = await response.text()
                        # vLLM without --enable-auto-tool-choice: fallback to ReAct-style prompt
                        if "tool-call-parser" in error_text or "auto-tool-choice" in error_text or "tool_choice" in error_text.lower():
                            logger.warning(f"[generate_with_tools] vLLM tool calling not enabled, using ReAct fallback")
                            return await self._generate_with_tools_react_fallback(
                                messages=messages, tools=tools,
                                max_tokens=max_tokens, temperature=temperature
                            )
                        error_msg = f"HTTP 400: {error_text}"
                        logger.error(f"[generate_with_tools] {error_msg}")
                        return GenerationResponse(text="", usage={}, success=False, error=error_msg)
                    else:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"
                        logger.error(f"[generate_with_tools] {error_msg}")
                        last_error = error_msg
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return GenerationResponse(
                            text="", usage={}, success=False, error=error_msg,
                        )

                except asyncio.TimeoutError:
                    last_error = f"Request timeout after {self.timeout}s"
                    logger.error(f"[generate_with_tools] {last_error}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                except (aiohttp.ClientError, ConnectionError, OSError) as e:
                    last_error = f"vLLM connection failed: {type(e).__name__}"
                    logger.warning(f"[generate_with_tools] {last_error}")
                    if attempt == 0:
                        try:
                            await self.close()
                        except Exception:
                            pass
                        await asyncio.sleep(1)
                        continue
                    return GenerationResponse(
                        text="", usage={}, success=False, error=last_error,
                    )

                except Exception as e:
                    last_error = f"Request failed: {e}"
                    logger.error(f"[generate_with_tools] {last_error}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                finally:
                    if response is not None:
                        await response.release()
                        response = None

        except Exception as e:
            logger.error(f"[generate_with_tools] Unexpected error: {e}")
            return GenerationResponse(
                text="", usage={}, success=False,
                error=f"Unexpected error: {e}",
            )

        return GenerationResponse(
            text="", usage={}, success=False,
            error=last_error or "All retries failed",
        )

    async def _generate_with_tools_react_fallback(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> "GenerationResponse":
        """
        Fallback for vLLM servers without --enable-auto-tool-choice.

        Two modes:
        - No tool results yet  → ask the model to output a JSON tool call
        - Tool results present → ask the model to generate a final answer in Persian
        """
        import re as _re

        # Check if conversation already contains tool results
        has_tool_results = any(m.get("role") == "tool" for m in messages)

        # Find the last user message
        user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                break

        if has_tool_results:
            # ── Mode 2: tool results exist → generate final answer ──
            # Build a concise summary of the conversation for the model
            conversation_parts = []
            for m in messages[1:]:  # skip system
                role = m.get("role", "")
                content = str(m.get("content", ""))[:2000]
                if role == "user":
                    conversation_parts.append(f"User: {content}")
                elif role == "tool":
                    conversation_parts.append(f"Tool result: {content}")
            conversation_text = "\n".join(conversation_parts)

            final_prompt = (
                f"Based on the following conversation and tool results, "
                f"answer the user's question in Persian (Farsi). "
                f"Be concise and helpful. Use the actual data from the tool results.\n\n"
                f"{conversation_text}\n\n"
                f"Answer in Persian:"
            )
            logger.info("[ReAct-Fallback] Mode 2: generating final answer from tool results")
            resp = await self.generate_text(
                prompt=final_prompt,
                system_prompt="You are a helpful assistant. Answer in Persian using the tool results provided.",
                max_tokens=max_tokens,
                temperature=0.3,
            )
            if not resp.success or not resp.text:
                return GenerationResponse(text="", usage={}, success=False, error="ReAct final-answer LLM failed")
            logger.info(f"[ReAct-Fallback] Final answer: {resp.text[:100]}")
            return GenerationResponse(text=resp.text, usage=resp.usage, success=True, finish_reason="stop")

        # ── Mode 1: no tool results yet → decide which tool to call ──
        tools_desc = ""
        for t in tools:
            fn = t.get("function", t)
            params = fn.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            param_lines = []
            for pname, pinfo in props.items():
                req = "(required)" if pname in required else "(optional)"
                param_lines.append(f"  - {pname} {req}: {pinfo.get('description', '')}")
            param_str = "\n".join(param_lines) if param_lines else "  (no parameters)"
            tools_desc += f"\n### Tool: {fn.get('name', '')}\n{fn.get('description', '')}\nParameters:\n{param_str}\n"

        react_prompt = f"""AVAILABLE TOOLS:
{tools_desc}

TASK: Select the right tool for the user request and output ONLY the JSON tool call.
IMPORTANT: Output ONLY the JSON object, no other text.

User request: "{user_query}"

Output the JSON tool call now:"""

        resp = await self.generate_text(
            prompt=react_prompt,
            system_prompt='You must output ONLY a JSON object like: {"tool_name": "name", "arguments": {"key": "value"}}. Nothing else.',
            max_tokens=150,
            temperature=0.0,
        )

        if not resp.success or not resp.text:
            return GenerationResponse(text="", usage={}, success=False, error="ReAct fallback LLM failed")

        raw = resp.text.strip()
        parsed = None

        # Strategy 1: direct JSON parse of full response
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Strategy 2: extract JSON from within surrounding text
        if not parsed:
            brace_start = raw.find('{')
            if brace_start >= 0:
                depth, end = 0, brace_start
                for i, ch in enumerate(raw[brace_start:], brace_start):
                    if ch == '{': depth += 1
                    elif ch == '}': depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
                try:
                    parsed = json.loads(raw[brace_start:end])
                except json.JSONDecodeError:
                    pass

        if isinstance(parsed, dict) and parsed.get("tool_name"):
            tool_name = parsed["tool_name"]
            arguments = parsed.get("arguments", {})
            logger.info(f"[ReAct-Fallback] Extracted tool call: {tool_name}({arguments})")
            return GenerationResponse(
                text="",
                usage=resp.usage,
                success=True,
                finish_reason="tool_calls",
                tool_calls=[{
                    "id": f"fallback_{tool_name}",
                    "function": {"name": tool_name, "arguments": arguments},
                }],
            )

        logger.info(f"[ReAct-Fallback] No tool call found, returning plain text")
        return GenerationResponse(text=raw, usage=resp.usage, success=True, finish_reason="stop")

    async def health_check(self) -> bool:
        """بررسی سلامت سرویس"""
        try:
            # استفاده از timeout مناسب برای health check (10 ثانیه)
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                try:
                    response = await temp_session.get(f"{self.base_url}/health")
                    try:
                        return response.status == 200
                    finally:
                        await response.release()
                except asyncio.TimeoutError:
                    # Timeout = service not available
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError) as e:
            # Connection errors = service not available
            return False
        except Exception as e:
            # Other errors = assume not available
            return False
    
    async def is_available(self) -> bool:
        """بررسی سریع اینکه آیا سرویس در دسترس است یا نه"""
        return await self.health_check()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """دریافت آمار استفاده"""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "session_active": self.session is not None and not self.session.closed
        }


# Global Qwen client instance
qwen_client = QwenClient()
