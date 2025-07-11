"""Унифицированный инициализатор сервисов."""

import logging
from typing import Dict, Any, List

from config.settings import AppConfig
from core.registry import registry

logger = logging.getLogger(__name__)

class ServiceInitializer:
    """Унифицированный инициализатор всех сервисов."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.initialized_services: List[str] = []
    
    def initialize_all(self) -> bool:
        """Инициализирует все сервисы в правильном порядке."""
        logger.info("🔧 Начало инициализации сервисов...")
        
        # Порядок инициализации важен - сначала базовые сервисы
        services_to_init = [
            ('storage', self._init_storage_service),
            ('character', self._init_character_service),
            ('llm', self._init_llm_service),
            ('image', self._init_image_service),
            ('handlers', self._init_handlers)
        ]
        
        success_count = 0
        for service_name, init_func in services_to_init:
            try:
                if init_func():
                    self.initialized_services.append(service_name)
                    success_count += 1
                    logger.info(f"✅ Сервис '{service_name}' инициализирован")
                else:
                    logger.warning(f"⚠️ Сервис '{service_name}' не удалось инициализировать")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации '{service_name}': {e}")
        
        total_required = len([s for s in services_to_init if s[0] in ['storage', 'character', 'handlers']])
        required_success = len([s for s in self.initialized_services if s in ['storage', 'character', 'handlers']])
        
        logger.info(f"📊 Инициализировано сервисов: {success_count}/{len(services_to_init)}")
        
        return required_success == total_required
    
    def _init_storage_service(self) -> bool:
        """Инициализирует сервис хранилища."""
        try:
            from services.storage.memory_storage import MemoryStorage
            
            storage = MemoryStorage(
                max_conversations=self.config.storage.max_conversations
            )
            
            registry.register('storage', storage)
            logger.debug("💾 Сервис хранилища создан")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания хранилища: {e}")
            return False
    
    def _init_character_service(self) -> bool:
        """Инициализирует сервис персонажа."""
        try:
            from characters.alice import AliceCharacter
            
            character = AliceCharacter()
            registry.register('character', character)
            logger.debug("👩 Персонаж Алиса создан")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания персонажа: {e}")
            return False
    
    def _init_llm_service(self) -> bool:
        """Инициализирует LLM сервис."""
        if self.config.llm.provider == "none":
            logger.info("🧠 LLM сервис отключен в конфигурации")
            return True
        
        try:
            if self.config.llm.provider == "ollama":
                from services.llm.ollama_client import OllamaClient
                
                llm = OllamaClient(
                    model_name=self.config.llm.model_name,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens
                )
                
                # Проверяем доступность
                if llm.is_available:
                    registry.register('llm', llm)
                    logger.debug(f"🧠 LLM сервис создан: {getattr(llm, 'active_model', llm.model_name)}")
                    return True
                else:
                    logger.warning("⚠️ Ollama недоступна, бот будет работать без LLM")
                    return False
            
            else:
                logger.warning(f"❓ Неизвестный LLM провайдер: {self.config.llm.provider}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания LLM сервиса: {e}")
            return False
    
    def _init_image_service(self) -> bool:
        """Инициализирует сервис генерации изображений."""
        if not self.config.image.enabled:
            logger.info("🎨 Генерация изображений отключена в конфигурации")
            return True
        
        try:
            if self.config.image.provider == "stable_diffusion":
                # Пока что только заглушка, т.к. требует async инициализации
                logger.warning("🎨 Генерация изображений требует async инициализации (отложена)")
                return True
            else:
                logger.warning(f"❓ Неизвестный провайдер изображений: {self.config.image.provider}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервиса изображений: {e}")
            return False
    
    def _init_handlers(self) -> bool:
        """Инициализирует обработчики сообщений."""
        try:
            from handlers.command_handlers import CommandHandlers
            from handlers.message_handlers import MessageHandlers
            
            command_handlers = CommandHandlers()
            message_handlers = MessageHandlers()
            
            registry.register('command_handlers', command_handlers)
            registry.register('message_handlers', message_handlers)
            
            logger.debug("📝 Обработчики созданы")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания обработчиков: {e}")
            return False
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Возвращает отчет об инициализации."""
        return {
            "initialized_services": self.initialized_services,
            "total_services": 5,  # storage, character, llm, image, handlers
            "success_rate": len(self.initialized_services) / 5,
            "registry_services": registry.get_registered_services()
        }
    
    def cleanup(self) -> None:
        """Очищает инициализированные сервисы."""
        logger.info("🧹 Очистка сервисов...")
        
        for service_name in reversed(self.initialized_services):
            try:
                service = registry.get(service_name, None)
                if service and hasattr(service, 'cleanup'):
                    service.cleanup()
                logger.debug(f"✅ Сервис {service_name} очищен")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка очистки сервиса {service_name}: {e}")
        
        self.initialized_services.clear()