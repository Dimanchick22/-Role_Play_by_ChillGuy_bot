"""Bot package."""

__version__ = "1.0.0"
__author__ = "Your Name"

from .character import Character
from .llm_client import LLMClient
from .handlers import BotHandlers

__all__ = ["Character", "LLMClient", "BotHandlers"]