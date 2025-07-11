#!/usr/bin/env python3
"""Исправленный тест бота для Windows без конфликтов event loop."""

import asyncio
import logging
import os
import platform
import sys
import threading
import time
from pathlib import Path

# Добавляем корневую папку в path
sys.path.append(str(Path(__file__).parent.parent))

# Настройка для Windows ПЕРЕД импортом telegram
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Загрузка переменных
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class WindowsTestBot:
    """Тестовый бот специально для Windows."""
    
    def __init__(self):
        self.app = None
        self.running = False
        self._stop_event = threading.Event()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        user = update.effective_user
        logger.info(f"📨 START команда от {user.first_name} ({user.id})")
        
        await update.message.reply_text(
            f"🤖 Привет, {user.first_name}!\n\n"
            f"✅ Windows тест-бот работает!\n"
            f"🖥️ Платформа: {platform.system()}\n"
            f"🐍 Python: {platform.python_version()}\n\n"
            f"📝 Отправь мне любое сообщение для теста."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        help_text = """🆘 Справка по тест-боту:

📋 Команды:
/start - Запуск бота
/help - Эта справка
/test - Тест всех функций
/info - Информация о системе
/stop - Остановить бота

💬 Просто пиши сообщения - я отвечу!"""
        
        await update.message.reply_text(help_text)
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stop."""
        await update.message.reply_text("🛑 Останавливаю бота...")
        self._stop_event.set()
        self.running = False
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test."""
        test_results = []
        
        # Тест 1: Платформа
        test_results.append(f"🖥️ Платформа: {platform.system()}")
        test_results.append(f"🐍 Python: {platform.python_version()}")
        
        # Тест 2: Переменные окружения
        bot_token = os.getenv("BOT_TOKEN")
        if bot_token:
            test_results.append("✅ BOT_TOKEN найден")
        else:
            test_results.append("❌ BOT_TOKEN не найден")
        
        # Тест 3: Event loop
        loop = asyncio.get_event_loop()
        test_results.append(f"🔄 Event loop: {type(loop).__name__}")
        
        # Тест 4: Права доступа
        try:
            test_file = Path("test_write.tmp")
            test_file.write_text("test")
            test_file.unlink()
            test_results.append("✅ Права записи: OK")
        except Exception as e:
            test_results.append(f"❌ Права записи: {e}")
        
        # Тест 5: Кодировка
        try:
            "тест".encode('utf-8')
            test_results.append("✅ UTF-8 кодировка: OK")
        except:
            test_results.append("❌ UTF-8 кодировка: ОШИБКА")
        
        result_text = "🧪 Результаты тестов:\n\n" + "\n".join(test_results)
        await update.message.reply_text(result_text)
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info."""
        info_lines = [
            f"🖥️ Операционная система: {platform.system()} {platform.release()}",
            f"🐍 Python: {platform.python_version()}",
            f"📁 Рабочая директория: {os.getcwd()}",
            f"🔄 Event loop policy: {type(asyncio.get_event_loop_policy()).__name__}",
            f"🌐 Кодировка по умолчанию: {sys.getdefaultencoding()}",
            f"📝 Логи сохраняются в: test_bot.log"
        ]
        
        info_text = "ℹ️ Информация о системе:\n\n" + "\n".join(info_lines)
        await update.message.reply_text(info_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений."""
        user = update.effective_user
        message_text = update.message.text
        
        logger.info(f"📨 Сообщение от {user.first_name} ({user.id}): {message_text}")
        
        # Показываем "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Ждем немного для реалистичности
        await asyncio.sleep(1)
        
        # Создаем ответ
        responses = [
            f"👋 Привет, {user.first_name}!",
            f"📝 Ты написал: '{message_text}'",
            f"✅ Windows бот работает отлично!",
            f"🕐 Время обработки: ~1 секунда"
        ]
        
        response = "\n\n".join(responses)
        await update.message.reply_text(response)
        
        logger.info("📤 Ответ отправлен успешно")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок."""
        logger.error(f"❌ Ошибка в боте: {context.error}")
        
        if update and update.message:
            try:
                await update.message.reply_text(
                    "❌ Произошла ошибка. Детали в логах."
                )
            except Exception as e:
                logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e}")
    
    def setup_application(self) -> Application:
        """Создает и настраивает приложение."""
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")
        
        logger.info("🔧 Создаем Telegram приложение...")
        
        # Создаем приложение с правильными настройками для Windows
        app = Application.builder().token(token).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("test", self.test_command))
        app.add_handler(CommandHandler("info", self.info_command))
        app.add_handler(CommandHandler("stop", self.stop_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Обработчик ошибок
        app.add_error_handler(self.error_handler)
        
        logger.info("📝 Обработчики добавлены")
        return app
    
    async def run_async(self):
        """Асинхронный запуск бота."""
        try:
            # Создаем приложение
            self.app = self.setup_application()
            
            # Проверяем подключение
            logger.info("🔗 Проверяем подключение к Telegram...")
            bot_info = await self.app.bot.get_me()
            logger.info(f"✅ Подключение успешно! Бот: @{bot_info.username}")
            
            # Инициализируем приложение
            await self.app.initialize()
            
            # Запускаем updater в отдельной задаче
            logger.info("🚀 Запуск updater...")
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            # Запускаем приложение
            await self.app.start()
            
            self.running = True
            logger.info("✅ Бот успешно запущен! Нажмите Ctrl+C для остановки")
            
            # Основной цикл - ждем сигнала остановки
            try:
                while self.running and not self._stop_event.is_set():
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("🛑 Получен сигнал отмены")
            
        except Exception as e:
            logger.error(f"💥 Ошибка запуска: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Очистка ресурсов."""
        logger.info("🧹 Очистка ресурсов...")
        
        if self.app:
            try:
                # Останавливаем updater
                if hasattr(self.app, 'updater') and self.app.updater.running:
                    logger.info("⏹️ Остановка updater...")
                    await self.app.updater.stop()
                
                # Останавливаем приложение
                logger.info("🔌 Остановка приложения...")
                await self.app.stop()
                
                # Завершаем работу
                logger.info("🔚 Завершение работы...")
                await self.app.shutdown()
                
            except Exception as e:
                logger.error(f"❌ Ошибка при остановке: {e}")
        
        self.running = False
        logger.info("👋 Бот остановлен")


def run_in_thread():
    """Запуск бота в отдельном потоке."""
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = WindowsTestBot()
    
    try:
        logger.info("🔄 Запуск бота в новом event loop...")
        loop.run_until_complete(bot.run_async())
    except KeyboardInterrupt:
        logger.info("⌨️ Получен сигнал Ctrl+C")
        bot.running = False
        bot._stop_event.set()
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            # Корректно закрываем loop
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.info(f"📋 Отмена {len(pending)} незавершенных задач...")
                for task in pending:
                    task.cancel()
                
                # Ждем завершения отмененных задач
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            
            loop.close()
            logger.info("🔚 Event loop закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия loop: {e}")


def main():
    """Главная функция."""
    print("🚀 Запуск Windows тест-бота...")
    print(f"🖥️ Платформа: {platform.system()}")
    print(f"🐍 Python: {platform.python_version()}")
    print("📝 Логи: test_bot.log")
    print("⚠️  Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    # Запускаем в отдельном потоке для изоляции event loop
    bot_thread = threading.Thread(target=run_in_thread, daemon=False)
    bot_thread.start()
    
    try:
        # Ждем завершения потока
        while bot_thread.is_alive():
            bot_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\n⌨️ Получен Ctrl+C, завершаем работу...")
    
    # Ждем корректного завершения потока
    if bot_thread.is_alive():
        print("⏳ Ожидание завершения бота...")
        bot_thread.join(timeout=10.0)
        
        if bot_thread.is_alive():
            print("⚠️ Поток не завершился за 10 секунд")
    
    print("👋 Программа завершена")


if __name__ == "__main__":
    main()