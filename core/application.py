"""Главный класс приложения - унифицированная версия."""

import logging
from typing import Optional

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import AppConfig, load_config
from core.registry import registry
from core.service_initializer import ServiceInitializer

logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Главное приложение бота с унифицированной архитектурой."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.app: Optional[Application] = None
        self.initializer = ServiceInitializer(self.config)
    
    def run(self) -> None:
        """Запускает бота."""
        try:
            logger.info("🚀 Инициализация приложения...")
            
            # Создаем Telegram приложение
            self.app = Application.builder().token(
                self.config.telegram.bot_token
            ).build()
            
            # Инициализируем сервисы через унифицированный подход
            self._initialize_services()
            
            # Регистрируем обработчики
            self._register_handlers()
            
            logger.info("🤖 Бот готов к запуску")
            self._log_services_status()
            logger.info("👂 Бот слушает сообщения...")
            
            # Запускаем polling
            self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            raise
    
    def _initialize_services(self) -> None:
        """Инициализирует сервисы через унифицированный подход."""
        logger.info("🔧 Инициализация сервисов...")
        
        try:
            # Используем ServiceInitializer для создания всех сервисов
            success = self.initializer.initialize_all()
            
            if success:
                logger.info("✅ Все сервисы инициализированы")
            else:
                logger.warning("⚠️ Некоторые сервисы не удалось инициализировать")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации сервисов: {e}")
            raise
    
    def _register_handlers(self) -> None:
        """Регистрирует обработчики сообщений."""
        # Получаем обработчики из реестра
        command_handlers = registry.get('command_handlers')
        message_handlers = registry.get('message_handlers')
        
        if not command_handlers or not message_handlers:
            raise RuntimeError("Обработчики не найдены в реестре")
        
        # Команды
        self.app.add_handler(CommandHandler("start", command_handlers.start_command))
        self.app.add_handler(CommandHandler("help", command_handlers.help_command))
        self.app.add_handler(CommandHandler("stats", command_handlers.stats_command))
        self.app.add_handler(CommandHandler("clear", command_handlers.clear_command))
        self.app.add_handler(CommandHandler("info", command_handlers.info_command))
        
        # Генерация изображений (если доступна)
        if self.config.image.enabled and registry.has('image'):
            self.app.add_handler(CommandHandler("image", command_handlers.image_command))
        
        # Текстовые сообщения
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handlers.handle_text
        ))
        
        # Ошибки
        self.app.add_error_handler(self._error_handler)
        
        logger.info("📝 Обработчики зарегистрированы")
    
    def _log_services_status(self) -> None:
        """Логирует статус сервисов."""
        services_status = []
        
        # LLM сервис
        if registry.has('llm'):
            llm_service = registry.get('llm')
            if getattr(llm_service, 'is_available', False):
                model_name = getattr(llm_service, 'active_model', 'неизвестно')
                services_status.append(f"🧠 LLM: ✅ {model_name}")
            else:
                services_status.append("🧠 LLM: ❌ недоступен")
        else:
            services_status.append("🧠 LLM: ❌ не найден")
        
        # Сервис изображений
        if registry.has('image'):
            image_service = registry.get('image')
            if getattr(image_service, 'is_initialized', False):
                services_status.append("🎨 Изображения: ✅ активны")
            else:
                services_status.append("🎨 Изображения: ❌ не инициализированы")
        else:
            services_status.append("🎨 Изображения: ❌ отключены")
        
        # Хранилище
        if registry.has('storage'):
            services_status.append("💾 Хранилище: ✅ активно")
        else:
            services_status.append("💾 Хранилище: ❌ ошибка")
        
        logger.info("Статус сервисов:")
        for status in services_status:
            logger.info(f"  {status}")
    
    async def _error_handler(self, update, context) -> None:
        """Обработчик ошибок."""
        logger.error(f"Ошибка в боте: {context.error}", exc_info=context.error)
        
        if update and update.message:
            try:
                await update.message.reply_text(
                    "Упс! 🙈 Произошла ошибка. Попробуйте еще раз!"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    def cleanup(self) -> None:
        """Очистка ресурсов."""
        logger.info("🧹 Очистка ресурсов приложения...")
        self.initializer.cleanup()
        registry.clear()