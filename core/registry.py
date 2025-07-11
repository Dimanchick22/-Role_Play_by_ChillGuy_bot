"""Реестр сервисов для dependency injection - улучшенная версия."""

from typing import Dict, Any, TypeVar, Type, Optional, Callable
import logging
import weakref

T = TypeVar('T')

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Реестр сервисов с улучшенной обработкой ошибок."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._weak_refs: Dict[str, Any] = {}
        self._initialized = True
    
    def register(self, name: str, service: Any) -> None:
        """Регистрирует сервис."""
        try:
            self._services[name] = service
            logger.debug(f"✅ Зарегистрирован сервис: {name}")
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации сервиса {name}: {e}")
            raise
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """Регистрирует фабрику сервиса."""
        if not callable(factory):
            raise ValueError(f"Фабрика для {name} должна быть вызываемой")
        
        self._factories[name] = factory
        logger.debug(f"🏭 Зарегистрирована фабрика: {name}")
    
    def register_singleton(self, name: str, factory: Callable) -> None:
        """Регистрирует синглтон."""
        if not callable(factory):
            raise ValueError(f"Фабрика синглтона для {name} должна быть вызываемой")
        
        self._factories[name] = factory
        # Помечаем как синглтон (используем None как маркер)
        self._singletons[name] = None
        logger.debug(f"🔒 Зарегистрирован синглтон: {name}")
    
    def get(self, name: str, default: Any = None) -> Any:
        """Получает сервис с безопасной обработкой ошибок."""
        try:
            # Проверяем готовые сервисы
            if name in self._services:
                return self._services[name]
            
            # Проверяем созданные синглтоны
            if name in self._singletons and self._singletons[name] is not None:
                return self._singletons[name]
            
            # Создаем через фабрику
            if name in self._factories:
                try:
                    service = self._factories[name]()
                    
                    # Если это синглтон, сохраняем
                    if name in self._singletons:
                        self._singletons[name] = service
                        logger.debug(f"🔒 Создан синглтон: {name}")
                    else:
                        logger.debug(f"🏭 Создан сервис через фабрику: {name}")
                    
                    return service
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка создания сервиса {name}: {e}")
                    if default is not None:
                        return default
                    raise
            
            # Сервис не найден
            if default is not None:
                logger.warning(f"⚠️ Сервис '{name}' не найден, возвращаю значение по умолчанию")
                return default
            
            raise ValueError(f"Сервис '{name}' не найден в реестре")
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сервиса {name}: {e}")
            if default is not None:
                return default
            raise
    
    def get_typed(self, service_type: Type[T]) -> Optional[T]:
        """Получает сервис по типу."""
        name = service_type.__name__.lower()
        try:
            return self.get(name)
        except Exception:
            logger.warning(f"⚠️ Сервис типа {service_type.__name__} не найден")
            return None
    
    def has(self, name: str) -> bool:
        """Проверяет наличие сервиса."""
        return (name in self._services or 
                name in self._factories or 
                (name in self._singletons and self._singletons[name] is not None))
    
    def get_registered_services(self) -> Dict[str, str]:
        """Возвращает список зарегистрированных сервисов."""
        services_info = {}
        
        for name in self._services:
            services_info[name] = "ready"
        
        for name in self._factories:
            if name in self._singletons:
                status = "singleton_created" if self._singletons[name] is not None else "singleton_factory"
            else:
                status = "factory"
            services_info[name] = status
        
        return services_info
    
    def clear(self) -> None:
        """Очищает реестр с безопасной очисткой ресурсов."""
        try:
            logger.debug("🧹 Очистка реестра сервисов...")
            
            # Очищаем синглтоны первыми (у них могут быть зависимости)
            for name, service in self._singletons.items():
                if service is not None and hasattr(service, 'cleanup'):
                    try:
                        service.cleanup()
                        logger.debug(f"🧹 Очищен синглтон: {name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка очистки синглтона {name}: {e}")
            
            # Очищаем обычные сервисы
            for name, service in self._services.items():
                if hasattr(service, 'cleanup'):
                    try:
                        service.cleanup()
                        logger.debug(f"🧹 Очищен сервис: {name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка очистки сервиса {name}: {e}")
            
            # Очищаем коллекции
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self._weak_refs.clear()
            
            logger.debug("✅ Реестр очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки реестра: {e}")
    
    def __del__(self):
        """Деструктор для автоматической очистки."""
        if hasattr(self, '_initialized') and self._initialized:
            try:
                self.clear()
            except:
                pass  # Игнорируем ошибки при уничтожении

# Глобальный реестр
registry = ServiceRegistry()