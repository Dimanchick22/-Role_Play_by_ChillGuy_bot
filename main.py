"""Главный файл бота."""

import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config
from bot.character import Character
from bot.llm_client import LLMClient
from bot.handlers import BotHandlers
from bot.model_selector import ModelSelector, select_model_cli


def setup_logging() -> None:
    """Настройка логирования."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, Config.get_log_level()),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )


def select_model() -> str:
    """Выбор модели для использования."""
    logger = logging.getLogger(__name__)
    
    # Если модель задана конкретно
    if Config.OLLAMA_MODEL and Config.OLLAMA_MODEL != "auto":
        logger.info(f"Используется модель из конфига: {Config.OLLAMA_MODEL}")
        return Config.OLLAMA_MODEL
    
    # Автоматический выбор
    try:
        selector = ModelSelector()
        
        # Интерактивный выбор если включен
        if Config.INTERACTIVE_MODEL_SELECT and sys.stdout.isatty():
            print("🤖 Выбор модели для бота\n")
            selected = selector.select_interactive()
            if selected:
                return selected
        
        # Автоматический выбор рекомендуемой модели
        recommended = selector.get_recommended_model()
        if recommended:
            logger.info(f"Автоматически выбрана модель: {recommended.name}")
            return recommended.name
        
        # Если моделей нет
        raise RuntimeError("Нет доступных моделей")
        
    except Exception as e:
        logger.error(f"Ошибка выбора модели: {e}")
        raise


def create_llm_client() -> LLMClient:
    """Создает LLM клиент с выбором модели."""
    try:
        # Выбираем модель
        model_name = select_model()
        
        # Создаем клиент
        llm = LLMClient(model_name, Config.MAX_HISTORY)
        logging.info(f"✅ LLM подключена: {model_name}")
        
        return llm
        
    except Exception as e:
        logging.error(f"❌ Ошибка подключения LLM: {e}")
        logging.info("Бот будет работать в режиме шаблонов")
        return None


def main() -> None:
    """Главная функция."""
    # Настройка
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск бота...")
    
    # Инициализация компонентов
    character = Character()
    llm = create_llm_client() if Config.USE_LLM else None
    handlers = BotHandlers(character, llm)
    
    # Создание приложения
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("info", handlers.info_command))
    app.add_handler(CommandHandler("question", handlers.question_command))
    
    if llm:
        app.add_handler(CommandHandler("clear", handlers.clear_command))
        app.add_handler(CommandHandler("mode", handlers.mode_command))
        app.add_handler(CommandHandler("stats", handlers.stats_command))
        app.add_handler(CommandHandler("models", handlers.models_command))
        app.add_handler(CommandHandler("switch", handlers.switch_command))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handlers.handle_text
    ))
    app.add_handler(MessageHandler(
        ~filters.TEXT & ~filters.COMMAND,
        handlers.handle_media
    ))
    
    # Обработчик ошибок
    app.add_error_handler(handlers.error_handler)
    
    # Запуск
    mode = "с LLM" if llm else "в режиме шаблонов"
    logger.info(f"🤖 Бот {character.name} запущен {mode}!")
    logger.info("Нажмите Ctrl+C для остановки")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()