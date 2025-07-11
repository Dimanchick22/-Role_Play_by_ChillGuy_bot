"""Ollama LLM клиент - исправленная версия с правильной async обработкой."""

import asyncio
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

try:
    import ollama
except ImportError:
    logging.error("❌ Библиотека ollama не установлена. Установите: pip install ollama")
    ollama = None

from services.llm.base_client import BaseLLMClient
from models.base import BaseMessage, User

logger = logging.getLogger(__name__)

class OllamaClient(BaseLLMClient):
    """Клиент для Ollama с правильной async обработкой."""
    
    def __init__(self, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        self.is_available = False
        self.active_model = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ollama")
        
        # Проверяем доступность при создании
        self._check_availability()
    
    def _check_availability(self) -> None:
        """Проверяет доступность Ollama синхронно при инициализации."""
        if ollama is None:
            logger.warning("⚠️ Ollama библиотека недоступна")
            return
            
        try:
            models = ollama.list()
            available_models = self._get_available_models_sync()
            
            # Автовыбор модели
            if self.model_name == "auto":
                self.active_model = self._select_best_model(available_models)
            else:
                self.active_model = self.model_name
            
            # Проверяем выбранную модель
            if self.active_model in available_models:
                self.is_available = True
                logger.info(f"✅ Ollama клиент готов с моделью {self.active_model}")
            else:
                logger.warning(f"⚠️ Модель {self.active_model} недоступна")
                
        except Exception as e:
            logger.warning(f"⚠️ Ollama недоступна: {e}")
    
    async def initialize(self) -> bool:
        """Асинхронная инициализация (переинициализация)."""
        try:
            # Выполняем проверку в executor чтобы не блокировать event loop
            await asyncio.get_event_loop().run_in_executor(
                self._executor, self._check_availability
            )
            return self.is_available
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False
    
    async def generate_response(
        self, 
        messages: List[BaseMessage], 
        user: User,
        **kwargs
    ) -> str:
        """Генерирует ответ через Ollama асинхронно."""
        if not self.is_available or ollama is None:
            raise RuntimeError("Ollama клиент недоступен")
            
        try:
            # Преобразуем сообщения в формат Ollama
            ollama_messages = self._convert_messages(messages, user)
            
            logger.debug(f"Отправляем {len(ollama_messages)} сообщений в Ollama")
            
            # ПРАВИЛЬНО: выполняем синхронный вызов в executor
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._call_ollama_sync, ollama_messages
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            raise
    
    async def check_health(self) -> bool:
        """Проверяет состояние Ollama асинхронно."""
        if ollama is None:
            return False
            
        try:
            # Выполняем проверку в executor
            await asyncio.get_event_loop().run_in_executor(
                self._executor, ollama.list
            )
            return True
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """Возвращает доступные модели (может быть вызван синхронно)."""
        return self._get_available_models_sync()
    
    def _get_available_models_sync(self) -> List[str]:
        """Синхронное получение доступных моделей."""
        if ollama is None:
            return []
            
        try:
            models_response = ollama.list()
            
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict):
                models_list = models_response.get('models', [])
            else:
                return []
            
            models = []
            for model in models_list:
                if hasattr(model, 'model'):
                    models.append(model.model)
                elif isinstance(model, dict):
                    models.append(model.get('model', ''))
                elif hasattr(model, 'name'):
                    models.append(model.name)
            
            return [m for m in models if m]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения моделей: {e}")
            return []
    
    def _select_best_model(self, available: List[str]) -> str:
        """Выбирает лучшую доступную модель."""
        preferred = [
            'llama3.2:3b', 'llama3.2:1b', 'llama3.2',
            'mistral:7b', 'mistral', 'qwen2.5:7b'
        ]
        
        for pref in preferred:
            for model in available:
                if pref.lower() in model.lower():
                    logger.info(f"🎯 Выбрана модель: {model}")
                    return model
        
        if available:
            logger.info(f"🎯 Выбрана первая доступная модель: {available[0]}")
            return available[0]
        
        logger.warning("⚠️ Нет доступных моделей, используем fallback")
        return "llama3.2:3b"
    
    def _convert_messages(self, messages: List[BaseMessage], user: User) -> List[Dict]:
        """Преобразует сообщения в формат Ollama."""
        ollama_messages = []
        
        # Получаем персонажа для системного промпта
        try:
            from core.registry import registry
            character_service = registry.get('character', None)
        except Exception:
            character_service = None
        
        # Добавляем системный промпт
        if character_service and hasattr(character_service, 'get_system_prompt'):
            system_prompt = character_service.get_system_prompt(user)
            ollama_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Добавляем сообщения пользователя (только последние 5 для экономии токенов)
        for msg in messages[-5:]:
            ollama_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return ollama_messages
    
    def _call_ollama_sync(self, messages: List[Dict]) -> str:
        """СИНХРОННЫЙ вызов Ollama API - выполняется в отдельном потоке."""
        try:
            logger.debug(f"Вызов Ollama с моделью {self.active_model}")
            
            # Пробуем chat API (предпочтительный способ)
            response = ollama.chat(
                model=self.active_model,
                messages=messages,
                options={
                    'temperature': self.config.get('temperature', 0.7),
                    'num_predict': self.config.get('max_tokens', 200),
                    'top_p': 0.9,
                    'top_k': 40
                }
            )
            
            if 'message' in response and 'content' in response['message']:
                return response['message']['content']
            else:
                logger.error(f"Неожиданный формат ответа: {response}")
                return "Извините, произошла ошибка при генерации ответа."
            
        except Exception as chat_error:
            logger.warning(f"Chat API не сработал: {chat_error}, пробуем generate API")
            
            try:
                # Fallback на generate API
                prompt = self._messages_to_prompt(messages)
                response = ollama.generate(
                    model=self.active_model,
                    prompt=prompt,
                    options={
                        'temperature': self.config.get('temperature', 0.7),
                        'num_predict': self.config.get('max_tokens', 200)
                    }
                )
                return response['response']
                
            except Exception as generate_error:
                logger.error(f"Generate API тоже не сработал: {generate_error}")
                raise
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Преобразует сообщения в промпт для generate API."""
        prompt_parts = []
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                prompt_parts.append(f"Система: {content}")
            elif role == 'user':
                prompt_parts.append(f"Пользователь: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Ассистент: {content}")
        
        prompt_parts.append("Ассистент:")
        return "\n".join(prompt_parts)
    
    async def cleanup(self):
        """Очистка ресурсов."""
        logger.info("🧹 Очистка Ollama клиента...")
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        logger.debug("✅ Ollama клиент очищен")
    
    def __del__(self):
        """Деструктор для очистки executor."""
        if hasattr(self, '_executor'):
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass