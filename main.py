"""Точка входа приложения - исправленная версия для Windows."""

import asyncio
import logging
import sys
import signal
import platform
import threading

from config.logging_config import setup_logging
from config.settings import load_config
from core.application import TelegramBotApplication

# Настройка для Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Глобальная переменная для приложения
app_instance = None
running = False

def signal_handler(signum, frame):
    """Обработчик сигналов завершения."""
    global running
    logging.info(f"🛑 Получен сигнал {signum}")
    running = False

async def run_app_async():
    """Асинхронный запуск приложения."""
    global app_instance, running
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Настраиваем логирование
        setup_logging(config.log_level, config.debug)
        
        # Создаем приложение
        app_instance = TelegramBotApplication(config)
        
        # Инициализируем приложение
        if await app_instance.initialize():
            logging.info("✅ Приложение готово к запуску")
            
            running = True
            
            # Запускаем приложение в фоне
            app_task = asyncio.create_task(app_instance.start())
            
            # Ждем завершения
            try:
                while running:
                    await asyncio.sleep(1)
                    if app_task.done():
                        break
            except asyncio.CancelledError:
                pass
            
            # Останавливаем приложение
            if not app_task.done():
                app_task.cancel()
                try:
                    await app_task
                except asyncio.CancelledError:
                    pass
            
        else:
            logging.error("❌ Не удалось инициализировать приложение")
            return False
            
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        return False
    finally:
        if app_instance:
            await app_instance.stop()
    
    return True

def run_app():
    """Запуск приложения в отдельном event loop."""
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Регистрируем обработчики сигналов (только для Unix)
    if platform.system() != 'Windows':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logging.info("🔄 Запуск приложения в новом event loop...")
        success = loop.run_until_complete(run_app_async())
        return success
    except KeyboardInterrupt:
        logging.info("⌨️ Получен сигнал Ctrl+C")
        return True
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        return False
    finally:
        try:
            # Отменяем все задачи
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            logging.info("🔚 Event loop закрыт")
        except Exception as e:
            logging.error(f"❌ Ошибка закрытия loop: {e}")

def main():
    """Главная функция."""
    try:
        # Базовое логирование для старта
        logging.basicConfig(level=logging.INFO)
        logging.info("🚀 Запуск Telegram бота...")
        logging.info(f"🖥️ Платформа: {platform.system()}")
        logging.info(f"🐍 Python: {platform.python_version()}")
        
        # Запускаем в отдельном потоке чтобы избежать проблем с event loop
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Ждем завершения
        app_thread.join()
        
        logging.info("👋 Приложение завершено")
        
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения (Ctrl+C)")
        global running
        running = False
    except Exception as e:
        logging.error(f"💥 Ошибка запуска: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()