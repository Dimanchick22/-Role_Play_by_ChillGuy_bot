"""Улучшенный реестр сервисов с лучшей архитектурой."""

import asyncio
import logging
import weakref
from abc import ABC, abstractmethod
from typing import Dict, Any, TypeVar, Type, Optional, Callable, Protocol
from enum import Enum

T = TypeVar('T')

logger = logging.getLogger(__name__)

class ServiceLifecycle(Enum):
    """Жизненный цикл сервиса."""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"

class IService(Protocol):
    """Интерфейс сервиса."""
    
    async def initialize(self) -> bool:
        """Инициализирует сервис."""
        ...
    
    async def cleanup(self) -> None:
        """Очищает ресурсы сервиса."""
        ...

class ServiceDescriptor:
    """Дескриптор сервиса с метаданными."""
    
    def __init__(self, name: str, service: Any, factory: Optional[Callable] = None):
        self.name = name
        self.service = service
        self.factory = factory
        self.lifecycle = ServiceLifecycle.CREATED
        self.dependencies: set[str] = set()
        self.dependents: set[str] = set()
        self.error: Optional[Exception] = None
    
    @property
    def is_ready(self) -> bool:
        return self.lifecycle == ServiceLifecycle.READY
    
    @property
    def has_error(self) -> bool:
        return self.lifecycle == ServiceLifecycle.ERROR

class DependencyResolver:
    """Резолвер зависимостей сервисов."""
    
    def __init__(self):
        self.dependencies: Dict[str, set[str]] = {}
    
    def add_dependency(self, service: str, depends_on: str) -> None:
        """Добавляет зависимость."""
        if service not in self.dependencies:
            self.dependencies[service] = set()
        self.dependencies[service].add(depends_on)
    
    def resolve_order(self, services: set[str]) -> list[str]:
        """Определяет порядок инициализации сервисов."""
        resolved = []
        unresolved = set(services)
        
        while unresolved:
            # Находим сервисы без нерешенных зависимостей
            ready = [
                service for service in unresolved
                if not (self.dependencies.get(service, set()) & unresolved)
            ]
            
            if not ready:
                # Циклическая зависимость
                raise ValueError(f"Циклическая зависимость: {unresolved}")
            
            resolved.extend(ready)
            unresolved -= set(ready)
        
        return resolved

