# handlers/__init__.py
"""Пакет обработчиков."""

from .command_handlers import CommandHandlers
from .message_handlers import MessageHandlers

__all__ = ["CommandHandlers", "MessageHandlers"]