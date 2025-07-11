"""Обработчики команд."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from handlers.base_handler import BaseHandler
from models.base import User

logger = logging.getLogger(__name__)

class CommandHandlers(BaseHandler):
    """Обработчики команд бота."""
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        user = self._get_user_from_update(update)
        
        # Получаем сервис персонажа
        character_service = self.get_service('character')
        
        if character_service:
            welcome_message = character_service.get_welcome_message(user)
        else:
            welcome_message = f"Привет, {user.first_name}! 🌟 Я Алиса, твоя виртуальная помощница!"
        
        await update.message.reply_text(welcome_message)
        await self.log_interaction(update, "start_command")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        # Проверяем доступные сервисы
        llm_service = self.get_service('llm')
        image_service = self.get_service('image')
        
        commands = [
            "/start - Знакомство со мной",
            "/help - Эта справка",
            "/info - Информация обо мне"
        ]
        
        if llm_service and getattr(llm_service, 'is_available', False):
            commands.extend([
                "/clear - Очистить историю диалога",
                "/stats - Статистика работы"
            ])
        
        if image_service and getattr(image_service, 'is_initialized', False):
            commands.extend([
                "/image <описание> - Генерация изображения"
            ])
        
        help_text = f"""🤖 Справка по боту

Привет! Я Алиса, твой виртуальный помощник!

📋 Доступные команды:
{chr(10).join(commands)}

💬 Просто пиши мне сообщения, и я отвечу!

{'🧠 Умные ответы через LLM активны' if llm_service and getattr(llm_service, 'is_available', False) else '📝 Работаю в режиме шаблонов'}
{'🎨 Генерация изображений доступна' if image_service and getattr(image_service, 'is_initialized', False) else ''}"""
        
        await update.message.reply_text(help_text)
        await self.log_interaction(update, "help_command")
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info."""
        character_service = self.get_service('character')
        
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
        
        await update.message.reply_text(info_text)
        await self.log_interaction(update, "info_command")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats."""
        # Собираем статистику сервисов
        stats_lines = ["📊 Статистика сервисов:\n"]
        
        # LLM статистика
        llm_service = self.get_service('llm')
        if llm_service:
            if hasattr(llm_service, 'is_available') and llm_service.is_available:
                model_name = getattr(llm_service, 'model_name', 'Неизвестно')
                stats_lines.append(f"🧠 LLM: ✅ {model_name}")
            else:
                stats_lines.append("🧠 LLM: ❌ Недоступно")
        else:
            stats_lines.append("🧠 LLM: ❌ Не найден")
        
        # Статистика изображений
        image_service = self.get_service('image')
        if image_service:
            if hasattr(image_service, 'is_initialized') and image_service.is_initialized:
                model_path = getattr(image_service, 'model_path', 'Неизвестно')
                stats_lines.append(f"🎨 Изображения: ✅ {model_path}")
            else:
                stats_lines.append("🎨 Изображения: ❌ Неактивно")
        else:
            stats_lines.append("🎨 Изображения: ❌ Не найден")
        
        # Статистика хранилища
        storage_service = self.get_service('storage')
        if storage_service and hasattr(storage_service, 'get_stats'):
            try:
                storage_stats = storage_service.get_stats()
                total_conversations = storage_stats.get('total_conversations', 0)
                stats_lines.append(f"💾 Хранилище: ✅ {total_conversations} диалогов")
            except:
                stats_lines.append("💾 Хранилище: ⚠️ Ошибка")
        else:
            stats_lines.append("💾 Хранилище: ❌ Не найден")
        
        stats_text = "\n".join(stats_lines)
        await update.message.reply_text(stats_text)
        await self.log_interaction(update, "stats_command")
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear - очистить историю."""
        user = self._get_user_from_update(update)
        
        storage_service = self.get_service('storage')
        if storage_service and hasattr(storage_service, 'clear_conversation'):
            try:
                storage_service.clear_conversation(user.id)
                await update.message.reply_text("🧹 История диалога очищена!")
                await self.log_interaction(update, "history_cleared")
            except Exception as e:
                logger.error(f"Ошибка очистки истории: {e}")
                await update.message.reply_text("❌ Ошибка очистки истории")
        else:
            await update.message.reply_text("❌ Сервис хранилища недоступен")
    
    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /image <prompt>."""
        if not context.args:
            await update.message.reply_text(
                "📝 Использование: /image <описание>\n\n"
                "Пример: /image красивый закат над морем"
            )
            return
        
        # Проверяем сервис генерации изображений
        image_service = self.get_service('image')
        if not image_service:
            await update.message.reply_text("❌ Сервис генерации изображений не найден")
            return
        
        if not getattr(image_service, 'is_initialized', False):
            await update.message.reply_text("❌ Генерация изображений недоступна")
            return
        
        prompt_text = " ".join(context.args)
        
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
    
    def _get_user_from_update(self, update: Update) -> User:
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