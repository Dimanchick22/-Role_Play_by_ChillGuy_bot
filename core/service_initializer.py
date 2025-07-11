"""Улучшенный инициализатор сервисов с поддержкой локальных моделей."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Callable
from abc import ABC, abstractmethod

from config.settings import AppConfig
from core.registry import registry

logger = logging.getLogger(__name__)

class ServiceFactory(ABC):
    """Абстрактная фабрика сервисов."""
    
    @abstractmethod
    def create_service(self, config: AppConfig) -> Any:
        """Создает сервис."""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Возвращает зависимости сервиса."""
        pass
    
    @abstractmethod
    def is_required(self, config: AppConfig) -> bool:
        """Определяет, является ли сервис обязательным."""
        pass

class StorageServiceFactory(ServiceFactory):
    """Фабрика для создания сервиса хранилища."""
    
    def create_service(self, config: AppConfig) -> Any:
        from services.storage.memory_storage import MemoryStorage
        return MemoryStorage(max_conversations=config.storage.max_conversations)
    
    def get_dependencies(self) -> List[str]:
        return []  # Нет зависимостей
    
    def is_required(self, config: AppConfig) -> bool:
        return True  # Всегда требуется

class CharacterServiceFactory(ServiceFactory):
    """Фабрика для создания сервиса персонажа."""
    
    def create_service(self, config: AppConfig) -> Any:
        from characters.alice import AliceCharacter
        return AliceCharacter()
    
    def get_dependencies(self) -> List[str]:
        return []  # Нет зависимостей
    
    def is_required(self, config: AppConfig) -> bool:
        return True  # Всегда требуется

class LLMServiceFactory(ServiceFactory):
    """Фабрика для создания LLM сервиса."""
    
    def create_service(self, config: AppConfig) -> Any:
        if config.llm.provider == "ollama":
            from services.llm.ollama_client import OllamaClient
            
            llm = OllamaClient(
                model_name=config.llm.model_name,
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens
            )
            
            # Проверяем доступность
            if not llm.is_available:
                logger.warning("⚠️ Ollama недоступна")
                return None
            
            return llm
        else:
            logger.warning(f"❓ Неизвестный LLM провайдер: {config.llm.provider}")
            return None
    
    def get_dependencies(self) -> List[str]:
        return ['character']  # Зависит от персонажа для системного промпта
    
    def is_required(self, config: AppConfig) -> bool:
        return config.llm.provider != "none"

class ImageServiceFactory(ServiceFactory):
    """Фабрика для создания сервиса изображений с поддержкой локальных моделей."""
    
    def create_service(self, config: AppConfig) -> Any:
        if config.image.provider == "stable_diffusion":
            model_path = config.image.model_path
            
            # Проверяем, локальная ли модель
            is_local_model = (
                model_path.endswith('.safetensors') or 
                model_path.endswith('.ckpt') or 
                model_path.startswith('./') or 
                model_path.startswith('../') or
                model_path.startswith('/') or
                (len(model_path) > 1 and model_path[1] == ':')  # Windows путь типа C:\
            )
            
            if is_local_model:
                logger.info(f"🎯 Обнаружена локальная модель: {model_path}")
                
                # Проверяем существование файла
                if model_path.startswith('./'):
                    full_path = Path(model_path).resolve()
                else:
                    full_path = Path(model_path)
                
                if not full_path.exists():
                    logger.error(f"❌ Локальная модель не найдена: {full_path}")
                    logger.info("🔄 Используем fallback модель")
                    model_path = "runwayml/stable-diffusion-v1-5"
                    is_local_model = False
                else:
                    logger.info(f"✅ Локальная модель найдена: {full_path}")
                    model_path = str(full_path)
            
            # Выбираем подходящий генератор
            if is_local_model:
                from services.image.stable_diffusion import LocalStableDiffusionGenerator
                return LocalStableDiffusionGenerator(
                    model_path=model_path,
                    output_dir=config.image.output_dir,
                    safety_check=config.image.safety_check
                )
            else:
                from services.image.stable_diffusion import StableDiffusionGenerator
                return StableDiffusionGenerator(
                    model_path=model_path,
                    output_dir=config.image.output_dir,
                    safety_check=config.image.safety_check
                )
        else:
            logger.warning(f"❓ Неизвестный провайдер изображений: {config.image.provider}")
            return None
    
    def get_dependencies(self) -> List[str]:
        return []  # Нет зависимостей
    
    def is_required(self, config: AppConfig) -> bool:
        return config.image.enabled

