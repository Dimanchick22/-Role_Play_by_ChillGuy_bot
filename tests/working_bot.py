#!/usr/bin/env python3
"""Рабочий бот для Windows с правильной обработкой event loop."""

import asyncio
import logging
import os
import platform
import signal
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для управления
app_instance = None
running = False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start."""
    user = update.effective_user
    logger.info(f"📨 START команда от {user.first_name} ({user.id})")
    
    await update.message.reply_text(
        f"🤖 Привет, {user.first_name}!\n\n"
        "✅ Бот работает!\n"
        "📝 Отправь мне любое сообщение для теста."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений."""
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"📨 Сообщение от {user.first_name} ({user.id}): {text}")
    
    # Показываем "печатает"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Простой ответ
    response = f"👋 Привет, {user.first_name}!\n\n🔄 Ты написал: '{text}'\n\n✨ Бот работает отлично!"
    await update.message.reply_text(response)
    
    logger.info("📤 Ответ отправлен успешно")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"❌ Ошибка в боте: {context.error}")

def setup_application():
    """Создает и настраивает приложение."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")
    
    logger.info("🔧 Создаем Telegram приложение...")
    
    # Создаем приложение с правильными настройками
    app = Application.builder().token(token).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("📝 Обработчики добавлены")
    return app

async def run_bot_async():
    """Асинхронный запуск бота."""
    global app_instance, running
    
    try:
        app_instance = setup_application()
        
        # Проверяем подключение
        logger.info("🔗 Проверяем подключение к Telegram...")
        bot_info = await app_instance.bot.get_me()
        logger.info(f"✅ Подключение успешно! Бот: @{bot_info.username}")
        
        # Инициализируем приложение
        logger.info("⚙️ Инициализация приложения...")
        await app_instance.initialize()
        
        # Запускаем updater
        logger.info("🚀 Запуск updater...")
        await app_instance.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
        # Запускаем приложение
        logger.info("▶️ Запуск приложения...")
        await app_instance.start()
        
        running = True
        logger.info("👂 Бот успешно запущен и слушает сообщения!")
        
        # Ждем остановки
        try:
            while running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        logger.error(f"💥 Ошибка запуска: {e}")
        raise
    finally:
        await cleanup()

async def cleanup():
    """Очистка ресурсов."""
    global app_instance, running
    
    logger.info("🧹 Очистка ресурсов...")
    running = False
    
    if app_instance:
        try:
            logger.info("⏹️ Остановка updater...")
            await app_instance.updater.stop()
            
            logger.info("🔌 Остановка приложения...")
            await app_instance.stop()
            
            logger.info("🔚 Завершение работы...")
            await app_instance.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")
    
    logger.info("👋 Бот остановлен")

def signal_handler(signum, frame):
    """Обработчик сигналов."""
    global running
    logger.info(f"🛑 Получен сигнал остановки ({signum})")
    running = False

def run_bot():
    """Запуск бота в отдельном event loop."""
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Регистрируем обработчики сигналов (только для Unix)
    if platform.system() != 'Windows':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🔄 Запуск бота в новом event loop...")
        loop.run_until_complete(run_bot_async())
    except KeyboardInterrupt:
        logger.info("⌨️ Получен сигнал Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        try:
            # Отменяем все задачи
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            logger.info("🔚 Event loop закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия loop: {e}")

def main():
    """Главная функция."""
    logger.info("🚀 Запуск бота...")
    logger.info(f"🖥️ Платформа: {platform.system()}")
    logger.info(f"🐍 Python: {platform.python_version()}")
    
    try:
        # Запускаем в отдельном потоке чтобы избежать проблем с event loop
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Ждем завершения
        bot_thread.join()
        
    except KeyboardInterrupt:
        logger.info("👋 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")

if __name__ == "__main__":
    main()