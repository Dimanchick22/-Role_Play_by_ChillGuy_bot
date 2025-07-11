# handlers/base_handler.py
"""Базовый обработчик."""

from abc import ABC
from typing import Any
from telegram import Update
from telegram.ext import ContextTypes
import logging

from core.registry import registry

logger = logging.getLogger(__name__)

class BaseHandler:
    """Базовый класс обработчика (не абстрактный)."""
    
    def __init__(self):
        self.registry = registry
    
    def get_service(self, name: str) -> Any:
        """Получает сервис из реестра."""
        try:
            return self.registry.get(name)
        except Exception as e:
            logger.warning(f"Сервис {name} недоступен: {e}")
            return None
    
    async def log_interaction(self, update: Update, action: str, **kwargs):
        """Логирует взаимодействие."""
        user = update.effective_user
        logger.info(
            f"User {user.id} ({user.first_name}): {action}",
            extra={
                "user_id": user.id,
                "action": action,
                **kwargs
            }
        )