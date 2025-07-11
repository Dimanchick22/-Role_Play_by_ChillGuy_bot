"""Точка входа приложения - ПРАВИЛЬНАЯ версия."""

import logging
import sys
import platform
from config.logging_config import setup_logging
from config.settings import load_config
from core.application import TelegramBotApplication

# Настройка для Windows (ТОЛЬКО для политики, НЕ для создания loop)
if platform.system() == 'Windows':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def main():
    """Главная функция - СИНХРОННАЯ!"""
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Настраиваем логирование
        setup_logging(config.log_level, config.debug)
        
        logging.info("🚀 Запуск Telegram бота...")
        logging.info(f"🖥️ Платформа: {platform.system()}")
        logging.info(f"🐍 Python: {platform.python_version()}")
        logging.info("⚠️ Для остановки нажмите Ctrl+C")
        
        # Создаем приложение
        app = TelegramBotApplication(config)
        
        # python-telegram-bot САМА управляет event loop
        # Мы НЕ создаем никаких loop'ов, НЕ используем threading
        app.run()  # Простой синхронный метод
        
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения (Ctrl+C)")
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()