class EnhancedServiceRegistry:
    """Улучшенный реестр сервисов."""
    
    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._dependency_resolver = DependencyResolver()
        self._initialization_lock = asyncio.Lock()
        self._weak_refs: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any, 
                depends_on: Optional[list[str]] = None) -> None:
        """Регистрирует сервис с зависимостями."""
        try:
            descriptor = ServiceDescriptor(name, service)
            self._services[name] = descriptor
            
            # Добавляем зависимости
            if depends_on:
                for dep in depends_on:
                    self._dependency_resolver.add_dependency(name, dep)
                    descriptor.dependencies.add(dep)
                    
                    # Обновляем обратные ссылки
                    if dep in self._services:
                        self._services[dep].dependents.add(name)
            
            logger.debug(f"✅ Зарегистрирован сервис: {name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации сервиса {name}: {e}")
            raise
    
    def register_factory(self, name: str, factory: Callable,
                        depends_on: Optional[list[str]] = None) -> None:
        """Регистрирует фабрику сервиса."""
        if not callable(factory):
            raise ValueError(f"Фабрика для {name} должна быть вызываемой")
        
        descriptor = ServiceDescriptor(name, None, factory)
        self._services[name] = descriptor
        
        if depends_on:
            for dep in depends_on:
                self._dependency_resolver.add_dependency(name, dep)
                descriptor.dependencies.add(dep)
        
        logger.debug(f"🏭 Зарегистрирована фабрика: {name}")
    
    async def initialize_all(self) -> bool:
        """Инициализирует все сервисы в правильном порядке."""
        async with self._initialization_lock:
            try:
                # Определяем порядок инициализации
                service_names = set(self._services.keys())
                init_order = self._dependency_resolver.resolve_order(service_names)
                
                logger.info(f"🔧 Инициализация {len(init_order)} сервисов...")
                
                success_count = 0
                for name in init_order:
                    try:
                        if await self._initialize_service(name):
                            success_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка инициализации {name}: {e}")
                        self._services[name].lifecycle = ServiceLifecycle.ERROR
                        self._services[name].error = e
                
                logger.info(f"✅ Инициализировано сервисов: {success_count}/{len(init_order)}")
                return success_count == len(init_order)
                
            except Exception as e:
                logger.error(f"❌ Ошибка массовой инициализации: {e}")
                return False
    
    async def _initialize_service(self, name: str) -> bool:
        """Инициализирует отдельный сервис."""
        descriptor = self._services[name]
        
        try:
            descriptor.lifecycle = ServiceLifecycle.INITIALIZING
            
            # Создаем сервис через фабрику если нужно
            if descriptor.service is None and descriptor.factory:
                descriptor.service = descriptor.factory()
            
            # Инициализируем если есть метод
            if hasattr(descriptor.service, 'initialize'):
                result = await descriptor.service.initialize()
                if not result:
                    descriptor.lifecycle = ServiceLifecycle.ERROR
                    return False
            
            descriptor.lifecycle = ServiceLifecycle.READY
            logger.debug(f"✅ Сервис {name} инициализирован")
            return True
            
        except Exception as e:
            descriptor.lifecycle = ServiceLifecycle.ERROR
            descriptor.error = e
            logger.error(f"❌ Ошибка инициализации {name}: {e}")
            return False
    
    def get(self, name: str, default: Any = None) -> Any:
        """Получает сервис с проверкой состояния."""
        try:
            if name not in self._services:
                if default is not None:
                    return default
                raise ValueError(f"Сервис '{name}' не найден")
            
            descriptor = self._services[name]
            
            if descriptor.has_error:
                logger.warning(f"⚠️ Сервис {name} в состоянии ошибки")
                if default is not None:
                    return default
                raise RuntimeError(f"Сервис '{name}' в состоянии ошибки")
            
            return descriptor.service
            
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
        """Проверяет наличие готового сервиса."""
        return (name in self._services and 
                self._services[name].is_ready)
    
    def get_service_status(self, name: str) -> Optional[ServiceLifecycle]:
        """Возвращает статус сервиса."""
        if name in self._services:
            return self._services[name].lifecycle
        return None
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Возвращает статус всего реестра."""
        status = {
            "total_services": len(self._services),
            "ready_services": sum(1 for s in self._services.values() if s.is_ready),
            "error_services": sum(1 for s in self._services.values() if s.has_error),
            "services": {}
        }
        
        for name, descriptor in self._services.items():
            status["services"][name] = {
                "lifecycle": descriptor.lifecycle.value,
                "dependencies": list(descriptor.dependencies),
                "dependents": list(descriptor.dependents),
                "error": str(descriptor.error) if descriptor.error else None
            }
        
        return status
    
    async def cleanup(self) -> None:
        """Очищает все сервисы в обратном порядке зависимостей."""
        logger.info("🧹 Очистка всех сервисов...")
        
        try:
            # Получаем порядок очистки (обратный к инициализации)
            service_names = [name for name in self._services.keys() 
                           if self._services[name].is_ready]
            
            if service_names:
                cleanup_order = list(reversed(
                    self._dependency_resolver.resolve_order(set(service_names))
                ))
                
                for name in cleanup_order:
                    await self._cleanup_service(name)
            
            self._services.clear()
            self._weak_refs.clear()
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки реестра: {e}")
    
    async def _cleanup_service(self, name: str) -> None:
        """Очищает отдельный сервис."""
        try:
            descriptor = self._services[name]
            descriptor.lifecycle = ServiceLifecycle.DESTROYING
            
            if hasattr(descriptor.service, 'cleanup'):
                cleanup_method = descriptor.service.cleanup
                # Проверяем, является ли метод async
                if asyncio.iscoroutinefunction(cleanup_method):
                    await cleanup_method()
                else:
                    # Синхронный метод - вызываем как обычно
                    cleanup_method()
            
            descriptor.lifecycle = ServiceLifecycle.DESTROYED
            logger.debug(f"🧹 Сервис {name} очищен")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка очистки сервиса {name}: {e}")

# Глобальный реестр
registry = EnhancedServiceRegistry()