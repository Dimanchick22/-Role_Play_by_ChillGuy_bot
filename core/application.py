"""Главный класс приложения - ПРАВИЛЬНАЯ версия."""

import logging
from typing import Optional

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import AppConfig, load_config
from core.registry import registry
from core.bot_factory import BotFactory

logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Главное приложение бота."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.app: Optional[Application] = None
        self.factory = BotFactory(self.config)
    
    def run(self) -> None:
        """Запускает бота - СИНХРОННО!"""
        try:
            logger.info("🚀 Инициализация приложения...")
            
            # Создаем Telegram приложение
            self.app = Application.builder().token(
                self.config.telegram.bot_token
            ).build()
            
            # Создаем сервисы СИНХРОННО
            self._create_services()
            
            # Регистрируем обработчики
            self._register_handlers()
            
            # Информацию о боте получим после запуска
            logger.info("🤖 Бот готов к запуску")
            
            # Логируем активные сервисы
            self._log_services_status()
            
            logger.info("👂 Бот слушает сообщения...")
            
            # python-telegram-bot САМА управляет event loop!
            # НЕ ИСПОЛЬЗУЕМ asyncio.run(), НЕ создаем потоки!
            self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            raise
    
    def _create_services(self) -> None:
        """Создает сервисы СИНХРОННО."""
        logger.info("🔧 Создание сервисов...")
        
        # Хранилище (всегда нужно)
        self._create_storage_service()
        
        # Персонаж (всегда нужен)
        self._create_character_service()
        
        # LLM сервис (опционально)
        if self.config.llm.provider != "none":
            self._create_llm_service()
        
        # Сервис изображений (опционально)
        if self.config.image.enabled:
            self._create_image_service()
        
        # Обработчики (всегда нужны)
        self._create_handlers()
        
        logger.info("✅ Сервисы созданы")
    
    def _create_storage_service(self) -> None:
        """Создает сервис хранилища."""
        try:
            from services.storage.memory_storage import MemoryStorage
            
            storage = MemoryStorage(
                max_conversations=self.config.storage.max_conversations
            )
            
            registry.register('storage', storage)
            logger.info("💾 Сервис хранилища создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания хранилища: {e}")
            raise
    
    def _create_character_service(self) -> None:
        """Создает сервис персонажа."""
        try:
            from characters.alice import AliceCharacter
            
            character = AliceCharacter()
            
            registry.register('character', character)
            logger.info("👩 Персонаж Алиса создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания персонажа: {e}")
            raise
    
    def _create_llm_service(self) -> None:
        """Создает LLM сервис."""
        try:
            if self.config.llm.provider == "ollama":
                from services.llm.ollama_client import OllamaClient
                
                llm = OllamaClient(
                    model_name=self.config.llm.model_name,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens
                )
                
                # Проверяем доступность СИНХРОННО
                try:
                    import ollama
                    ollama.list()  # Простая проверка
                    
                    registry.register('llm', llm)
                    logger.info(f"🧠 LLM сервис создан: {llm.model_name}")
                except:
                    logger.warning("⚠️ Ollama недоступна, бот будет работать без LLM")
            
            else:
                logger.warning(f"❓ Неизвестный LLM провайдер: {self.config.llm.provider}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания LLM сервиса: {e}")
            # Не падаем, бот может работать без LLM
    
    def _create_image_service(self) -> None:
        """Создает сервис генерации изображений."""
        try:
            logger.warning("🎨 Генерация изображений отключена (требует async инициализации)")
            # Можно добавить простую синхронную проверку доступности
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервиса изображений: {e}")
    
    def _create_handlers(self) -> None:
        """Создает обработчики сообщений."""
        try:
            from handlers.command_handlers import CommandHandlers
            from handlers.message_handlers import MessageHandlers
            
            command_handlers = CommandHandlers()
            message_handlers = MessageHandlers()
            
            registry.register('command_handlers', command_handlers)
            registry.register('message_handlers', message_handlers)
            
            logger.info("📝 Обработчики созданы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания обработчиков: {e}")
            raise
    
    def _register_handlers(self) -> None:
        """Регистрирует обработчики сообщений."""
        # Получаем обработчики из реестра
        command_handlers = registry.get('command_handlers')
        message_handlers = registry.get('message_handlers')
        
        # Команды
        self.app.add_handler(CommandHandler("start", command_handlers.start_command))
        self.app.add_handler(CommandHandler("help", command_handlers.help_command))
        self.app.add_handler(CommandHandler("stats", command_handlers.stats_command))
        self.app.add_handler(CommandHandler("clear", command_handlers.clear_command))
        self.app.add_handler(CommandHandler("info", command_handlers.info_command))
        
        # Генерация изображений (если доступна)
        if self.config.image.enabled:
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
            services_status.append("🧠 LLM: доступен")
        else:
            services_status.append("🧠 LLM: недоступен")
        
        # Сервис изображений
        if registry.has('image'):
            services_status.append("🎨 Изображения: активны")
        else:
            services_status.append("🎨 Изображения: отключены")
        
        # Хранилище
        if registry.has('storage'):
            services_status.append("💾 Хранилище: активно")
        else:
            services_status.append("💾 Хранилище: ошибка")
        
        logger.info("Активные сервисы:")
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