class HandlerServiceFactory(ServiceFactory):
    """Фабрика для создания обработчиков."""
    
    def create_service(self, config: AppConfig) -> Dict[str, Any]:
        from handlers.command_handlers import CommandHandlers
        from handlers.message_handlers import MessageHandlers
        
        return {
            'command_handlers': CommandHandlers(),
            'message_handlers': MessageHandlers()
        }
    
    def get_dependencies(self) -> List[str]:
        return ['storage', 'character']  # Зависят от хранилища и персонажа
    
    def is_required(self, config: AppConfig) -> bool:
        return True  # Всегда требуются

class ImprovedServiceInitializer:
    """Улучшенный инициализатор сервисов с использованием фабрик."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.factories: Dict[str, ServiceFactory] = {
            'storage': StorageServiceFactory(),
            'character': CharacterServiceFactory(),
            'llm': LLMServiceFactory(),
            'image': ImageServiceFactory(),
            'handlers': HandlerServiceFactory()
        }
        self.initialized_services: List[str] = []
    
    async def initialize_all(self) -> bool:
        """Инициализирует все сервисы через фабрики."""
        logger.info("🔧 Начало инициализации сервисов через фабрики...")
        
        try:
            # Регистрируем все сервисы с их зависимостями
            self._register_all_services()
            
            # Инициализируем все сервисы в правильном порядке
            success = await registry.initialize_all()
            
            # Получаем статистику
            status = registry.get_registry_status()
            self.initialized_services = [
                name for name, info in status["services"].items() 
                if info["lifecycle"] == "ready"
            ]
            
            logger.info(f"📊 Инициализировано сервисов: {len(self.initialized_services)}")
            
            # Проверяем обязательные сервисы
            required_services = [
                name for name, factory in self.factories.items()
                if factory.is_required(self.config)
            ]
            
            missing_required = [
                name for name in required_services
                if name not in self.initialized_services
            ]
            
            if missing_required:
                logger.error(f"❌ Отсутствуют обязательные сервисы: {missing_required}")
                return False
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации сервисов: {e}")
            return False
    
    def _register_all_services(self) -> None:
        """Регистрирует все сервисы в реестре."""
        for service_name, factory in self.factories.items():
            try:
                # Создаем фабричную функцию
                def create_service(factory=factory):
                    service = factory.create_service(self.config)
                    if service is None:
                        raise RuntimeError(f"Фабрика вернула None для {service_name}")
                    
                    # Если это словарь сервисов (как handlers), регистрируем каждый отдельно
                    if isinstance(service, dict):
                        for sub_name, sub_service in service.items():
                            registry.register(sub_name, sub_service)
                        return service
                    
                    return service
                
                # Регистрируем фабрику с зависимостями
                dependencies = factory.get_dependencies()
                
                # Особая обработка для handlers (регистрируем каждый отдельно)
                if service_name == 'handlers':
                    def create_handlers(factory=factory):
                        handlers_dict = factory.create_service(self.config)
                        if not isinstance(handlers_dict, dict):
                            raise RuntimeError(f"Handlers factory должна возвращать dict")
                        
                        # Регистрируем каждый обработчик отдельно
                        for handler_name, handler_instance in handlers_dict.items():
                            registry.register(handler_name, handler_instance)
                        
                        return handlers_dict
                    
                    registry.register_factory(service_name, create_handlers, dependencies)
                else:
                    # Для остальных сервисов используем обычные фабрики
                    registry.register_factory(service_name, create_service, dependencies)
                
                logger.debug(f"📋 Зарегистрирована фабрика {service_name}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка регистрации фабрики {service_name}: {e}")
                raise
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Возвращает детальный отчет об инициализации."""
        registry_status = registry.get_registry_status()
        
        required_services = [
            name for name, factory in self.factories.items()
            if factory.is_required(self.config)
        ]
        
        optional_services = [
            name for name, factory in self.factories.items()
            if not factory.is_required(self.config)
        ]
        
        return {
            "initialized_services": self.initialized_services,
            "required_services": required_services,
            "optional_services": optional_services,
            "registry_status": registry_status,
            "success_rate": registry_status["ready_services"] / registry_status["total_services"] if registry_status["total_services"] > 0 else 0,
            "all_required_ready": all(
                name in self.initialized_services 
                for name in required_services
            )
        }
    
    async def cleanup(self) -> None:
        """Очищает все инициализированные сервисы."""
        logger.info("🧹 Очистка сервисов через улучшенный инициализатор...")
        await registry.cleanup()
        self.initialized_services.clear()


