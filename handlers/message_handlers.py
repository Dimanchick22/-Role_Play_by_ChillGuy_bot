# handlers/message_handlers.py
"""Обработчики текстовых сообщений."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from handlers.base_handler import BaseHandler
from models.base import BaseMessage, MessageType, MessageRole

logger = logging.getLogger(__name__)

class MessageHandlers(BaseHandler):
    """Обработчики текстовых сообщений."""
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового сообщения."""
        user = self._get_user_from_update(update)
        message_text = update.message.text
        
        # Показываем "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            # Получаем сервисы
            llm_service = self.get_service('llm')
            storage_service = self.get_service('storage')
            character_service = self.get_service('character')
            
            # Создаем сообщение пользователя
            user_message = BaseMessage(
                id=str(update.message.message_id),
                content=message_text,
                role=MessageRole.USER,
                message_type=MessageType.TEXT,
                timestamp=datetime.now(),
                metadata={"user_id": user.id}
            )
            
            # Работаем с историей если есть хранилище
            if storage_service and hasattr(storage_service, 'get_conversation'):
                try:
                    conversation = storage_service.get_conversation(user.id)
                    conversation.add_message(user_message)
                    recent_messages = conversation.get_recent_messages()
                except Exception as e:
                    logger.warning(f"Ошибка работы с хранилищем: {e}")
                    recent_messages = [user_message]
            else:
                recent_messages = [user_message]
            
            # Генерируем ответ
            if llm_service and getattr(llm_service, 'is_available', False):
                try:
                    response_text = await llm_service.generate_response(
                        messages=recent_messages,
                        user=user
                    )
                    used_llm = True
                except Exception as e:
                    logger.warning(f"Ошибка LLM, переключаемся на шаблоны: {e}")
                    response_text = self._get_template_response(message_text, user.first_name, character_service)
                    used_llm = False
            else:
                response_text = self._get_template_response(message_text, user.first_name, character_service)
                used_llm = False
            
            # Создаем ответное сообщение
            bot_message = BaseMessage(
                id=f"bot_{datetime.now().timestamp()}",
                content=response_text,
                role=MessageRole.ASSISTANT,
                message_type=MessageType.TEXT,
                timestamp=datetime.now(),
                metadata={"generated_by": "llm" if used_llm else "template"}
            )
            
            # Сохраняем в историю
            if storage_service and hasattr(storage_service, 'save_conversation'):
                try:
                    conversation.add_message(bot_message)
                    storage_service.save_conversation(conversation)
                except Exception as e:
                    logger.warning(f"Ошибка сохранения в хранилище: {e}")
            
            # Отправляем ответ
            await update.message.reply_text(response_text)
            
            await self.log_interaction(
                update, "text_processed",
                response_length=len(response_text),
                used_llm=used_llm
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await update.message.reply_text(
                "Упс! 🙈 Что-то пошло не так. Попробуй еще раз!"
            )
    
    def _get_template_response(self, message: str, user_name: str, character_service) -> str:
        """Получает шаблонный ответ."""
        if character_service and hasattr(character_service, 'get_template_response'):
            return character_service.get_template_response(message, user_name)
        
        # Fallback ответы если персонаж недоступен
        import random
        responses = [
            f"Привет{f', {user_name}' if user_name else ''}! 😊 Как дела?",
            "Интересно! 😊 Расскажи больше!",
            "Классно! ✨ А что еще?",
            "Супер! 🎉 Я слушаю!"
        ]
        return random.choice(responses)
    
    def _get_user_from_update(self, update: Update):
        """Создает объект User из Update."""
        from models.base import User
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