# handlers/__init__.py
"""Пакет обработчиков - исправленная версия."""

from .command_handlers import CommandHandlers
from .message_handlers import MessageHandlers
from .base_handler import ImprovedBaseHandler

__all__ = ["CommandHandlers", "MessageHandlers", "ImprovedBaseHandler"]