# === РОЛЬ-ПЛЕЙ ФАБРИКИ ===

class RoleplayCharacterServiceFactory(ServiceFactory):
    """Фабрика для создания роль-плей персонажа."""
    
    def create_service(self, config: AppConfig) -> Any:
        from characters.alice import RoleplayAliceCharacter
        return RoleplayAliceCharacter()
    
    def get_dependencies(self) -> List[str]:
        return []
    
    def is_required(self, config: AppConfig) -> bool:
        return True

class RoleplayLLMServiceFactory(ServiceFactory):
    """Фабрика для создания роль-плей LLM сервиса."""
    
    def create_service(self, config: AppConfig) -> Any:
        if config.llm.provider == "ollama":
            from services.llm.ollama_client import RoleplayOllamaClient
            
            llm = RoleplayOllamaClient(
                model_name=config.llm.model_name,
                temperature=max(config.llm.temperature, 0.7),  # Минимум 0.7 для роль-плея
                max_tokens=max(config.llm.max_tokens, 250)     # Минимум 250 токенов
            )
            
            if not llm.is_available:
                logger.warning("⚠️ Roleplay Ollama недоступна")
                return None
            
            return llm
        else:
            logger.warning(f"❓ Неизвестный LLM провайдер для роль-плея: {config.llm.provider}")
            return None
    
    def get_dependencies(self) -> List[str]:
        return ['character']
    
    def is_required(self, config: AppConfig) -> bool:
        return config.llm.provider != "none"

class RoleplayImageServiceFactory(ServiceFactory):
    """Фабрика для создания роль-плей сервиса изображений с поддержкой локальных моделей."""
    
    def create_service(self, config: AppConfig) -> Any:
        if config.image.provider == "stable_diffusion":
            model_path = config.image.model_path
            
            # Проверяем, локальная ли модель
            is_local_model = (
                model_path.endswith('.safetensors') or 
                model_path.endswith('.ckpt') or 
                model_path.startswith('./') or 
                model_path.startswith('../') or
                model_path.startswith('/') or
                (len(model_path) > 1 and model_path[1] == ':')  # Windows путь типа C:\
            )
            
            if is_local_model:
                logger.info(f"🎯 Обнаружена локальная роль-плей модель: {model_path}")
                
                # Проверяем существование файла
                if model_path.startswith('./'):
                    full_path = Path(model_path).resolve()
                else:
                    full_path = Path(model_path)
                
                if not full_path.exists():
                    logger.error(f"❌ Локальная модель не найдена: {full_path}")
                    logger.info("🔄 Используем fallback модель")
                    model_path = "runwayml/stable-diffusion-v1-5"
                    is_local_model = False
                else:
                    logger.info(f"✅ Локальная роль-плей модель найдена: {full_path}")
                    model_path = str(full_path)
            
            # Выбираем подходящий генератор
            if is_local_model:
                from services.image.stable_diffusion import LocalStableDiffusionGenerator
                return LocalStableDiffusionGenerator(
                    model_path=model_path,
                    output_dir=config.image.output_dir,
                    safety_check=config.image.safety_check
                )
            else:
                from services.image.stable_diffusion import StableDiffusionGenerator
                return StableDiffusionGenerator(
                    model_path=model_path,
                    output_dir=config.image.output_dir,
                    safety_check=config.image.safety_check
                )
        else:
            logger.warning(f"❓ Неизвестный провайдер изображений: {config.image.provider}")
            return None
    
    def get_dependencies(self) -> List[str]:
        return []
    
    def is_required(self, config: AppConfig) -> bool:
        return config.image.enabled

