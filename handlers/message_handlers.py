"""Обработчики текстовых сообщений - обновленная версия."""

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
        user = self.get_user_from_update(update)  # Используем общий метод
        message_text = update.message.text
        
        # Показываем "печатает"
        await self.send_typing_action(update, context)
        
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
            response_text, used_llm = await self._generate_response(
                llm_service, character_service, recent_messages, user, message_text
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
            await self._send_error_response(update, character_service)
    
    async def _generate_response(self, llm_service, character_service, 
                               recent_messages, user, message_text) -> tuple[str, bool]:
        """Генерирует ответ, используя LLM или шаблоны."""
        
        # Пытаемся использовать LLM
        if llm_service and getattr(llm_service, 'is_available', False):
            try:
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
    
    async def _send_error_response(self, update: Update, character_service):
        """Отправляет ответ при ошибке."""
        try:
            if character_service and hasattr(character_service, 'get_error_responses'):
                import random
                error_responses = character_service.get_error_responses()
                error_message = random.choice(error_responses)
            else:
                error_message = "Упс! 🙈 Что-то пошло не так. Попробуй еще раз!"
            
            await update.message.reply_text(error_message)
            
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")