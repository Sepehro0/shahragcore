# -*- coding: utf-8 -*-
"""
Core modules for RAG system
All imports are lazy to avoid circular dependencies and missing modules.
"""

__all__ = [
    'DomainPromptGenerator',
    'ComponentInitializer',
    'ChatManager',
]


def __getattr__(name):
    """Lazy import for core modules"""
    if name == 'DomainPromptGenerator':
        from .domain_prompt_generator import DomainPromptGenerator
        return DomainPromptGenerator
    elif name == 'ComponentInitializer':
        from .initialization import ComponentInitializer
        return ComponentInitializer
    elif name == 'ChatManager':
        from .chat_manager import ChatManager
        return ChatManager
    elif name == 'RefactoredRAGSystem':
        from .refactored_rag_system import RefactoredRAGSystem
        return RefactoredRAGSystem
    elif name == 'AnswerGenerator':
        try:
            from .answer_generator import AnswerGenerator
            return AnswerGenerator
        except ImportError:
            return None
    raise AttributeError(f"module 'core' has no attribute {name!r}")