class RoleplayHandlerServiceFactory(ServiceFactory):
    """Фабрика для создания роль-плей обработчиков."""
    
    def create_service(self, config: AppConfig) -> Dict[str, Any]:
        from handlers.command_handlers import CommandHandlers
        from handlers.message_handlers import RoleplayMessageHandlers
        
        return {
            'command_handlers': CommandHandlers(),
            'message_handlers': RoleplayMessageHandlers()
        }
    
    def get_dependencies(self) -> List[str]:
        return ['storage', 'character']
    
    def is_required(self, config: AppConfig) -> bool:
        return True

class RoleplayServiceInitializer:
    """Инициализатор сервисов для роль-плея."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.factories: Dict[str, ServiceFactory] = {
            'storage': StorageServiceFactory(),
            'character': RoleplayCharacterServiceFactory(),    # Роль-плей персонаж
            'llm': RoleplayLLMServiceFactory(),               # Роль-плей LLM
            'image': RoleplayImageServiceFactory(),           # Роль-плей изображения с локальными моделями
            'handlers': RoleplayHandlerServiceFactory()       # Роль-плей обработчики
        }
        self.initialized_services: List[str] = []
    
    async def initialize_all(self) -> bool:
        """Инициализирует все сервисы для роль-плея."""
        logger.info("🎭 Начало инициализации роль-плей сервисов...")
        
        try:
            # Регистрируем все сервисы
            self._register_all_services()
            
            # Инициализируем
            success = await registry.initialize_all()
            
            # Получаем статистику
            status = registry.get_registry_status()
            self.initialized_services = [
                name for name, info in status["services"].items() 
                if info["lifecycle"] == "ready"
            ]
            
            logger.info(f"🎭 Инициализировано роль-плей сервисов: {len(self.initialized_services)}")
            
            # Специальная проверка для роль-плея
            self._validate_roleplay_setup()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации роль-плей сервисов: {e}")
            return False
    
    def _validate_roleplay_setup(self):
        """Валидирует настройку роль-плея."""
        character = registry.get('character', None)
        llm = registry.get('llm', None)
        image = registry.get('image', None)
        
        logger.info("🎭 Проверка роль-плей настроек:")
        
        # Персонаж
        if character and hasattr(character, 'get_template_response'):
            logger.info("  ✅ Роль-плей персонаж готов")
        else:
            logger.warning("  ⚠️ Роль-плей персонаж не готов")
        
        # LLM
        if llm and hasattr(llm, 'roleplay_settings'):
            temp = llm.roleplay_settings.get('temperature', 0)
            logger.info(f"  ✅ Роль-плей LLM готов (temperature: {temp})")
        else:
            logger.warning("  ⚠️ Роль-плей LLM не готов, работаем на шаблонах")
        
        # Изображения
        if image and hasattr(image, 'is_initialized') and image.is_initialized:
            model_info = getattr(image, 'model_path', 'неизвестно')
            if 'oneObsession' in model_info or 'one-obsession' in model_info:
                logger.info(f"  ✅ Локальная модель One Obsession готова: {model_info}")
            else:
                logger.info(f"  ✅ Генерация изображений готова: {model_info}")
        else:
            logger.warning("  ⚠️ Генерация изображений недоступна")
    
    def _register_all_services(self):
        """Регистрирует все роль-плей сервисы."""
        for service_name, factory in self.factories.items():
            try:
                def create_service(factory=factory):
                    service = factory.create_service(self.config)
                    if service is None and factory.is_required(self.config):
                        raise RuntimeError(f"Обязательный сервис {service_name} не создан")
                    
                    if isinstance(service, dict):
                        for sub_name, sub_service in service.items():
                            registry.register(sub_name, sub_service)
                        return service
                    
                    return service
                
                dependencies = factory.get_dependencies()
                
                if service_name == 'handlers':
                    def create_handlers(factory=factory):
                        handlers_dict = factory.create_service(self.config)
                        for handler_name, handler_instance in handlers_dict.items():
                            registry.register(handler_name, handler_instance)
                        return handlers_dict
                    
                    registry.register_factory(service_name, create_handlers, dependencies)
                else:
                    registry.register_factory(service_name, create_service, dependencies)
                
                logger.debug(f"🎭 Зарегистрирована роль-плей фабрика {service_name}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка регистрации роль-плей фабрики {service_name}: {e}")
                raise
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Возвращает детальный отчет об инициализации роль-плея."""
        registry_status = registry.get_registry_status()
        
        required_services = [
            name for name, factory in self.factories.items()
            if factory.is_required(self.config)
        ]
        
        optional_services = [
            name for name, factory in self.factories.items()
            if not factory.is_required(self.config)
        ]
        
        return {
            "initialized_services": self.initialized_services,
            "required_services": required_services,
            "optional_services": optional_services,
            "registry_status": registry_status,
            "success_rate": registry_status["ready_services"] / registry_status["total_services"] if registry_status["total_services"] > 0 else 0,
            "all_required_ready": all(
                name in self.initialized_services 
                for name in required_services
            )
        }
    
    async def cleanup(self) -> None:
        """Очищает все инициализированные роль-плей сервисы."""
        logger.info("🧹 Очистка роль-плей сервисов...")
        await registry.cleanup()
        self.initialized_services.clear()


