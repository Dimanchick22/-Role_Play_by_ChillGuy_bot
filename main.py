"""Точка входа приложения - версия с принудительным завершением."""

import asyncio
import logging
import sys
import signal
import platform
import threading
import time
import os
from typing import Optional

from config.logging_config import setup_logging
from config.settings import load_config
from core.application import TelegramBotApplication

# Настройка для Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Глобальные переменные для управления
app_instance: Optional[TelegramBotApplication] = None
running = False
shutdown_event = threading.Event()
force_exit = False

def signal_handler(signum, frame):
    """Обработчик сигналов завершения."""
    global running, force_exit
    logging.info(f"🛑 Получен сигнал {signum}")
    running = False
    shutdown_event.set()
    
    # Через 3 секунды принудительно завершаем
    def force_shutdown():
        time.sleep(3)
        if not force_exit:
            logging.warning("🔪 Принудительное завершение через 3 секунды...")
            os._exit(0)
    
    threading.Thread(target=force_shutdown, daemon=True).start()

async def run_app_async():
    """Асинхронный запуск приложения."""
    global app_instance, running, force_exit
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Создаем приложение
        app_instance = TelegramBotApplication(config)
        
        # Инициализируем приложение
        if not await app_instance.initialize():
            logging.error("❌ Не удалось инициализировать приложение")
            return False
        
        logging.info("✅ Приложение готово к запуску")
        running = True
        
        # Запускаем приложение
        await app_instance.start()
        
        return True
            
    except KeyboardInterrupt:
        logging.info("⌨️ Получен сигнал прерывания (Ctrl+C)")
        return True
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        return False
    finally:
        # Корректное завершение
        if app_instance:
            try:
                logging.info("🛑 Начинаю корректное завершение...")
                
                # Ограничиваем время на завершение
                async def cleanup_with_timeout():
                    try:
                        await asyncio.wait_for(app_instance.stop(), timeout=2.0)
                    except asyncio.TimeoutError:
                        logging.warning("⚠️ Таймаут завершения, принудительно закрываем")
                
                await cleanup_with_timeout()
                logging.info("✅ Приложение корректно остановлено")
                
            except Exception as e:
                logging.error(f"❌ Ошибка при завершении: {e}")
        
        force_exit = True

def run_app():
    """Запуск приложения в отдельном event loop."""
    global running, shutdown_event, force_exit
    
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        logging.info("🔄 Запуск приложения в новом event loop...")
        
        # Запускаем основное приложение
        success = loop.run_until_complete(run_app_async())
        
        if success:
            logging.info("✅ Приложение завершилось успешно")
        else:
            logging.error("❌ Приложение завершилось с ошибками")
            
        return success
        
    except KeyboardInterrupt:
        logging.info("⌨️ Получен Ctrl+C в потоке приложения")
        running = False
        return True
    except Exception as e:
        logging.error(f"💥 Критическая ошибка в потоке: {e}", exc_info=True)
        return False
    finally:
        force_exit = True
        try:
            # Быстро закрываем event loop
            logging.info("🔄 Быстрое закрытие event loop...")
            
            # Отменяем все задачи максимально быстро
            pending_tasks = asyncio.all_tasks(loop)
            if pending_tasks:
                for task in pending_tasks:
                    task.cancel()
                
                # Даем 1 секунду на завершение
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending_tasks, return_exceptions=True),
                            timeout=1.0
                        )
                    )
                except asyncio.TimeoutError:
                    logging.warning("⚠️ Таймаут отмены задач")
            
            loop.close()
            logging.info("🔚 Event loop закрыт")
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка закрытия event loop: {e}")

def setup_signal_handlers():
    """Настройка обработчиков сигналов."""
    if platform.system() != 'Windows':
        # Для Unix-подобных систем
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        logging.info("📡 Обработчики сигналов настроены (Unix)")
    else:
        # Для Windows используем другой подход
        try:
            signal.signal(signal.SIGINT, signal_handler)
            logging.info("📡 Обработчик SIGINT настроен (Windows)")
        except Exception as e:
            logging.warning(f"⚠️ Не удалось настроить обработчик сигналов: {e}")

def main():
    """Главная функция."""
    global running, shutdown_event, force_exit
    
    try:
        # Проверяем конфигурацию первым делом
        try:
            config = load_config()
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            sys.exit(1)
        
        # Настраиваем логирование ОДИН РАЗ
        setup_logging(config.log_level, config.debug)
        
        logging.info("🚀 Запуск Telegram бота...")
        logging.info(f"🖥️ Платформа: {platform.system()}")
        logging.info(f"🐍 Python: {platform.python_version()}")
        logging.info("⚠️ Для остановки нажмите Ctrl+C")
        
        # Настраиваем обработчики сигналов
        setup_signal_handlers()
        
        # Запускаем в отдельном потоке
        logging.info("🎯 Запуск бота в отдельном потоке...")
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Основной поток ждет завершения или сигнала
        try:
            while app_thread.is_alive() and not shutdown_event.is_set() and not force_exit:
                time.sleep(0.1)  # Очень короткий интервал для быстрой реакции
        except KeyboardInterrupt:
            logging.info("⌨️ Получен Ctrl+C в главном потоке")
            running = False
            shutdown_event.set()
        
        # Даем потоку 2 секунды на завершение
        if app_thread.is_alive() and not force_exit:
            logging.info("⏳ Ожидание завершения потока приложения...")
            app_thread.join(timeout=2.0)
            
            if app_thread.is_alive():
                logging.warning("⚠️ Поток приложения не завершился за 2 секунды")
                logging.info("🔪 Принудительное завершение...")
                force_exit = True
        
        # Принудительно завершаем если нужно
        if not force_exit:
            force_exit = True
            
        logging.info("👋 Приложение завершено")
        
        # Принудительно выходим из Python
        logging.info("🚪 Принудительный выход из программы...")
        os._exit(0)
        
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения (Ctrl+C)")
        running = False
        shutdown_event.set()
        force_exit = True
        os._exit(0)
    except Exception as e:
        logging.error(f"💥 Критическая ошибка в main: {e}", exc_info=True)
        os._exit(1)

if __name__ == "__main__":
    main()