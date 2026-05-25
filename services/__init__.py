# -*- coding: utf-8 -*-
"""
External Service Clients
کلاینت‌های سرویس‌های خارجی
"""

from .jina_client import JinaClient
from .qwen_client import QwenClient
from .deepseek_client import DeepSeekClient
from .reranker_client import RerankerClient
from .openrouter_client import OpenRouterClient
from .llm_provider import (
    LLMProvider,
    PROVIDER_LOCAL,
    PROVIDER_OPENROUTER,
    build_llm_provider_from_settings,
)
from .collection_llm_manager import (
    CollectionLLMManager,
    CollectionLLMOverride,
)
from .collection_aware_llm_provider import CollectionAwareLLMProvider

__all__ = [
    "JinaClient",
    "QwenClient",
    "DeepSeekClient",
    "RerankerClient",
    "OpenRouterClient",
    "LLMProvider",
    "PROVIDER_LOCAL",
    "PROVIDER_OPENROUTER",
    "build_llm_provider_from_settings",
    "CollectionLLMManager",
    "CollectionLLMOverride",
    "CollectionAwareLLMProvider",
]