# Утилиты для работы с конкретными сервисами
class ServiceUtils:
    """Утилиты для работы с сервисами."""
    
    @staticmethod
    def get_llm_service():
        """Получает LLM сервис если доступен."""
        try:
            return registry.get('llm')
        except Exception:
            return None
    
    @staticmethod
    def get_storage_service():
        """Получает сервис хранилища."""
        return registry.get('storage')
    
    @staticmethod
    def get_character_service():
        """Получает сервис персонажа."""
        return registry.get('character')
    
    @staticmethod
    def get_image_service():
        """Получает сервис изображений если доступен."""
        try:
            return registry.get('image')
        except Exception:
            return None
    
    @staticmethod
    def is_llm_available() -> bool:
        """Проверяет доступность LLM."""
        llm = ServiceUtils.get_llm_service()
        return llm is not None and getattr(llm, 'is_available', False)
    
    @staticmethod
    def is_image_generation_available() -> bool:
        """Проверяет доступность генерации изображений."""
        image_service = ServiceUtils.get_image_service()
        return image_service is not None and getattr(image_service, 'is_initialized', False)
    
    @staticmethod
    def get_service_health() -> Dict[str, bool]:
        """Возвращает состояние здоровья всех сервисов."""
        return {
            "storage": registry.has('storage'),
            "character": registry.has('character'),
            "llm": ServiceUtils.is_llm_available(),
            "image": ServiceUtils.is_image_generation_available(),
            "command_handlers": registry.has('command_handlers'),
            "message_handlers": registry.has('message_handlers')
        }