#!/usr/bin/env python3
"""
Отладочная версия бота для проверки получения сообщений.
Использование: python debug_bot.py
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start."""
    logger.info(f"Получена команда /start от пользователя {update.effective_user.first_name}")
    await update.message.reply_text("🤖 Привет! Отладочный бот работает!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений."""
    user = update.effective_user
    message_text = update.message.text
    
    logger.info(f"📨 Получено сообщение от {user.first_name} ({user.id}): {message_text}")
    
    # Показываем "печатает"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Простой ответ
    response = f"👋 Привет, {user.first_name}! Ты написал: '{message_text}'"
    await update.message.reply_text(response)
    
    logger.info(f"📤 Отправлен ответ: {response}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"❌ Ошибка: {context.error}")

async def main():
    """Главная функция."""
    token = os.getenv("BOT_TOKEN")
    
    if not token:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
        return
    
    logger.info("🚀 Запуск отладочного бота...")
    
    # Создаем приложение
    app = Application.builder().token(token).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    # Получаем информацию о боте
    try:
        bot_info = await app.bot.get_me()
        logger.info(f"🤖 Бот @{bot_info.username} готов к работе!")
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о боте: {e}")
        return
    
    # Запускаем polling
    logger.info("👂 Бот слушает сообщения...")
    
    try:
        await app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске polling: {e}")
    finally:
        logger.info("👋 Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")