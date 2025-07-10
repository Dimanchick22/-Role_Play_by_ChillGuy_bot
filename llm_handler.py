import ollama
import logging
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class LLMHandler:
    """Класс для работы с локальной LLM через Ollama"""
    
    def __init__(self, model_name: str = "dolphin3:latest", max_history: int = 10):
        self.model_name = model_name
        self.max_history = max_history
        self.conversation_history: Dict[int, List[Dict]] = {}
        self.system_prompt = ""
        
        # Проверяем доступность модели
        self._check_model_availability()
    
    def _check_model_availability(self) -> bool:
        """Проверяет доступность модели"""
        try:
            # Получаем список установленных моделей
            models_response = ollama.list()
            
            # Обрабатываем новую структуру данных Ollama
            model_names = []
            
            # Проверяем, есть ли атрибут models
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                logger.error(f"Неизвестная структура ответа: {type(models_response)}")
                return False
            
            # Извлекаем имена моделей
            for model in models_list:
                if hasattr(model, 'model'):
                    model_names.append(model.model)
                elif isinstance(model, dict) and 'model' in model:
                    model_names.append(model['model'])
                elif hasattr(model, 'name'):
                    model_names.append(model.name)
                elif isinstance(model, dict) and 'name' in model:
                    model_names.append(model['name'])
            
            logger.info(f"Найденные модели: {model_names}")
            
            if self.model_name not in model_names:
                logger.warning(f"Модель {self.model_name} не найдена. Доступные модели: {model_names}")
                
                # Пытаемся найти похожую модель
                for model_name in model_names:
                    if any(variant in model_name.lower() for variant in ['llama', 'mistral', 'qwen', 'dolphin']):
                        self.model_name = model_name
                        logger.info(f"Переключились на модель: {self.model_name}")
                        break
                else:
                    if model_names:
                        self.model_name = model_names[0]
                        logger.info(f"Используем первую доступную модель: {self.model_name}")
                    else:
                        logger.error("Нет доступных моделей! Установите модель через 'ollama pull'")
                        return False
            
            # Тестируем модель простым запросом
            try:
                test_response = ollama.generate(
                    model=self.model_name,
                    prompt="Скажи только 'Тест пройден' на русском языке.",
                    options={'num_predict': 10}
                )
                logger.info(f"Модель {self.model_name} протестирована успешно")
                return True
            except Exception as test_error:
                logger.error(f"Ошибка тестирования модели {self.model_name}: {test_error}")
                return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке модели: {e}")
            return False
    
    def set_system_prompt(self, character_prompt: str):
        """Устанавливает системный промпт персонажа"""
        self.system_prompt = character_prompt
        logger.info("Системный промпт установлен")
    
    def _get_conversation_history(self, user_id: int) -> List[Dict]:
        """Получает историю разговора для пользователя"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        return self.conversation_history[user_id]
    
    def _add_to_history(self, user_id: int, role: str, content: str):
        """Добавляет сообщение в историю"""
        history = self._get_conversation_history(user_id)
        history.append({"role": role, "content": content})
        
        # Ограничиваем размер истории
        if len(history) > self.max_history * 2:  # *2 потому что user + assistant
            history = history[-self.max_history * 2:]
            self.conversation_history[user_id] = history
    
    def _prepare_messages(self, user_id: int, user_message: str) -> List[Dict]:
        """Подготавливает сообщения для отправки в LLM"""
        messages = []
        
        # Добавляем системный промпт
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Добавляем историю разговора
        history = self._get_conversation_history(user_id)
        messages.extend(history)
        
        # Добавляем текущее сообщение пользователя
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    async def get_response(self, user_message: str, user_id: int, user_name: str = "") -> str:
        """Получает ответ от LLM"""
        try:
            start_time = time.time()
            
            # Подготавливаем сообщения
            messages = self._prepare_messages(user_id, user_message)
            
            # Отправляем запрос к модели
            logger.info(f"Отправляем запрос к {self.model_name}...")
            
            try:
                # Пробуем новый формат chat API
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options={
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'num_predict': 500
                    }
                )
                ai_response = response['message']['content'].strip()
                
            except Exception as chat_error:
                logger.warning(f"Chat API не сработал: {chat_error}")
                logger.info("Пробуем generate API...")
                
                # Формируем полный промпт для generate API
                full_prompt = ""
                for msg in messages:
                    if msg['role'] == 'system':
                        full_prompt += f"Системное сообщение: {msg['content']}\n\n"
                    elif msg['role'] == 'user':
                        full_prompt += f"Пользователь: {msg['content']}\n"
                    elif msg['role'] == 'assistant':
                        full_prompt += f"Ассистент: {msg['content']}\n"
                
                full_prompt += "Ассистент:"
                
                # Пробуем generate API
                response = ollama.generate(
                    model=self.model_name,
                    prompt=full_prompt,
                    options={
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'num_predict': 500
                    }
                )
                ai_response = response['response'].strip()
            
            # Добавляем в историю
            self._add_to_history(user_id, "user", user_message)
            self._add_to_history(user_id, "assistant", ai_response)
            
            # Логируем
            response_time = time.time() - start_time
            logger.info(f"Получен ответ за {response_time:.2f}s: {ai_response[:100]}...")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Ошибка при получении ответа от LLM: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Возвращает запасной ответ в случае ошибки"""
        fallback_responses = [
            "Упс! 🙈 Что-то с моими мыслями... Попробуй еще раз!",
            "Хм, кажется я задумалась 🤔 Повтори, пожалуйста?",
            "Ой, произошла небольшая ошибка 😅 Давай еще раз!",
            "Моя нейросеть немного подвисла 🤖 Попробуй снова!"
        ]
        import random
        return random.choice(fallback_responses)
    
    def clear_history(self, user_id: int):
        """Очищает историю разговора для пользователя"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"История пользователя {user_id} очищена")
    
    def get_model_info(self) -> Dict:
        """Возвращает информацию о текущей модели"""
        try:
            models_response = ollama.list()
            
            # Обрабатываем новую структуру данных
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                return {'name': self.model_name, 'size': 'Неизвестно', 'modified': 'Неизвестно'}
            
            # Ищем информацию о текущей модели
            for model in models_list:
                model_name = None
                
                if hasattr(model, 'model'):
                    model_name = model.model
                elif isinstance(model, dict) and 'model' in model:
                    model_name = model['model']
                elif hasattr(model, 'name'):
                    model_name = model.name
                elif isinstance(model, dict) and 'name' in model:
                    model_name = model['name']
                
                if model_name == self.model_name:
                    # Извлекаем информацию
                    size = 'Неизвестно'
                    modified = 'Неизвестно'
                    
                    if hasattr(model, 'size'):
                        size = f"{model.size / (1024**3):.1f} GB" if model.size else 'Неизвестно'
                    elif isinstance(model, dict) and 'size' in model:
                        size = f"{model['size'] / (1024**3):.1f} GB" if model['size'] else 'Неизвестно'
                    
                    if hasattr(model, 'modified_at'):
                        modified = str(model.modified_at) if model.modified_at else 'Неизвестно'
                    elif isinstance(model, dict) and 'modified_at' in model:
                        modified = str(model['modified_at']) if model['modified_at'] else 'Неизвестно'
                    
                    return {
                        'name': model_name,
                        'size': size,
                        'modified': modified
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения информации о модели: {e}")
        
        return {'name': self.model_name, 'size': 'Неизвестно', 'modified': 'Неизвестно'}