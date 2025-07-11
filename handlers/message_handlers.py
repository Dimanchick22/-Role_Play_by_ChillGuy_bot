"""Обработчики текстовых сообщений - полная версия с роль-плеем."""

import logging
import re
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from handlers.base_handler import ImprovedBaseHandler
from models.base import BaseMessage, MessageType, MessageRole

logger = logging.getLogger(__name__)

class MessageHandlers(ImprovedBaseHandler):
    """Стандартные обработчики текстовых сообщений."""
    
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


class RoleplayMessageHandlers(ImprovedBaseHandler):
    """Роль-плей обработчики текстовых сообщений с генерацией изображений."""
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового сообщения с роль-плеем и генерацией изображений."""
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
            # Получаем сервисы
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
            
            # Работаем с историей
            conversation = None
            message_count = 0
            
            if storage_service:
                try:
                    conversation = storage_service.get_conversation(user.id)
                    conversation.add_message(user_message)
                    message_count = len(conversation.messages)
                    
                    # Обновляем отношения в персонаже
                    if hasattr(character_service, 'update_relationship'):
                        character_service.update_relationship(message_count)
                        
                except Exception as e:
                    logger.warning(f"Ошибка работы с хранилищем: {e}")
            
            # Генерируем ответ
            response_text, image_prompt = await self._generate_roleplay_response(
                user_message, user, message_text, character_service, conversation
            )
            
            # Создаем ответное сообщение
            bot_message = BaseMessage(
                id=f"bot_{datetime.now().timestamp()}",
                content=response_text,
                role=MessageRole.ASSISTANT,
                message_type=MessageType.TEXT,
                timestamp=datetime.now(),
                metadata={
                    "generated_by": "llm" if self.is_llm_available() else "template",
                    "image_prompt": image_prompt,
                    "scene": getattr(character_service, 'current_scene', 'unknown'),
                    "mood": getattr(character_service, 'mood', 'neutral')
                }
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
            
            # Генерируем и отправляем изображение
            if image_prompt and self.is_image_generation_available():
                try:
                    await self._generate_and_send_image(update, context, image_prompt, response_text)
                except Exception as e:
                    logger.error(f"Ошибка генерации изображения: {e}")
                    # Не прерываем диалог из-за ошибки с картинкой
                    pass
            
            # Логируем взаимодействие
            await self.log_interaction(
                update, "roleplay_message",
                response_length=len(response_text),
                message_count=message_count,
                scene=getattr(character_service, 'current_scene', 'unknown'),
                mood=getattr(character_service, 'mood', 'neutral'),
                image_generated=bool(image_prompt and self.is_image_generation_available())
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки роль-плей сообщения: {e}", exc_info=True)
            await self._send_roleplay_error_response(update)
    
    async def _generate_roleplay_response(self, user_message, user, message_text, character_service, conversation) -> tuple[str, str]:
        """Генерирует роль-плей ответ с промптом для изображения."""
        
        # Пытаемся использовать LLM для более живого общения
        if self.is_llm_available():
            try:
                llm_service = self.get_llm_service()
                
                # Собираем контекст для LLM
                recent_messages = [user_message]
                if conversation:
                    recent_messages = conversation.get_recent_messages(5)
                
                # Генерируем ответ через LLM
                full_response = await llm_service.generate_response(
                    messages=recent_messages,
                    user=user
                )
                
                # Извлекаем промпт для изображения из ответа LLM
                response_text, image_prompt = self._extract_image_prompt(full_response)
                
                # Если промпт не найден, используем fallback
                if not image_prompt:
                    image_prompt = self._generate_fallback_image_prompt(response_text, character_service)
                
                return response_text, image_prompt
                
            except Exception as e:
                logger.warning(f"Ошибка LLM, переключаемся на шаблоны: {e}")
        
        # Fallback на шаблонные ответы
        if character_service and hasattr(character_service, 'get_template_response'):
            # Проверяем, возвращает ли шаблонный ответ tuple (с промптом изображения)
            template_result = character_service.get_template_response(message_text, user.first_name)
            
            if isinstance(template_result, tuple):
                response_text, image_prompt = template_result
            else:
                response_text = template_result
                image_prompt = self._generate_fallback_image_prompt(response_text, character_service)
        else:
            # Базовый fallback
            response_text = self.get_template_response_fallback(message_text, user.first_name)
            image_prompt = "young woman having casual conversation, friendly atmosphere"
        
        return response_text, image_prompt
    
    def _extract_image_prompt(self, llm_response: str) -> tuple[str, str]:
        """Извлекает промпт для изображения из ответа LLM."""
        # Ищем блок [IMAGE_PROMPT: ...]
        pattern = r'\[IMAGE_PROMPT:\s*([^\]]+)\]'
        match = re.search(pattern, llm_response, re.IGNORECASE)
        
        if match:
            image_prompt = match.group(1).strip()
            # Убираем промпт из основного текста
            clean_response = re.sub(pattern, '', llm_response, flags=re.IGNORECASE).strip()
            return clean_response, image_prompt
        
        return llm_response, ""
    
    def _generate_fallback_image_prompt(self, response_text: str, character_service) -> str:
        """Генерирует базовый промпт для изображения на основе ответа."""
        response_lower = response_text.lower()
        
        # Определяем эмоцию по тексту
        if any(emoji in response_text for emoji in ["😊", "😄", "🤗", "🎉"]):
            emotion = "happy"
        elif any(emoji in response_text for emoji in ["😢", "😔", "💔"]):
            emotion = "sad"
        elif any(emoji in response_text for emoji in ["😮", "😲", "🤔"]):
            emotion = "surprised"
        elif any(emoji in response_text for emoji in ["😏", "😉", "💖"]):
            emotion = "flirtatious"
        else:
            emotion = "neutral"
        
        # Определяем активность
        if any(word in response_lower for word in ["давай", "пойдем", "сделаем"]):
            activity = "active"
        elif any(word in response_lower for word in ["думаю", "размышляю", "вспоминаю"]):
            activity = "thoughtful"
        elif any(word in response_lower for word in ["слушаю", "смотрю", "читаю"]):
            activity = "engaged"
        else:
            activity = "talking"
        
        # Базовый промпт
        base_prompt = f"young woman, {emotion} expression, {activity} pose"
        
        # Добавляем контекст сцены если есть
        if character_service and hasattr(character_service, 'current_scene'):
            scene = character_service.current_scene
            if scene == "приветствие":
                base_prompt += ", greeting gesture"
            elif scene == "утешение":
                base_prompt += ", comforting atmosphere"
            elif scene == "развлечения":
                base_prompt += ", playful mood"
            elif scene == "прощание":
                base_prompt += ", waving goodbye"
            elif scene == "кафе":
                base_prompt += ", cafe setting, coffee atmosphere"
            elif scene == "парк":
                base_prompt += ", park background, outdoor setting"
            elif scene == "дома":
                base_prompt += ", home interior, cozy atmosphere"
            elif scene == "офис":
                base_prompt += ", office setting, professional"
            elif scene == "путешествие":
                base_prompt += ", travel setting, adventure mood"
        
        return base_prompt + ", casual clothes, warm lighting, portrait"
    
    async def _generate_and_send_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     image_prompt: str, response_text: str):
        """Генерирует и отправляет изображение."""
        try:
            image_service = self.get_image_service()
            if not image_service:
                return
            
            # Показываем статус генерации
            status_message = await update.message.reply_text("🎨 Генерирую картинку к нашей беседе...")
            
            # Создаем промпт для изображения
            from services.image.base_generator import ImagePrompt
            
            # Улучшаем промпт для лучшего качества
            enhanced_prompt = self._enhance_image_prompt(image_prompt)
            
            prompt = ImagePrompt(
                text=enhanced_prompt,
                negative_prompt="ugly, distorted, blurry, low quality, nsfw, nude",
                size=(512, 512),
                steps=20,
                cfg_scale=7.5
            )
            
            # Генерируем изображение
            result = await image_service.generate(prompt)
            
            # Отправляем изображение
            with open(result.image_path, 'rb') as image_file:
                await update.message.reply_photo(
                    photo=image_file,
                    caption=f"✨ {self._get_image_caption(response_text)}"
                )
            
            # Удаляем статусное сообщение
            await status_message.delete()
            
            logger.info(f"Изображение сгенерировано и отправлено за {result.generation_time:.1f}с")
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            # Пытаемся обновить статусное сообщение
            try:
                await status_message.edit_text("❌ Не удалось создать картинку, но диалог продолжается! 😊")
            except:
                pass
    
    def _enhance_image_prompt(self, base_prompt: str) -> str:
        """Улучшает промпт для лучшего качества изображения."""
        # Добавляем качественные теги
        quality_tags = [
            "high quality", "detailed", "professional", 
            "good lighting", "sharp focus", "realistic"
        ]
        
        # Добавляем стилистические теги
        style_tags = [
            "portrait photography", "natural lighting", "casual style"
        ]
        
        enhanced = base_prompt
        
        # Добавляем случайные улучшения
        import random
        enhanced += f", {random.choice(quality_tags)}, {random.choice(style_tags)}"
        
        return enhanced
    
    def _get_image_caption(self, response_text: str) -> str:
        """Создает подпись к изображению на основе ответа."""
        # Берем первое предложение ответа для подписи
        sentences = response_text.split('.')
        if sentences and len(sentences[0]) > 10:
            caption = sentences[0].strip()
            if len(caption) > 100:
                caption = caption[:97] + "..."
            return caption
        
        return "Момент из нашей беседы ✨"
    
    async def _send_roleplay_error_response(self, update: Update):
        """Отправляет роль-плей ответ при ошибке."""
        character_service = self.get_character_service()
        
        if character_service and hasattr(character_service, 'get_error_responses'):
            import random
            error_responses = character_service.get_error_responses()
            
            # Проверяем формат ответов (tuple или string)
            if error_responses and isinstance(error_responses[0], tuple):
                response_text, image_prompt = random.choice(error_responses)
            else:
                response_text = random.choice(error_responses) if error_responses else "Упс! 🙈 Что-то пошло не так!"
                image_prompt = "confused young woman, embarrassed expression, questioning gesture"
        else:
            response_text = "Упс! 🙈 Что-то пошло не так! Но давай не будем останавливаться - расскажи, как дела?"
            image_prompt = "confused young woman, embarrassed expression, questioning gesture"
        
        await self.safe_reply(update, response_text)
        
        # Попытаемся сгенерировать изображение даже для ошибки
        if self.is_image_generation_available():
            try:
                await self._generate_and_send_image(update, None, image_prompt, response_text)
            except Exception:
                pass  # Игнорируем ошибки генерации изображений при ошибках
    
    async def handle_conversation_starter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запускает случайный стартер беседы (можно вызывать периодически)."""
        character_service = self.get_character_service()
        
        if character_service and hasattr(character_service, 'get_random_conversation_starter'):
            result = character_service.get_random_conversation_starter()
            
            if isinstance(result, tuple):
                response_text, image_prompt = result
            else:
                response_text = result
                image_prompt = "young woman starting conversation, engaging expression"
            
            await self.safe_reply(update, response_text)
            
            if self.is_image_generation_available():
                try:
                    await self._generate_and_send_image(update, context, image_prompt, response_text)
                except Exception as e:
                    logger.error(f"Ошибка генерации изображения для стартера: {e}")
    
    def _analyze_conversation_flow(self, conversation) -> dict:
        """Анализирует ход беседы для адаптации поведения."""
        if not conversation or len(conversation.messages) < 2:
            return {"engagement": "new", "topic_changes": 0, "emotional_tone": "neutral"}
        
        messages = conversation.messages[-10:]  # Последние 10 сообщений
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        
        # Подсчитываем вовлеченность
        avg_length = sum(len(msg.content) for msg in user_messages) / len(user_messages) if user_messages else 0
        
        if avg_length > 100:
            engagement = "high"
        elif avg_length > 30:
            engagement = "medium"
        else:
            engagement = "low"
        
        # Анализируем эмоциональный тон
        emotional_keywords = {
            "positive": ["хорошо", "отлично", "круто", "классно", "супер", "здорово"],
            "negative": ["плохо", "грустно", "ужасно", "отвратительно", "скучно"],
            "excited": ["вау", "ого", "невероятно", "потрясающе", "обожаю"],
            "calm": ["нормально", "спокойно", "тихо", "размеренно"]
        }
        
        emotional_tone = "neutral"
        for tone, keywords in emotional_keywords.items():
            if any(keyword in msg.content.lower() for msg in user_messages for keyword in keywords):
                emotional_tone = tone
                break
        
        return {
            "engagement": engagement,
            "message_count": len(user_messages),
            "emotional_tone": emotional_tone,
            "avg_message_length": avg_length
        }