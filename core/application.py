"""Главный класс приложения - улучшенная архитектура."""

import logging
from typing import Optional

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import AppConfig, load_config
from core.registry import registry
from core.service_initializer import ImprovedServiceInitializer, ServiceUtils

logger = logging.getLogger(__name__)

class TelegramBotApplication:
    """Главное приложение бота с улучшенной архитектурой."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.app: Optional[Application] = None
        self.initializer = ImprovedServiceInitializer(self.config)
        self._is_running = False
    
    def run(self) -> None:
        """Запускает бота."""
        try:
            logger.info("🚀 Инициализация приложения...")
            
            # Создаем Telegram приложение
            self.app = Application.builder().token(
                self.config.telegram.bot_token
            ).build()
            
            # Инициализируем сервисы через улучшенный подход
            if not self._initialize_services():
                raise RuntimeError("Не удалось инициализировать критически важные сервисы")
            
            # Регистрируем обработчики
            self._register_handlers()
            
            # Логируем статус
            self._log_application_status()
            
            logger.info("👂 Бот слушает сообщения...")
            self._is_running = True
            
            # Запускаем polling
            self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
            raise
        finally:
            self._is_running = False
            self._cleanup()
    
    def _initialize_services(self) -> bool:
        """Инициализирует сервисы через улучшенный подход."""
        logger.info("🔧 Инициализация сервисов...")
        
        try:
            # Используем улучшенный ServiceInitializer
            import asyncio
            success = asyncio.get_event_loop().run_until_complete(
                self.initializer.initialize_all()
            )
            
            # Получаем отчет об инициализации
            report = self.initializer.get_initialization_report()
            
            logger.info(f"📊 Результат инициализации:")
            logger.info(f"  Успешность: {report['success_rate']:.0%}")
            logger.info(f"  Готово сервисов: {len(report['initialized_services'])}")
            logger.info(f"  Все обязательные готовы: {report['all_required_ready']}")
            
            # Детальный лог по сервисам
            for service_name, status in report['registry_status']['services'].items():
                status_emoji = "✅" if status['lifecycle'] == 'ready' else "❌"
                logger.info(f"  {status_emoji} {service_name}: {status['lifecycle']}")
                
                if status['error']:
                    logger.warning(f"    Ошибка: {status['error']}")
            
            return report['all_required_ready']
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации сервисов: {e}")
            return False
    
    def _register_handlers(self) -> None:
        """Регистрирует обработчики сообщений."""
        try:
            # Получаем обработчики через утилиты
            command_handlers = registry.get('command_handlers')
            message_handlers = registry.get('message_handlers')
            
            if not command_handlers or not message_handlers:
                raise RuntimeError("Обработчики не найдены в реестре")
            
            # Основные команды
            self.app.add_handler(CommandHandler("start", command_handlers.start_command))
            self.app.add_handler(CommandHandler("help", command_handlers.help_command))
            self.app.add_handler(CommandHandler("info", command_handlers.info_command))
            
            # Команды для работы с историей (если LLM доступен)
            if ServiceUtils.is_llm_available():
                self.app.add_handler(CommandHandler("clear", command_handlers.clear_command))
                self.app.add_handler(CommandHandler("stats", command_handlers.stats_command))
            
            # Команды для генерации изображений (если доступны)
            if ServiceUtils.is_image_generation_available():
                self.app.add_handler(CommandHandler("image", command_handlers.image_command))
            
            # Текстовые сообщения
            self.app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                message_handlers.handle_text
            ))
            
            # Обработчик ошибок
            self.app.add_error_handler(self._error_handler)
            
            logger.info("📝 Обработчики зарегистрированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации обработчиков: {e}")
            raise
    
    def _log_application_status(self) -> None:
        """Логирует статус приложения."""
        logger.info("🤖 Статус бота:")
        
        # Получаем состояние здоровья сервисов
        health = ServiceUtils.get_service_health()
        
        # Основные сервисы
        storage_status = "✅ активно" if health['storage'] else "❌ ошибка"
        character_status = "✅ активен" if health['character'] else "❌ ошибка"
        
        logger.info(f"  💾 Хранилище: {storage_status}")
        logger.info(f"  👩 Персонаж: {character_status}")
        
        # LLM сервис
        if health['llm']:
            llm_service = ServiceUtils.get_llm_service()
            model_name = getattr(llm_service, 'active_model', 'неизвестно')
            logger.info(f"  🧠 LLM: ✅ {model_name}")
        else:
            logger.info("  🧠 LLM: ❌ недоступен (работаем в режиме шаблонов)")
        
        # Сервис изображений
        if health['image']:
            logger.info("  🎨 Изображения: ✅ активны")
        else:
            logger.info("  🎨 Изображения: ❌ отключены")
        
        # Обработчики
        handlers_status = "✅" if health['command_handlers'] and health['message_handlers'] else "❌"
        logger.info(f"  📝 Обработчики: {handlers_status}")
        
        # Общий статус
        critical_services = ['storage', 'character', 'command_handlers', 'message_handlers']
        all_critical_ready = all(health[service] for service in critical_services)
        
        if all_critical_ready:
            logger.info("🟢 Бот полностью готов к работе!")
        else:
            logger.warning("🟡 Бот готов, но некоторые сервисы недоступны")
    
    async def _error_handler(self, update, context) -> None:
        """Улучшенный обработчик ошибок."""
        error = context.error
        logger.error(f"Ошибка в боте: {error}", exc_info=error)
        
        # Пытаемся определить тип ошибки и дать соответствующий ответ
        if update and update.message:
            try:
                # Получаем персонажа для генерации ответа об ошибке
                character_service = ServiceUtils.get_character_service()
                
                if character_service and hasattr(character_service, 'get_error_responses'):
                    import random
                    error_responses = character_service.get_error_responses()
                    error_message = random.choice(error_responses)
                else:
                    error_message = "Упс! 🙈 Что-то пошло не так. Попробуйте еще раз!"
                
                await update.message.reply_text(error_message)
                
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    def _cleanup(self) -> None:
        """Очистка ресурсов приложения."""
        logger.info("🧹 Очистка ресурсов приложения...")
        
        try:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                self.initializer.cleanup()
            )
        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")
    
    @property
    def is_running(self) -> bool:
        """Проверяет, запущен ли бот."""
        return self._is_running
    
    def get_application_status(self) -> dict:
        """Возвращает статус приложения."""
        health = ServiceUtils.get_service_health()
        report = self.initializer.get_initialization_report()
        
        return {
            "is_running": self.is_running,
            "services_health": health,
            "initialization_report": report,
            "telegram_app_ready": self.app is not None
        }