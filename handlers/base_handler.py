"""Базовый обработчик с общими методами."""

from typing import Any
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import logging

from core.registry import registry
from models.base import User

logger = logging.getLogger(__name__)

class BaseHandler:
    """Базовый класс обработчика с общими методами."""
    
    def __init__(self):
        self.registry = registry
    
    def get_service(self, name: str) -> Any:
        """Получает сервис из реестра."""
        try:
            return self.registry.get(name)
        except Exception as e:
            logger.warning(f"Сервис {name} недоступен: {e}")
            return None
    
    def get_user_from_update(self, update: Update) -> User:
        """Создает объект User из Update - общий метод для всех обработчиков."""
        tg_user = update.effective_user
        
        return User(
            id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
            created_at=datetime.now(),
            last_seen=datetime.now(),
            is_premium=getattr(tg_user, 'is_premium', False)
        )
    
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
    
    async def send_typing_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет действие 'печатает'."""
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить typing action: {e}")
    
    def get_template_response_fallback(self, message: str, user_name: str = "") -> str:
        """Fallback шаблонные ответы если персонаж недоступен."""
        import random
        
        message_lower = message.lower()
        
        # Простые шаблоны
        if any(word in message_lower for word in ["привет", "хай", "hello"]):
            responses = [
                f"Привет{f', {user_name}' if user_name else ''}! 😊",
                f"Хеллоу{f', {user_name}' if user_name else ''}! 👋"
            ]
        elif any(word in message_lower for word in ["пока", "до свидания", "бай"]):
            responses = [
                "Пока! 👋 Хорошего дня!",
                "До встречи! 😊"
            ]
        elif any(word in message_lower for word in ["спасибо", "благодарю"]):
            responses = [
                "Пожалуйста! 😊",
                "Не за что! 💫"
            ]
        else:
            responses = [
                "Интересно! 😊 Расскажи больше!",
                "Классно! ✨ А что еще?",
                "Супер! 🎉 Я слушаю!"
            ]
        
        return random.choice(responses)