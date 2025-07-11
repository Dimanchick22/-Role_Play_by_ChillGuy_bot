"""Улучшенный базовый обработчик с dependency injection."""

import logging
from typing import Any, Optional
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from models.base import User
from core.service_initializer import ServiceUtils

logger = logging.getLogger(__name__)

class ImprovedBaseHandler:
    """Улучшенный базовый класс обработчика с dependency injection."""
    
    def __init__(self):
        # Используем ServiceUtils вместо прямого обращения к registry
        self.service_utils = ServiceUtils
    
    # === Получение сервисов через утилиты ===
    
    def get_storage_service(self):
        """Получает сервис хранилища."""
        return self.service_utils.get_storage_service()
    
    def get_character_service(self):
        """Получает сервис персонажа."""
        return self.service_utils.get_character_service()
    
    def get_llm_service(self):
        """Получает LLM сервис."""
        return self.service_utils.get_llm_service()
    
    def get_image_service(self):
        """Получает сервис изображений."""
        return self.service_utils.get_image_service()
    
    # === Проверки доступности сервисов ===
    
    def is_llm_available(self) -> bool:
        """Проверяет доступность LLM."""
        return self.service_utils.is_llm_available()
    
    def is_image_generation_available(self) -> bool:
        """Проверяет доступность генерации изображений."""
        return self.service_utils.is_image_generation_available()
    
    # === Общие методы ===
    
    def get_user_from_update(self, update: Update) -> User:
        """Создает объект User из Update."""
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
            f"👤 User {user.id} ({user.first_name}): {action}",
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
    
    def get_error_response(self, error_type: str = "general") -> str:
        """Получает ответ на ошибку от персонажа или fallback."""
        character_service = self.get_character_service()
        
        if character_service and hasattr(character_service, 'get_error_responses'):
            import random
            error_responses = character_service.get_error_responses()
            return random.choice(error_responses)
        
        # Fallback ответы по типам ошибок
        fallback_responses = {
            "general": "Упс! 🙈 Что-то пошло не так!",
            "llm_unavailable": "🧠 LLM сейчас недоступна, отвечаю по шаблонам",
            "image_unavailable": "🎨 Генерация изображений сейчас недоступна",
            "service_error": "⚙️ Сервис временно недоступен",
            "validation_error": "📝 Проверьте правильность введенных данных"
        }
        
        return fallback_responses.get(error_type, fallback_responses["general"])
    
    def get_template_response_fallback(self, message: str, user_name: str = "") -> str:
        """Fallback шаблонные ответы если персонаж недоступен."""
        import random
        
        message_lower = message.lower()
        
        # Простые шаблоны с эмодзи
        if any(word in message_lower for word in ["привет", "хай", "hello", "йо"]):
            responses = [
                f"Привет{f', {user_name}' if user_name else ''}! 😊 Как дела?",
                f"Хеллоу{f', {user_name}' if user_name else ''}! 👋 Что нового?",
                f"Йо{f', {user_name}' if user_name else ''}! 🤗 Как настроение?"
            ]
        elif any(word in message_lower for word in ["пока", "до свидания", "бай"]):
            responses = [
                "Пока! 👋 Хорошего дня!",
                "До встречи! 😊 Заходи еще!",
                "Бай-бай! 🌟 Всего доброго!"
            ]
        elif any(word in message_lower for word in ["спасибо", "благодарю", "пасибо"]):
            responses = [
                "Пожалуйста! 😊 Всегда рада помочь!",
                "Не за что! 💫 Обращайся еще!",
                "Рада помочь! 🌸"
            ]
        elif any(word in message_lower for word in ["грустно", "плохо", "расстроен"]):
            responses = [
                "Не грусти! 🤗 Что случилось?",
                "Держись! 💪 Все будет хорошо!",
                "Я с тобой! 🌟 Расскажи, что не так?"
            ]
        elif any(word in message_lower for word in ["отлично", "супер", "классно", "круто"]):
            responses = [
                "Вау, здорово! 🎉 Расскажи больше!",
                "Классно! ✨ Я рада за тебя!",
                "Супер! 🌟 Продолжай в том же духе!"
            ]
        else:
            responses = [
                "Интересно! 😊 Расскажи больше!",
                "Классно! ✨ А что еще?",
                "Вау! 🤩 Это звучит круто!",
                "Супер! 🎉 Я слушаю!",
                "Круто! 🌟 Продолжай!"
            ]
        
        return random.choice(responses)
    
    async def safe_reply(self, update: Update, text: str, 
                        parse_mode: Optional[str] = None) -> bool:
        """Безопасная отправка ответа с обработкой ошибок."""
        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            
            # Пытаемся отправить упрощенное сообщение
            try:
                await update.message.reply_text("❌ Произошла ошибка при отправке ответа")
                return False
            except Exception as e2:
                logger.error(f"❌ Критическая ошибка отправки: {e2}")
                return False
    
    def validate_message_length(self, text: str, max_length: int = 4000) -> bool:
        """Валидирует длину сообщения."""
        return len(text) <= max_length
    
    def sanitize_text_input(self, text: str) -> str:
        """Очищает текстовый ввод от потенциально опасных символов."""
        # Убираем управляющие символы кроме переноса строки и табуляции
        import re
        cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Ограничиваем длину
        if len(cleaned) > 4000:
            cleaned = cleaned[:4000] + "..."
        
        return cleaned.strip()
    
    async def handle_service_unavailable(self, update: Update, service_name: str):
        """Обрабатывает ситуацию недоступности сервиса."""
        error_message = self.get_error_response("service_error")
        logger.warning(f"⚠️ Сервис {service_name} недоступен для пользователя {update.effective_user.id}")
        await self.safe_reply(update, f"{error_message}\n\nСервис '{service_name}' временно недоступен.")
    
    def get_services_status_summary(self) -> dict:
        """Возвращает краткий статус всех сервисов."""
        return self.service_utils.get_service_health()