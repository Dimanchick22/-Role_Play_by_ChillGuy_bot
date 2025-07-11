"""Обработчики текстовых сообщений - исправленная версия."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

# ИСПРАВЛЕНО: Импорт улучшенного базового обработчика
from handlers.base_handler import ImprovedBaseHandler
from models.base import BaseMessage, MessageType, MessageRole

logger = logging.getLogger(__name__)

class MessageHandlers(ImprovedBaseHandler):
    """Обработчики текстовых сообщений."""
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового сообщения."""
        user = self.get_user_from_update(update)
        message_text = update.message.text
        
        # Валидация и очистка ввода
        if not self.validate_message_length(message_text):
            await self.safe_reply(update, "❌ Сообщение слишком длинное")
            return
        
        message_text = self.sanitize_text_input(message_text)
        
        # Показываем "печатает"
        await self.send_typing_action(update, context)
        
        try:
            # Получаем сервисы через улучшенные методы
            storage_service = self.get_storage_service()
            character_service = self.get_character_service()
            
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
            recent_messages = [user_message]
            conversation = None
            
            if storage_service and hasattr(storage_service, 'get_conversation'):
                try:
                    conversation = storage_service.get_conversation(user.id)
                    conversation.add_message(user_message)
                    recent_messages = conversation.get_recent_messages()
                except Exception as e:
                    logger.warning(f"Ошибка работы с хранилищем: {e}")
            
            # Генерируем ответ
            response_text, used_llm = await self._generate_response(
                recent_messages, user, message_text, character_service
            )
            
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
            if conversation and storage_service:
                try:
                    conversation.add_message(bot_message)
                    storage_service.save_conversation(conversation)
                except Exception as e:
                    logger.warning(f"Ошибка сохранения в хранилище: {e}")
            
            # Отправляем ответ
            await self.safe_reply(update, response_text)
            
            await self.log_interaction(
                update, "text_processed",
                response_length=len(response_text),
                used_llm=used_llm
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await self._send_error_response(update)
    
    async def _generate_response(self, recent_messages, user, message_text, character_service) -> tuple[str, bool]:
        """Генерирует ответ, используя LLM или шаблоны."""
        
        # Пытаемся использовать LLM
        if self.is_llm_available():
            try:
                llm_service = self.get_llm_service()
                response_text = await llm_service.generate_response(
                    messages=recent_messages,
                    user=user
                )
                return response_text, True
                
            except Exception as e:
                logger.warning(f"Ошибка LLM, переключаемся на шаблоны: {e}")
        
        # Fallback на шаблонные ответы
        if character_service and hasattr(character_service, 'get_template_response'):
            response_text = character_service.get_template_response(
                message_text, user.first_name
            )
        else:
            # Используем базовые fallback ответы
            response_text = self.get_template_response_fallback(
                message_text, user.first_name
            )
        
        return response_text, False
    
    async def _send_error_response(self, update: Update):
        """Отправляет ответ при ошибке."""
        error_message = self.get_error_response("general")
        await self.safe_reply(update, error_message)