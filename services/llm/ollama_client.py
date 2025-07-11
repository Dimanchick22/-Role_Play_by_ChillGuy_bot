"""Ollama LLM клиент."""

import logging
import time
from typing import List, Dict, Any
import ollama

from services.llm.base_client import BaseLLMClient
from models.base import BaseMessage, User

logger = logging.getLogger(__name__)

class OllamaClient(BaseLLMClient):
    """Клиент для Ollama."""
    
    async def initialize(self) -> bool:
        """Инициализирует клиент."""
        try:
            # Проверяем подключение
            models = ollama.list()
            available_models = self.get_available_models()
            
            # Автовыбор модели
            if self.model_name == "auto":
                self.model_name = self._select_best_model(available_models)
            
            # Проверяем выбранную модель
            if self.model_name not in available_models:
                logger.warning(f"Модель {self.model_name} недоступна, пробуем скачать...")
                # Пробуем скачать модель
                try:
                    ollama.pull(self.model_name)
                    logger.info(f"✅ Модель {self.model_name} успешно скачана")
                except Exception as pull_error:
                    logger.error(f"❌ Не удалось скачать модель: {pull_error}")
                    raise ValueError(f"Модель {self.model_name} недоступна и не может быть скачана")
            
            # Тестируем модель
            await self._test_model()
            
            self.is_available = True
            logger.info(f"✅ Ollama клиент инициализирован с моделью {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Ollama: {e}")
            self.is_available = False
            return False
    
    async def generate_response(
        self, 
        messages: List[BaseMessage], 
        user: User,
        **kwargs
    ) -> str:
        """Генерирует ответ через Ollama."""
        try:
            # Преобразуем сообщения в формат Ollama
            ollama_messages = self._convert_messages(messages, user)
            
            logger.debug(f"Отправляем {len(ollama_messages)} сообщений в Ollama")
            
            # Делаем запрос
            response = await self._call_ollama(ollama_messages)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            raise
    
    async def check_health(self) -> bool:
        """Проверяет состояние Ollama."""
        try:
            ollama.list()
            return True
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Возвращает доступные модели."""
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
                    return model
        
        return available[0] if available else "llama3.2:3b"
    
    def _convert_messages(self, messages: List[BaseMessage], user: User) -> List[Dict]:
        """Преобразует сообщения в формат Ollama."""
        ollama_messages = []
        
        # Получаем персонажа для системного промпта
        character_service = None
        try:
            from core.registry import registry
            character_service = registry.get('character')
        except:
            pass
        
        # Добавляем системный промпт
        if character_service and hasattr(character_service, 'get_system_prompt'):
            system_prompt = character_service.get_system_prompt(user)
            ollama_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Добавляем сообщения пользователя (только последние 5)
        for msg in messages[-5:]:
            ollama_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return ollama_messages
    
    async def _call_ollama(self, messages: List[Dict]) -> str:
        """Вызывает Ollama API."""
        try:
            logger.debug(f"Вызов Ollama с моделью {self.model_name}")
            
            # Пробуем chat API
            response = ollama.chat(
                model=self.model_name,
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
                # Fallback на generate
                prompt = self._messages_to_prompt(messages)
                response = ollama.generate(
                    model=self.model_name,
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
        """Преобразует сообщения в промпт."""
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
    
    async def _test_model(self) -> None:
        """Тестирует модель."""
        try:
            test_response = ollama.generate(
                model=self.model_name,
                prompt="Скажи 'тест'",
                options={'num_predict': 10}
            )
            logger.debug(f"Тест модели успешен: {test_response['response'][:50]}...")
        except Exception as e:
            logger.error(f"Тест модели не прошел: {e}")
            raise