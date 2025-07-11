"""Точка входа приложения."""

import asyncio
import logging
import sys

from config.logging_config import setup_logging
from config.settings import load_config
from core.application import TelegramBotApplication

async def main():
    """Главная функция."""
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Настраиваем логирование
        setup_logging(config.log_level, config.debug)
        
        # Создаем и запускаем приложение
        app = TelegramBotApplication(config)
        
        if await app.initialize():
            await app.start()
        else:
            logging.error("❌ Не удалось инициализировать приложение")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения")
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())