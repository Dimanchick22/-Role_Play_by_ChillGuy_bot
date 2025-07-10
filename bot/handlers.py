"""Обработчики команд и сообщений."""

import logging
import random
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from .character import Character
from .llm_client import LLMClient
from .model_selector import ModelSelector

logger = logging.getLogger(__name__)


class BotHandlers:
    """Класс с обработчиками бота."""
    
    def __init__(self, character: Character, llm: Optional[LLMClient] = None):
        self.character = character
        self.llm = llm
        self.use_llm = llm is not None
    
    def toggle_llm_mode(self) -> str:
        """Переключает режим LLM."""
        self.use_llm = not self.use_llm
        mode = "🤖 LLM" if self.use_llm else "📝 Шаблоны"
        return f"Режим изменен на: {mode}"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /start."""
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        
        # Устанавливаем персональный промпт для LLM
        if self.llm:
            prompt = self.character.get_system_prompt(user_name)
            self.llm.set_system_prompt(prompt)
        
        welcome = f"Привет, {user_name}! 🌟\n\n{self.character.get_info()}"
        
        if self.llm:
            mode = "🤖 LLM" if self.use_llm else "📝 Шаблоны"
            welcome += f"\n\nРежим: {mode}"
        
        await update.message.reply_text(welcome)
        logger.info(f"Новый пользователь: {user_name} ({user_id})")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /help."""
        commands = [
            "/start - Познакомиться со мной",
            "/help - Показать эту справку", 
            "/info - Узнать больше обо мне",
            "/question - Случайный вопрос"
        ]
        
        if self.llm:
            commands.extend([
                "/clear - Очистить историю",
                "/mode - Переключить режим",
                "/stats - Статистика",
                "/models - Список моделей",
                "/switch - Сменить модель"
            ])
        
        help_text = f"""🤖 Справка по боту

Привет! Я {self.character.name}, твой виртуальный друг!

Команды:
{chr(10).join(commands)}

Просто пиши мне сообщения! 💬"""
        
        await update.message.reply_text(help_text)
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /info."""
        await update.message.reply_text(self.character.get_info())
    
    async def question_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /question."""
        question = self.character.get_random_question()
        await update.message.reply_text(question)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /clear."""
        if not self.llm:
            await update.message.reply_text("LLM не подключена 🤷‍♀️")
            return
        
        user_id = update.effective_user.id
        self.llm.clear_history(user_id)
        await update.message.reply_text("История очищена! 🧹✨")
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /mode."""
        if not self.llm:
            await update.message.reply_text("LLM не подключена 🤷‍♀️")
            return
        
        response = self.toggle_llm_mode()
        await update.message.reply_text(response)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /stats."""
        if not self.llm:
            await update.message.reply_text("LLM не подключена 🤷‍♀️")
            return
        
        stats = self.llm.get_stats()
        stats_text = f"""📊 Статистика:

Модель: {stats['model']}
Активных диалогов: {stats['active_conversations']}
Максимум истории: {stats['max_history']} сообщений
Режим: {"🤖 LLM" if self.use_llm else "📝 Шаблоны"}"""
        
        await update.message.reply_text(stats_text)
    
    async def models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /models - показать доступные модели."""
        if not self.llm:
            await update.message.reply_text("LLM не подключена 🤷‍♀️")
            return
        
        try:
            selector = ModelSelector()
            models_list = selector.display_models()
            
            current_model = f"\n\n🎯 Текущая модель: {self.llm.model_name}"
            await update.message.reply_text(models_list + current_model)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка моделей: {e}")
            await update.message.reply_text("❌ Ошибка получения списка моделей")
    
    async def switch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /switch - смена модели."""
        if not self.llm:
            await update.message.reply_text("LLM не подключена 🤷‍♀️")
            return
        
        # Получаем аргумент команды
        args = context.args
        if not args:
            # Показываем доступные модели
            try:
                selector = ModelSelector()
                models_list = selector.display_models()
                help_text = f"""{models_list}

💡 Для смены модели используйте:
/switch <имя_модели>

Например:
/switch llama3.2:3b
/switch mistral"""
                await update.message.reply_text(help_text)
                return
            except Exception as e:
                await update.message.reply_text("❌ Ошибка получения списка моделей")
                return
        
        # Пытаемся сменить модель
        new_model = " ".join(args)
        
        try:
            # Проверяем доступность модели
            selector = ModelSelector()
            found_model = selector.find_model(new_model)
            
            if not found_model:
                available = ", ".join([m.name for m in selector.get_models()[:3]])
                await update.message.reply_text(
                    f"❌ Модель '{new_model}' не найдена\n\n"
                    f"Доступные: {available}...\n"
                    f"Используйте /models для полного списка"
                )
                return
            
            # Меняем модель
            old_model = self.llm.model_name
            self.llm.set_model(found_model.name)
            
            # Очищаем историю при смене модели
            user_id = update.effective_user.id
            self.llm.clear_history(user_id)
            
            await update.message.reply_text(
                f"✅ Модель изменена!\n\n"
                f"Было: {old_model}\n"
                f"Стало: {found_model.name}\n\n"
                f"История диалога очищена 🧹"
            )
            
            logger.info(f"Пользователь {update.effective_user.id} сменил модель с {old_model} на {found_model.name}")
            
        except Exception as e:
            logger.error(f"Ошибка смены модели: {e}")
            await update.message.reply_text(f"❌ Ошибка смены модели: {str(e)}")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений."""
        user_message = update.message.text
        user_name = update.effective_user.first_name
        user_id = update.effective_user.id
        
        # Показываем "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        
        try:
            # Выбираем способ ответа
            if self.use_llm and self.llm:
                response = await self.llm.get_response(user_message, user_id)
            else:
                response = self.character.get_template_response(user_message, user_name)
            
            await update.message.reply_text(response)
            
            # Логируем
            mode = "LLM" if (self.use_llm and self.llm) else "Template"
            logger.info(f"{user_name}: {user_message[:50]}... -> [{mode}] {response[:50]}...")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text("Упс! 🙈 Попробуй еще раз!")
    
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка медиа-файлов."""
        user_id = update.effective_user.id
        
        # Определяем тип медиа
        if update.message.sticker:
            media_prompt = "Пользователь прислал стикер"
            fallback_responses = ["Классный стикер! 😄", "Люблю стикеры! 🤩"]
        elif update.message.photo:
            media_prompt = "Пользователь прислал фото"
            fallback_responses = ["Красивое фото! 📸✨", "Вау! 🤩"]
        elif update.message.voice:
            media_prompt = "Пользователь прислал голосовое сообщение"
            fallback_responses = ["Получила голосовое! 🎤 Но пока не понимаю речь 😅"]
        elif update.message.video:
            media_prompt = "Пользователь прислал видео"
            fallback_responses = ["Интересное видео! 🎥", "Классно! ✨"]
        else:
            media_prompt = "Пользователь прислал файл"
            fallback_responses = ["Получила файл! 📎", "Спасибо! 😊"]
        
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            # Используем LLM или шаблон
            if self.use_llm and self.llm:
                response = await self.llm.get_response(media_prompt, user_id)
            else:
                response = random.choice(fallback_responses)
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Ошибка обработки медиа: {e}")
            await update.message.reply_text("Получила! 😊")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок."""
        logger.error("Ошибка в боте:", exc_info=context.error)
        
        if update and update.message:
            await update.message.reply_text("Упс! 🙈 Что-то пошло не так!")