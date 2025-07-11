"""Фабрика для создания сервисов бота."""

import logging
from typing import Dict, Any

from config.settings import AppConfig
from core.registry import registry

logger = logging.getLogger(__name__)

class BotFactory:
    """Фабрика для создания и настройки сервисов."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.created_services: Dict[str, Any] = {}
    
    async def create_services(self) -> None:
        """Создает все необходимые сервисы."""
        logger.info("🔧 Создание сервисов...")
        
        # Хранилище (всегда нужно)
        await self._create_storage_service()
        
        # Персонаж (всегда нужен)
        await self._create_character_service()
        
        # LLM сервис (опционально)
        if self.config.llm.provider != "none":
            await self._create_llm_service()
        
        # Сервис изображений (опционально)
        if self.config.image.enabled:
            await self._create_image_service()
        
        # Обработчики (всегда нужны)
        await self._create_handlers()
        
        logger.info(f"✅ Создано сервисов: {len(self.created_services)}")
    
    async def _create_storage_service(self) -> None:
        """Создает сервис хранилища."""
        try:
            from services.storage.memory_storage import MemoryStorage
            
            storage = MemoryStorage(
                max_conversations=self.config.storage.max_conversations
            )
            
            registry.register('storage', storage)
            self.created_services['storage'] = storage
            
            logger.info("💾 Сервис хранилища создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания хранилища: {e}")
            raise
    
    async def _create_character_service(self) -> None:
        """Создает сервис персонажа."""
        try:
            from characters.alice import AliceCharacter
            
            character = AliceCharacter()
            
            registry.register('character', character)
            self.created_services['character'] = character
            
            logger.info("👩 Персонаж Алиса создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания персонажа: {e}")
            raise
    
    async def _create_llm_service(self) -> None:
        """Создает LLM сервис."""
        try:
            if self.config.llm.provider == "ollama":
                from services.llm.ollama_client import OllamaClient
                
                llm = OllamaClient(
                    model_name=self.config.llm.model_name,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens
                )
                
                # Инициализируем
                if await llm.initialize():
                    registry.register('llm', llm)
                    self.created_services['llm'] = llm
                    logger.info(f"🧠 LLM сервис создан: {llm.model_name}")
                else:
                    logger.warning("⚠️ LLM сервис не удалось инициализировать")
            
            else:
                logger.warning(f"❓ Неизвестный LLM провайдер: {self.config.llm.provider}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания LLM сервиса: {e}")
            # Не падаем, бот может работать без LLM
    
    async def _create_image_service(self) -> None:
        """Создает сервис генерации изображений."""
        try:
            if self.config.image.provider == "stable_diffusion":
                from services.image.stable_diffusion import StableDiffusionGenerator
                
                image_generator = StableDiffusionGenerator(
                    model_path=self.config.image.model_path,
                    output_dir=self.config.image.output_dir,
                    safety_check=self.config.image.safety_check
                )
                
                # Инициализируем в фоне (может быть долго)
                if await image_generator.initialize():
                    registry.register('image', image_generator)
                    self.created_services['image'] = image_generator
                    logger.info(f"🎨 Сервис изображений создан: {image_generator.model_path}")
                else:
                    logger.warning("⚠️ Сервис изображений не удалось инициализировать")
            
            else:
                logger.warning(f"❓ Неизвестный провайдер изображений: {self.config.image.provider}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервиса изображений: {e}")
            # Не падаем, бот может работать без генерации изображений
    
    async def _create_handlers(self) -> None:
        """Создает обработчики сообщений."""
        try:
            from handlers.command_handlers import CommandHandlers
            from handlers.message_handlers import MessageHandlers
            
            command_handlers = CommandHandlers()
            message_handlers = MessageHandlers()
            
            registry.register('command_handlers', command_handlers)
            registry.register('message_handlers', message_handlers)
            
            self.created_services['command_handlers'] = command_handlers
            self.created_services['message_handlers'] = message_handlers
            
            logger.info("📝 Обработчики созданы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания обработчиков: {e}")
            raise
    
    async def cleanup_services(self) -> None:
        """Очищает ресурсы сервисов."""
        logger.info("🧹 Очистка сервисов...")
        
        for name, service in self.created_services.items():
            try:
                # Если у сервиса есть метод cleanup, вызываем его
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                logger.debug(f"✅ Сервис {name} очищен")
            except Exception as e:
                logger.error(f"❌ Ошибка очистки сервиса {name}: {e}")
        
        self.created_services.clear()
        registry.clear()