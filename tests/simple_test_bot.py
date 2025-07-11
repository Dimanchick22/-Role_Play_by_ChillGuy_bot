#!/usr/bin/env python3
"""Самый простой тест бота для Windows."""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start."""
    logger.info(f"START команда от {update.effective_user.first_name}")
    await update.message.reply_text("✅ Простой бот работает!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений."""
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"📨 Сообщение от {user.first_name}: {text}")
    
    response = f"Эхо: {text}"
    await update.message.reply_text(response)
    
    logger.info("📤 Ответ отправлен")

async def main():
    """Главная функция."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Нет токена!")
        return
    
    print("🚀 Создаем приложение...")
    app = Application.builder().token(token).build()
    
    print("📝 Добавляем обработчики...")
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🔗 Проверяем подключение...")
    bot_info = await app.bot.get_me()
    print(f"✅ Бот готов: @{bot_info.username}")
    
    print("👂 Запускаем polling...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Остановлено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()