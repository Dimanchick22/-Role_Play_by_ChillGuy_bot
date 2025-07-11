"""Реестр сервисов для dependency injection."""

from typing import Dict, Any, TypeVar, Type, Optional
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Реестр сервисов."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Регистрирует сервис."""
        self._services[name] = service
        logger.debug(f"Зарегистрирован сервис: {name}")
    
    def register_factory(self, name: str, factory: callable) -> None:
        """Регистрирует фабрику сервиса."""
        self._factories[name] = factory
        logger.debug(f"Зарегистрирована фабрика: {name}")
    
    def register_singleton(self, name: str, factory: callable) -> None:
        """Регистрирует синглтон."""
        self._factories[name] = factory
        logger.debug(f"Зарегистрирован синглтон: {name}")
    
    def get(self, name: str) -> Any:
        """Получает сервис."""
        # Проверяем готовые сервисы
        if name in self._services:
            return self._services[name]
        
        # Проверяем синглтоны
        if name in self._singletons:
            return self._singletons[name]
        
        # Создаем через фабрику
        if name in self._factories:
            service = self._factories[name]()
            
            # Если это синглтон, сохраняем
            if name in self._singletons:
                self._singletons[name] = service
            
            return service
        
        raise ValueError(f"Сервис '{name}' не найден")
    
    def get_typed(self, service_type: Type[T]) -> T:
        """Получает сервис по типу."""
        name = service_type.__name__.lower()
        return self.get(name)
    
    def clear(self) -> None:
        """Очищает реестр."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()

# Глобальный реестр
registry = ServiceRegistry()