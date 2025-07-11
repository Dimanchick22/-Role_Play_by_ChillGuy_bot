"""Обработчики команд - исправленная версия."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

# ИСПРАВЛЕНО: Импорт улучшенного базового обработчика
from handlers.base_handler import ImprovedBaseHandler

logger = logging.getLogger(__name__)

class CommandHandlers(ImprovedBaseHandler):
    """Обработчики команд бота."""
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        user = self.get_user_from_update(update)
        
        # Получаем сервис персонажа через улучшенный метод
        character_service = self.get_character_service()
        
        if character_service:
            welcome_message = character_service.get_welcome_message(user)
        else:
            welcome_message = f"Привет, {user.first_name}! 🌟 Я Алиса, твоя виртуальная помощница!"
        
        await self.safe_reply(update, welcome_message)
        await self.log_interaction(update, "start_command")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        # Проверяем доступные сервисы через улучшенные методы
        commands = [
            "/start - Знакомство со мной",
            "/help - Эта справка",
            "/info - Информация обо мне"
        ]
        
        if self.is_llm_available():
            commands.extend([
                "/clear - Очистить историю диалога",
                "/stats - Статистика работы"
            ])
        
        if self.is_image_generation_available():
            commands.extend([
                "/image <описание> - Генерация изображения"
            ])
        
        help_text = f"""🤖 Справка по боту

Привет! Я Алиса, твой виртуальный помощник!

📋 Доступные команды:
{chr(10).join(commands)}

💬 Просто пиши мне сообщения, и я отвечу!

{'🧠 Умные ответы через LLM активны' if self.is_llm_available() else '📝 Работаю в режиме шаблонов'}
{'🎨 Генерация изображений доступна' if self.is_image_generation_available() else ''}"""
        
        await self.safe_reply(update, help_text)
        await self.log_interaction(update, "help_command")
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info."""
        character_service = self.get_character_service()
        
        if character_service and hasattr(character_service, 'get_info'):
            info_text = character_service.get_info()
        else:
            info_text = """🌟 Привет! Меня зовут Алиса!

О себе:
• Дружелюбная и энергичная помощница
• Люблю общаться и помогать
• Всегда готова поддержать
• Обожаю узнавать новое

Давай дружить! 🤗"""
        
        await self.safe_reply(update, info_text)
        await self.log_interaction(update, "info_command")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats."""
        # Получаем статус всех сервисов
        services_health = self.get_services_status_summary()
        
        stats_lines = ["📊 Статистика сервисов:\n"]
        
        # LLM статистика
        if services_health['llm']:
            llm_service = self.get_llm_service()
            model_name = getattr(llm_service, 'active_model', 
                               getattr(llm_service, 'model_name', 'Неизвестно'))
            stats_lines.append(f"🧠 LLM: ✅ {model_name}")
        else:
            stats_lines.append("🧠 LLM: ❌ Недоступно")
        
        # Статистика изображений
        if services_health['image']:
            image_service = self.get_image_service()
            model_path = getattr(image_service, 'model_path', 'Неизвестно')
            stats_lines.append(f"🎨 Изображения: ✅ {model_path}")
        else:
            stats_lines.append("🎨 Изображения: ❌ Неактивно")
        
        # Статистика хранилища
        if services_health['storage']:
            storage_service = self.get_storage_service()
            if hasattr(storage_service, 'get_stats'):
                try:
                    storage_stats = storage_service.get_stats()
                    total_conversations = storage_stats.get('total_conversations', 0)
                    total_messages = storage_stats.get('total_messages', 0)
                    stats_lines.append(f"💾 Хранилище: ✅ {total_conversations} диалогов, {total_messages} сообщений")
                except:
                    stats_lines.append("💾 Хранилище: ⚠️ Ошибка получения статистики")
            else:
                stats_lines.append("💾 Хранилище: ✅ Активно")
        else:
            stats_lines.append("💾 Хранилище: ❌ Не найден")
        
        stats_text = "\n".join(stats_lines)
        await self.safe_reply(update, stats_text)
        await self.log_interaction(update, "stats_command")
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear - очистить историю."""
        user = self.get_user_from_update(update)
        
        storage_service = self.get_storage_service()
        if storage_service and hasattr(storage_service, 'clear_conversation'):
            try:
                storage_service.clear_conversation(user.id)
                await self.safe_reply(update, "🧹 История диалога очищена!")
                await self.log_interaction(update, "history_cleared")
            except Exception as e:
                logger.error(f"Ошибка очистки истории: {e}")
                await self.safe_reply(update, self.get_error_response("service_error"))
        else:
            await self.safe_reply(update, "❌ Сервис хранилища недоступен")
    
    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /image <prompt>."""
        if not context.args:
            await self.safe_reply(
                update,
                "📝 Использование: /image <описание>\n\n"
                "Пример: /image красивый закат над морем"
            )
            return
        
        # Проверяем сервис генерации изображений
        if not self.is_image_generation_available():
            await self.safe_reply(update, "❌ Генерация изображений недоступна")
            return
        
        image_service = self.get_image_service()
        prompt_text = " ".join(context.args)
        
        # Валидация промпта
        if not self.validate_message_length(prompt_text, 500):
            await self.safe_reply(update, "❌ Описание слишком длинное (максимум 500 символов)")
            return
        
        # Очищаем ввод
        prompt_text = self.sanitize_text_input(prompt_text)
        
        # Показываем статус генерации
        status_message = await update.message.reply_text(
            "🎨 Генерирую изображение... Это может занять несколько минут"
        )
        
        try:
            # Создаем промпт
            from services.image.base_generator import ImagePrompt
            prompt = ImagePrompt(
                text=prompt_text,
                size=(512, 512),
                steps=20
            )
            
            # Генерируем изображение
            result = await image_service.generate(prompt)
            
            # Отправляем результат
            with open(result.image_path, 'rb') as image_file:
                await update.message.reply_photo(
                    photo=image_file,
                    caption=f"🎨 Промпт: {prompt_text}\n⏱️ Время: {result.generation_time:.1f}с"
                )
            
            # Удаляем статусное сообщение
            await status_message.delete()
            
            await self.log_interaction(
                update, "image_generated", 
                prompt=prompt_text, 
                time=result.generation_time
            )
            
        except Exception as e:
            await status_message.edit_text(f"❌ Ошибка генерации: {str(e)}")
            logger.error(f"Ошибка генерации изображения: {e}")
            await self.log_interaction(update, "image_generation_failed", error=str(e))