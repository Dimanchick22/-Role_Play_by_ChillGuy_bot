"""Клиент для работы с LLM через Ollama."""

import logging
import random
import time
from typing import Dict, List, Optional

import ollama

logger = logging.getLogger(__name__)


class LLMClient:
    """Клиент для работы с локальной LLM."""
    
    def __init__(self, model_name: str, max_history: int = 10):
        self.model_name = model_name
        self.max_history = max_history
        self.conversations: Dict[int, List[Dict]] = {}
        self.system_prompt = ""
        
        # Если model_name это "auto", не проверяем сразу
        if model_name != "auto":
            self._verify_model()
    
    def set_model(self, model_name: str) -> None:
        """Устанавливает новую модель."""
        self.model_name = model_name
        self._verify_model()
        logger.info(f"Модель изменена на: {model_name}")
    
    def _verify_model(self) -> None:
        """Проверяет доступность модели."""
        try:
            # Проверяем список моделей
            models_response = ollama.list()
            available_models = []
            
            # Обрабатываем разные форматы ответа
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                logger.warning(f"Неизвестный формат ответа: {type(models_response)}")
                models_list = []
            
            # Извлекаем имена моделей
            for model in models_list:
                if hasattr(model, 'model'):
                    available_models.append(model.model)
                elif isinstance(model, dict) and 'model' in model:
                    available_models.append(model['model'])
            
            logger.info(f"Доступные модели: {available_models}")
            
            # Проверяем нашу модель
            if self.model_name not in available_models:
                logger.warning(f"Модель {self.model_name} не найдена")
                
                # Ищем альтернативу
                alternative = self._find_alternative_model(available_models)
                if alternative:
                    self.model_name = alternative
                    logger.info(f"Используем модель: {self.model_name}")
                else:
                    raise RuntimeError("Нет доступных моделей")
            
            # Тестируем модель
            self._test_model()
            
        except Exception as e:
            logger.error(f"Ошибка проверки модели: {e}")
            raise
    
    def _find_alternative_model(self, available: List[str]) -> Optional[str]:
        """Ищет альтернативную модель."""
        # Приоритет моделей
        preferred = ['llama3.2:3b', 'llama3.2', 'mistral', 'qwen']
        
        for pref in preferred:
            for model in available:
                if pref in model.lower():
                    return model
        
        # Возвращаем первую доступную
        return available[0] if available else None
    
    def _test_model(self) -> None:
        """Тестирует модель простым запросом."""
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt="Скажи 'тест' на русском языке",
                options={'num_predict': 5}
            )
            logger.info(f"Модель {self.model_name} работает корректно")
        except Exception as e:
            logger.error(f"Ошибка тестирования модели: {e}")
            raise
    
    def set_system_prompt(self, prompt: str) -> None:
        """Устанавливает системный промпт."""
        self.system_prompt = prompt
        logger.debug("Системный промпт установлен")
    
    def _get_history(self, user_id: int) -> List[Dict]:
        """Получает историю разговора."""
        return self.conversations.get(user_id, [])
    
    def _add_to_history(self, user_id: int, role: str, content: str) -> None:
        """Добавляет сообщение в историю."""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        self.conversations[user_id].append({"role": role, "content": content})
        
        # Ограничиваем размер истории
        if len(self.conversations[user_id]) > self.max_history * 2:
            self.conversations[user_id] = self.conversations[user_id][-self.max_history * 2:]
    
    async def get_response(self, message: str, user_id: int) -> str:
        """Получает ответ от LLM."""
        try:
            start_time = time.time()
            
            # Готовим сообщения
            messages = self._prepare_messages(user_id, message)
            
            # Отправляем запрос
            response = await self._call_llm(messages)
            
            # Сохраняем в историю
            self._add_to_history(user_id, "user", message)
            self._add_to_history(user_id, "assistant", response)
            
            # Логируем
            elapsed = time.time() - start_time
            logger.info(f"Ответ получен за {elapsed:.2f}с: {response[:50]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа: {e}")
            return self._get_fallback_response()
    
    def _prepare_messages(self, user_id: int, message: str) -> List[Dict]:
        """Готовит сообщения для LLM."""
        messages = []
        
        # Системный промпт
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # История
        messages.extend(self._get_history(user_id))
        
        # Текущее сообщение
        messages.append({"role": "user", "content": message})
        
        return messages
    
    async def _call_llm(self, messages: List[Dict]) -> str:
        """Вызывает LLM API."""
        try:
            # Пробуем chat API
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_predict': 200
                }
            )
            return response['message']['content'].strip()
            
        except Exception:
            # Fallback на generate API
            logger.info("Переключаемся на generate API")
            prompt = self._messages_to_prompt(messages)
            
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.7,
                    'top_p': 0.9, 
                    'num_predict': 200
                }
            )
            return response['response'].strip()
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Преобразует сообщения в промпт."""
        prompt = ""
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                prompt += f"Системное сообщение: {content}\n\n"
            elif role == 'user':
                prompt += f"Пользователь: {content}\n"
            elif role == 'assistant':
                prompt += f"Ассистент: {content}\n"
        
        prompt += "Ассистент:"
        return prompt
    
    def _get_fallback_response(self) -> str:
        """Запасной ответ при ошибке."""
        responses = [
            "Упс! 🙈 Что-то с моими мыслями... Попробуй еще раз!",
            "Хм, кажется я задумалась 🤔 Повтори, пожалуйста?",
            "Ой, произошла ошибка 😅 Давай еще раз!",
            "Моя нейросеть подвисла 🤖 Попробуй снова!"
        ]
        return random.choice(responses)
    
    def clear_history(self, user_id: int) -> None:
        """Очищает историю пользователя."""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"История пользователя {user_id} очищена")
    
    def get_stats(self) -> Dict:
        """Статистика работы."""
        return {
            'model': self.model_name,
            'active_conversations': len(self.conversations),
            'max_history': self.max_history
        }