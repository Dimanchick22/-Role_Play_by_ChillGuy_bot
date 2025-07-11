"""Главный класс приложения - исправленная версия."""

import logging
import asyncio
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
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Инициализирует приложение."""
        try:
            logger.info("🚀 Инициализация приложения...")
            
            # Создаем сервисы
            await self.factory.create_services()
            
            # Создаем Telegram приложение
            self.app = Application.builder().token(
                self.config.telegram.bot_token
            ).build()
            
            # Регистрируем обработчики
            self._register_handlers()
            
            logger.info("✅ Приложение инициализировано")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}", exc_info=True)
            return False
    
    async def start(self) -> None:
        """Запускает бота."""
        if not self.app:
            raise RuntimeError("Приложение не инициализировано")
        
        try:
            # Получаем информацию о боте
            bot_info = await self.app.bot.get_me()
            logger.info(f"🤖 Запуск бота @{bot_info.username}")
            
            # Логируем активные сервисы
            await self._log_services_status()
            
            self.is_running = True
            logger.info("👂 Бот слушает сообщения...")
            
            # Инициализируем приложение
            await self.app.initialize()
            
            # Запускаем updater
            await self.app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
            # Запускаем приложение
            await self.app.start()
            
            logger.info("✅ Бот успешно запущен!")
            
            # Бесконечный цикл для поддержания работы
            try:
                while self.is_running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("🛑 Получен сигнал остановки")
                
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            raise
        finally:
            await self._cleanup()
    
    async def stop(self) -> None:
        """Останавливает бота."""
        if self.is_running:
            logger.info("🛑 Начинаю остановку бота...")
            self.is_running = False
    
    async def _cleanup(self) -> None:
        """Очищает ресурсы."""
        logger.info("🧹 Очистка ресурсов...")
        
        try:
            if self.app:
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
            
            # Очищаем сервисы
            await self.factory.cleanup_services()
            
            logger.info("👋 Бот остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}", exc_info=True)
    
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
        
        # Дополнительная команда для отладки
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
    
    async def _log_services_status(self) -> None:
        """Логирует статус сервисов."""
        services_status = []
        
        # LLM сервис
        try:
            llm_service = registry.get('llm', None)
            if llm_service and hasattr(llm_service, 'is_available') and llm_service.is_available:
                model_name = getattr(llm_service, 'model_name', 'неизвестно')
                services_status.append(f"🧠 LLM: {model_name}")
            else:
                services_status.append("🧠 LLM: недоступен")
        except:
            services_status.append("🧠 LLM: не найден")
        
        # Сервис изображений (только если включен в конфигурации)
        if self.config.image.enabled:
            try:
                image_service = registry.get('image', None)
                if image_service and hasattr(image_service, 'is_initialized') and image_service.is_initialized:
                    services_status.append("🎨 Изображения: активны")
                else:
                    services_status.append("🎨 Изображения: неактивны")
            except:
                services_status.append("🎨 Изображения: не найден")
        else:
            services_status.append("🎨 Изображения: отключены")
        
        # Хранилище
        try:
            storage_service = registry.get('storage', None)
            if storage_service and hasattr(storage_service, 'get_stats'):
                stats = storage_service.get_stats()
                total_conversations = stats.get('total_conversations', 0)
                services_status.append(f"💾 Хранилище: {total_conversations} диалогов")
            else:
                services_status.append("💾 Хранилище: активно")
        except:
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