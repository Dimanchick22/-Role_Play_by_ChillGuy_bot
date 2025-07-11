"""Базовый LLM клиент."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from models.base import BaseMessage, User, Conversation

logger = logging.getLogger(__name__)

class BaseLLMClient(ABC):
    """Базовый класс для LLM клиентов."""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs
        self.is_available = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Инициализирует клиент."""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[BaseMessage], 
        user: User,
        **kwargs
    ) -> str:
        """Генерирует ответ."""
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """Проверяет состояние сервиса."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Возвращает доступные модели."""
        pass
    
    async def set_model(self, model_name: str) -> bool:
        """Меняет модель."""
        old_model = self.model_name
        self.model_name = model_name
        
        try:
            success = await self.initialize()
            if success:
                logger.info(f"Модель изменена: {old_model} -> {model_name}")
                return True
            else:
                self.model_name = old_model
                return False
        except Exception as e:
            logger.error(f"Ошибка смены модели: {e}")
            self.model_name = old_model
            return False