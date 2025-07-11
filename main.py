"""Точка входа приложения - роль-плей версия."""

import logging
import sys
import platform

# ВАЖНО: WindowsProactorEventLoopPolicy устанавливаем ТОЛЬКО ЗДЕСЬ!
if platform.system() == 'Windows':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from config.logging_config import setup_logging
from config.settings import load_config
from core.application import RoleplayTelegramBotApplication  # Используем роль-плей версию

def main():
    """Главная функция."""
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Настраиваем логирование
        setup_logging(config.log_level, config.debug)
        
        logging.info("🎭 Запуск роль-плей Telegram бота...")
        logging.info(f"🖥️ Платформа: {platform.system()}")
        logging.info(f"🐍 Python: {platform.python_version()}")
        
        if platform.system() == 'Windows':
            logging.info("🪟 Использована Windows Event Loop Policy")
        
        logging.info("⚠️ Для остановки нажмите Ctrl+C")
        logging.info("🎭 Режим: Интерактивный роль-плей с генерацией изображений")
        
        # Создаем и запускаем роль-плей приложение
        app = RoleplayTelegramBotApplication(config)
        app.run()
        
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения (Ctrl+C)")
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()