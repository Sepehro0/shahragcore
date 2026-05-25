# -*- coding: utf-8 -*-
"""
OpenRouter LLM Service Client
کلاینت OpenRouter - API سازگار با OpenAI برای دسترسی به صدها مدل.

طراحی:
- رابط (interface) این کلاس دقیقا شبیه `QwenClient` است:
    generate_text / generate_response / generate_stream / health_check
    is_available / close / get_usage_stats
  بنابراین می‌توان آن را به عنوان drop-in replacement استفاده کرد.
- همان dataclass های GenerationRequest/GenerationResponse از qwen_client
  استفاده می‌شود تا تمامی consumer های فعلی بدون تغییر کار کنند.

Reference: https://openrouter.ai/docs/quickstart
Endpoint: POST https://openrouter.ai/api/v1/chat/completions
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp

from services.qwen_client import GenerationRequest, GenerationResponse  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)

_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"


class OpenRouterClient:
    """
    کلاینت OpenRouter با interface سازگار با QwenClient.

    Parameters
    ----------
    api_key : str
        کلید OpenRouter (ضروری). می‌توان از متغیر محیطی OPENROUTER_API_KEY هم خواند.
    model : str
        نام مدل روی OpenRouter (مثال: "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet").
    base_url : str
        پایه URL (پیش‌فرض: https://openrouter.ai/api/v1).
    site_url, app_name : Optional[str]
        هدرهای اختیاری HTTP-Referer و X-Title برای لیدربرد OpenRouter.
    extra_body : Optional[dict]
        پارامترهای اضافی که به بدنه هر درخواست اضافه می‌شود (مثلا provider routing).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_OPENROUTER_MODEL,
        base_url: str = _DEFAULT_OPENROUTER_BASE_URL,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3,
        extra_body: Optional[Dict[str, Any]] = None,
        rate_limit_delay: float = 0.1,
    ):
        if not api_key:
            # Fail fast with a clear error; the factory/router is responsible for
            # falling back to the local provider if the key is missing.
            raise ValueError(
                "OpenRouterClient requires an api_key. "
                "Set OPENROUTER_API_KEY env var or pass it explicitly."
            )

        self.api_key = api_key
        self.model = model
        # Store model under `model_name` too, mirroring QwenClient's public API.
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_body = dict(extra_body) if extra_body else {}

        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock: Optional[asyncio.Lock] = None
        self._session_event_loop = None

        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0

        logger.info(
            f"OpenRouterClient initialized (model={self.model}, base_url={self.base_url})"
        )

    # ------------------------------------------------------------------
    # Session / lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _default_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Enhanced-RAG-System/1.0 (OpenRouterClient)",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    async def _ensure_session(self):
        """اطمینان از وجود aiohttp session - event-loop aware."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("OpenRouterClient: no running event loop")
            return

        if self._session_lock is None:
            self._session_lock = asyncio.Lock()

        if self._session_event_loop is not None and self._session_event_loop != current_loop:
            logger.warning("⚠️ OpenRouter: event loop changed, recreating session")
            if self.session and not self.session.closed:
                try:
                    await self.session.close()
                except Exception as e:
                    logger.error(f"Error closing old OpenRouter session: {e}")
            self.session = None
            self._session_lock = asyncio.Lock()

        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    timeout = aiohttp.ClientTimeout(
                        total=self.timeout,
                        connect=30,
                        sock_read=self.timeout,
                    )
                    connector = aiohttp.TCPConnector(
                        limit=50,
                        limit_per_host=20,
                        ttl_dns_cache=300,
                        keepalive_timeout=60,
                        force_close=False,
                        enable_cleanup_closed=True,
                    )
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        headers=self._default_headers(),
                        connector=connector,
                    )
                    self._session_event_loop = current_loop
                    logger.info(f"✅ OpenRouter aiohttp session created (loop={id(current_loop)})")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self._session_event_loop = None

    async def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        top_p: float,
        stream: bool,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }

        # Merge in configured extras (e.g., provider routing preferences)
        if self.extra_body:
            for k, v in self.extra_body.items():
                payload.setdefault(k, v)

        # Per-call overrides
        if extra:
            payload.update(extra)

        return payload

    # ------------------------------------------------------------------
    # Public API: generate_text
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> GenerationResponse:
        """تولید متن غیر-streaming از طریق OpenRouter."""
        await self._ensure_session()
        await self._rate_limit()

        payload = self._build_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=False,
        )

        last_error: Optional[str] = None
        response = None

        try:
            for attempt in range(self.max_retries):
                try:
                    await self._ensure_session()
                    response = await self.session.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                    )

                    if response.status == 200:
                        result = await response.json()
                        choices = result.get("choices", [])
                        if not choices:
                            return GenerationResponse(
                                text="",
                                usage={},
                                success=False,
                                error="No choices in OpenRouter response",
                            )
                        choice = choices[0]
                        text = (choice.get("message") or {}).get("content", "") or ""
                        finish_reason = choice.get("finish_reason", "stop")
                        return GenerationResponse(
                            text=text,
                            usage=result.get("usage", {}) or {},
                            success=True,
                            finish_reason=finish_reason,
                        )

                    if response.status == 429:
                        wait = 2 ** attempt
                        logger.warning(
                            f"OpenRouter rate-limited (429), retry in {wait}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(wait)
                        continue

                    error_text = await response.text()
                    last_error = f"HTTP {response.status}: {error_text}"
                    logger.error(f"OpenRouter error: {last_error}")
                    # Retry on 5xx
                    if 500 <= response.status < 600 and attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return GenerationResponse(
                        text="", usage={}, success=False, error=last_error
                    )

                except asyncio.TimeoutError:
                    last_error = f"OpenRouter request timeout after {self.timeout}s"
                    logger.error(last_error)
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                except (aiohttp.ClientError, ConnectionError, OSError, BrokenPipeError) as e:
                    err_type = type(e).__name__
                    last_error = f"OpenRouter connection failed ({err_type}): {e}"
                    logger.warning(f"⚠️ {last_error}")
                    if attempt == 0:
                        try:
                            await self.close()
                        except Exception:
                            pass
                        await asyncio.sleep(1)
                        continue
                    return GenerationResponse(
                        text="", usage={}, success=False, error=last_error
                    )

                except Exception as e:
                    last_error = f"OpenRouter unexpected error: {e}"
                    logger.error(last_error)
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue

                finally:
                    if response is not None:
                        try:
                            await response.release()
                        except Exception:
                            pass
                        response = None

        except Exception as e:
            logger.error(f"OpenRouter generate_text fatal: {e}")
            return GenerationResponse(
                text="", usage={}, success=False, error=f"Unexpected error: {e}"
            )

        return GenerationResponse(
            text="", usage={}, success=False, error=last_error or "All retries failed"
        )

    # ------------------------------------------------------------------
    # Public API: generate_response (with optional Pydantic parsing)
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        response_model: Any = None,
    ) -> GenerationResponse:
        """نسخه extended که اگر response_model بدهید، پاسخ را به Pydantic parse می‌کند."""
        result = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        if response_model and result.success:
            try:
                from pydantic import ValidationError  # type: ignore

                text = (result.text or "").strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

                data = json.loads(text)
                parsed = response_model(**data)
                # Attach parsed result like qwen_client does
                result.parsed_response = parsed  # type: ignore[attr-defined]
            except (json.JSONDecodeError, Exception) as e:  # noqa: BLE001
                logger.warning(f"OpenRouter: failed to parse response as {response_model}: {e}")
                try:
                    result.parsed_response = response_model()  # type: ignore[attr-defined]
                except Exception:
                    result.parsed_response = None  # type: ignore[attr-defined]

        return result

    # ------------------------------------------------------------------
    # Public API: streaming
    # ------------------------------------------------------------------

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """تولید streaming از طریق SSE سازگار با OpenAI."""
        await self._ensure_session()
        await self._rate_limit()

        payload = self._build_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
        )

        max_retries = self.max_retries
        last_error: Optional[str] = None

        for attempt in range(max_retries):
            try:
                await self._ensure_session()
                stream_timeout = aiohttp.ClientTimeout(
                    total=self.timeout, connect=15, sock_read=90
                )
                async with self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=stream_timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"OpenRouter stream failed: HTTP {response.status}: {error_text}"
                        )
                        if response.status >= 500 and attempt < max_retries - 1:
                            last_error = f"HTTP {response.status}"
                            await asyncio.sleep(2 ** attempt)
                            continue
                        yield f"Error: HTTP {response.status}"
                        return

                    try:
                        async for raw_line in response.content:
                            line = raw_line.decode("utf-8", errors="ignore").strip()
                            if not line:
                                continue
                            # OpenRouter keeps SSE comments starting with ":" (heartbeats) - skip them
                            if line.startswith(":"):
                                continue
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].lstrip()
                            if data == "[DONE]":
                                return
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content") or ""
                            if content:
                                yield content
                        return
                    except (asyncio.CancelledError, GeneratorExit):
                        logger.debug("OpenRouter stream cancelled by client")
                        return
                    except Exception as e:
                        exc_type = type(e).__name__
                        _disconnect_types = (
                            "ClientConnectionError", "ClientPayloadError",
                            "ServerDisconnectedError", "ClientOSError",
                            "ConnectionResetError", "BrokenPipeError",
                        )
                        msg = str(e) or ""
                        is_disconnect = (
                            not msg
                            or exc_type in _disconnect_types
                            or "disconnect" in msg.lower()
                            or "broken pipe" in msg.lower()
                            or "connection reset" in msg.lower()
                        )
                        if is_disconnect:
                            logger.debug(f"OpenRouter stream ended (client disconnect: {exc_type})")
                            return
                        logger.error(f"OpenRouter stream processing error [{exc_type}]: {e}")
                        yield f"Error: {e}"
                        return

            except asyncio.TimeoutError:
                last_error = "OpenRouter stream timeout"
                logger.warning(f"⚠️ {last_error} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

            except (aiohttp.ClientError, ConnectionError, OSError) as e:
                err_type = type(e).__name__
                last_error = f"{err_type}: {e}"
                logger.warning(
                    f"⚠️ OpenRouter stream connection failed: {last_error} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                if self.session is not None:
                    try:
                        await self.session.close()
                    except Exception:
                        pass
                    self.session = None
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

            except Exception as e:
                logger.error(f"OpenRouter stream unexpected error: {e}")
                yield f"Error: {e}"
                return

        logger.error(f"❌ OpenRouter stream failed after {max_retries} attempts: {last_error}")
        yield f"Error: OpenRouter unavailable after {max_retries} retries: {last_error}"

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        بررسی سلامت با یک درخواست سبک GET /models.
        نیاز به API key معتبر دارد؛ در نبود کلید، False برمی‌گرداند.
        """
        if not self.api_key:
            return False
        try:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with aiohttp.ClientSession(
                timeout=timeout, headers=self._default_headers()
            ) as temp_session:
                resp = await temp_session.get(f"{self.base_url}/models")
                try:
                    return resp.status == 200
                finally:
                    await resp.release()
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, OSError):
            return False
        except Exception:
            return False

    async def is_available(self) -> bool:
        return await self.health_check()

    def get_usage_stats(self) -> Dict[str, Any]:
        return {
            "provider": "openrouter",
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "session_active": self.session is not None and not self.session.closed,
        }
