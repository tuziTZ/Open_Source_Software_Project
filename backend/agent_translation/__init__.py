"""Translation agent module - translates articles via LLM providers.

Exports:
- TranslationService: Application service for translation
- TranslationAgent: Low-level translation logic
- router: HTTP router with POST /agents/translation endpoint
"""

from .agent import TranslationAgent
from .router import router
from .service import TranslationService

__all__ = [
    "TranslationAgent",
    "TranslationService",
    "router",
]
