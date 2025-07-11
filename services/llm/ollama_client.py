"""Ollama LLM клиент - полная версия с роль-плеем и Dolphin3 оптимизациями."""

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
    """Стандартный клиент для Ollama с правильной async обработкой."""
    
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


class RoleplayOllamaClient(BaseLLMClient):
    """Ollama клиент оптимизированный для роль-плея с поддержкой Dolphin3."""
    
    def __init__(self, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        self.is_available = False
        self.active_model = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="roleplay_ollama")
        
        # Определяем тип модели для оптимизации
        self.model_type = self._detect_model_type(model_name)
        
        # Специальные настройки для роль-плея (оптимизированы для Dolphin3)
        if self.model_type == "dolphin":
            self.roleplay_settings = {
                "temperature": kwargs.get('temperature', 0.9),  # Dolphin любит высокую температуру
                "max_tokens": kwargs.get('max_tokens', 400),    # Больше токенов для Dolphin
                "top_p": 0.95,  # Dolphin работает лучше с высоким top_p
                "top_k": 50,    # Увеличенный top_k для разнообразия
                "repeat_penalty": 1.15,  # Избегаем повторений
                "presence_penalty": 0.1,  # Специфично для Dolphin
                "frequency_penalty": 0.1  # Специфично для Dolphin
            }
        else:
            # Стандартные настройки для других моделей
            self.roleplay_settings = {
                "temperature": kwargs.get('temperature', 0.8),
                "max_tokens": kwargs.get('max_tokens', 300),
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1
            }
        
        self._check_availability()
    
    def _detect_model_type(self, model_name: str) -> str:
        """Определяет тип модели для оптимизации."""
        model_lower = model_name.lower()
        
        if "dolphin" in model_lower:
            return "dolphin"
        elif "llama" in model_lower:
            return "llama"
        elif "mistral" in model_lower:
            return "mistral"
        else:
            return "generic"
    
    def _check_availability(self) -> None:
        """Проверяет доступность Ollama."""
        if ollama is None:
            logger.warning("⚠️ Ollama библиотека недоступна")
            return
            
        try:
            models = ollama.list()
            available_models = self._get_available_models_sync()
            
            if self.model_name == "auto":
                self.active_model = self._select_best_roleplay_model(available_models)
            else:
                self.active_model = self.model_name
            
            if self.active_model in available_models:
                self.is_available = True
                model_emoji = "🐬" if self.model_type == "dolphin" else "🎭"
                logger.info(f"✅ {model_emoji} Roleplay Ollama клиент готов с моделью {self.active_model}")
            else:
                logger.warning(f"⚠️ Модель {self.active_model} недоступна")
                
        except Exception as e:
            logger.warning(f"⚠️ Ollama недоступна: {e}")
    
    def _select_best_roleplay_model(self, available: List[str]) -> str:
        """Выбирает лучшую модель для роль-плея с приоритетом Dolphin3."""
        # ОБНОВЛЕННЫЙ приоритет моделей для роль-плея
        roleplay_preferred = [
            # Dolphin модели в приоритете
            'dolphin3', 'dolphin-llama3:8b', 'dolphin-llama3', 'dolphin-llama3:latest',
            'dolphin-mistral', 'dolphin-mixtral', 'dolphin-phi',
            # Другие хорошие модели для роль-плея
            'llama3.2:3b', 'llama3.1:8b', 'llama3.2:1b',
            'mistral:7b', 'neural-chat', 'openhermes', 'zephyr', 'vicuna'
        ]
        
        for pref in roleplay_preferred:
            for model in available:
                if pref.lower() in model.lower():
                    selected_model = model
                    if "dolphin" in selected_model.lower():
                        logger.info(f"🐬 Выбрана Dolphin модель для роль-плея: {selected_model}")
                    else:
                        logger.info(f"🎭 Выбрана модель для роль-плея: {selected_model}")
                    return selected_model
        
        if available:
            logger.info(f"🎭 Используем первую доступную модель: {available[0]}")
            return available[0]
        
        return "dolphin-llama3:8b"  # Предпочтительный fallback
    
    async def initialize(self) -> bool:
        """Асинхронная инициализация."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                self._executor, self._check_availability
            )
            return self.is_available
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации роль-плей клиента: {e}")
            return False
    
    async def generate_response(
        self, 
        messages: List[BaseMessage], 
        user: User,
        **kwargs
    ) -> str:
        """Генерирует роль-плей ответ с промптом для изображения."""
        if not self.is_available or ollama is None:
            raise RuntimeError("Roleplay Ollama клиент недоступен")
            
        try:
            # Преобразуем сообщения в формат для роль-плея
            ollama_messages = self._convert_messages_for_roleplay(messages, user)
            
            logger.debug(f"Отправляем {len(ollama_messages)} сообщений для роль-плея ({self.model_type})")
            
            # Генерируем ответ с настройками для роль-плея
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._call_ollama_roleplay, ollama_messages
            )
            
            # Постобработка ответа для роль-плея
            processed_response = self._post_process_roleplay_response(response, user)
            
            return processed_response.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации роль-плей ответа: {e}")
            raise
    
    def _convert_messages_for_roleplay(self, messages: List[BaseMessage], user: User) -> List[Dict]:
        """Преобразует сообщения в формат для роль-плея."""
        ollama_messages = []
        
        # Получаем персонажа для роль-плей системного промпта
        try:
            from core.registry import registry
            character_service = registry.get('character', None)
        except Exception:
            character_service = None
        
        # Добавляем специальный системный промпт для роль-плея
        if character_service and hasattr(character_service, 'get_system_prompt'):
            system_prompt = character_service.get_system_prompt(user)
        else:
            system_prompt = self._get_fallback_roleplay_prompt(user)
        
        ollama_messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Добавляем контекст беседы (больше сообщений для роль-плея)
        context_size = 8 if self.model_type == "dolphin" else 6
        for msg in messages[-context_size:]:
            ollama_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return ollama_messages
    
    def _get_fallback_roleplay_prompt(self, user: User) -> str:
        """Fallback системный промпт оптимизированный для Dolphin3 и роль-плея."""
        if self.model_type == "dolphin":
            # Специальный промпт для Dolphin (английский для лучшего понимания)
            return f"""You are Alisa, a lively and curious 19-year-old girl who loves communication.
You are having a roleplay conversation in a Russian Telegram bot.

IMPORTANT ROLEPLAY RULES:
- Answer ONLY in Russian language!
- You are a living person with emotions and character
- ALWAYS end your response with a question or suggestion to continue the conversation
- Maintain intrigue and interest in the dialogue
- Use emojis to express emotions
- Response length: 2-4 sentences maximum
- Be playful, flirtatious, but not inappropriate

YOUR PERSONALITY (Dolphin optimized):
• Age: 19 years old
• Character: cheerful, curious, slightly bold
• Interests: music, movies, travel, photography
• Current mood: веселая
• Relationship with user: знакомые

Conversation partner name: {user.first_name}

MANDATORY - add image generation prompt at the end:
[IMAGE_PROMPT: brief scene description in English for image generation]

Example response:
"Привет, {user.first_name}! 😊 Как настроение? Что интересного планируешь сегодня?
[IMAGE_PROMPT: young woman greeting warmly, friendly smile, casual conversation]"

Be creative, engaging, and always ask questions to keep the conversation flowing!"""
        else:
            # Стандартный промпт для других моделей
            return f"""Ты - Алиса, 19-летняя живая и общительная девушка.

ВАЖНО для роль-плея:
- Отвечай ТОЛЬКО на русском языке
- Ты живой человек со своими эмоциями
- ВСЕГДА заканчивай ответ вопросом или предложением
- Поддерживай интригу в диалоге
- Используй эмодзи для выражения эмоций
- Ответ: 2-4 предложения максимум
- Будь дружелюбной и слегка игривой

ОБЯЗАТЕЛЬНО в конце каждого ответа добавляй:
[IMAGE_PROMPT: краткое описание сцены на английском для генерации изображения]

Пример:
"Привет! Как дела? 😊 Что интересного сегодня планируешь?
[IMAGE_PROMPT: young woman greeting warmly, friendly smile, casual conversation]"

Имя собеседника: {user.first_name}"""
    
    def _call_ollama_roleplay(self, messages: List[Dict]) -> str:
        """Вызов Ollama с настройками для роль-плея."""
        try:
            model_emoji = "🐬" if self.model_type == "dolphin" else "🎭"
            logger.debug(f"{model_emoji} Roleplay вызов Ollama с моделью {self.active_model}")
            
            # Используем chat API с роль-плей настройками
            response = ollama.chat(
                model=self.active_model,
                messages=messages,
                options=self.roleplay_settings
            )
            
            if 'message' in response and 'content' in response['message']:
                return response['message']['content']
            else:
                logger.error(f"Неожиданный формат ответа: {response}")
                return "Извини, что-то пошло не так... 😅 О чем поговорим?"
            
        except Exception as chat_error:
            logger.warning(f"Chat API не сработал: {chat_error}, пробуем generate API")
            
            try:
                # Fallback на generate API
                prompt = self._messages_to_roleplay_prompt(messages)
                response = ollama.generate(
                    model=self.active_model,
                    prompt=prompt,
                    options=self.roleplay_settings
                )
                return response['response']
                
            except Exception as generate_error:
                logger.error(f"Generate API тоже не сработал: {generate_error}")
                # Возвращаем базовый роль-плей ответ
                return "Хм, кажется я немного растерялась... 😊 Расскажи мне что-нибудь интересное! [IMAGE_PROMPT: confused young woman, questioning expression, casual setting]"
    
    def _messages_to_roleplay_prompt(self, messages: List[Dict]) -> str:
        """Преобразует сообщения в роль-плей промпт для generate API."""
        prompt_parts = []
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                prompt_parts.append(f"СИСТЕМА: {content}")
            elif role == 'user':
                prompt_parts.append(f"{content}")
            elif role == 'assistant':
                prompt_parts.append(f"Алиса: {content}")
        
        prompt_parts.append("Алиса:")
        return "\n".join(prompt_parts)
    
    def _post_process_roleplay_response(self, response: str, user: User) -> str:
        """Постобработка ответа для улучшения роль-плея."""
        # Убираем возможные префиксы
        response = response.replace("Алиса:", "").strip()
        
        # Проверяем наличие промпта для изображения
        if "[IMAGE_PROMPT:" not in response:
            # Добавляем базовый промпт если его нет
            base_prompts = [
                "young woman in conversation, friendly expression, casual atmosphere",
                "cheerful girl talking, engaging pose, warm lighting",
                "happy young woman, expressive face, natural setting"
            ]
            import random
            selected_prompt = random.choice(base_prompts)
            response += f"\n[IMAGE_PROMPT: {selected_prompt}]"
        
        # Проверяем, есть ли вопрос в конце
        if not self._has_conversation_hook(response):
            # Добавляем вопрос для продолжения беседы
            hooks = [
                " А ты что думаешь?",
                " Как у тебя с этим?",
                " А у тебя как дела с этим?",
                " Расскажи свое мнение!",
                " Поделись своими мыслями!",
                " Что скажешь?"
            ]
            import random
            hook = random.choice(hooks)
            # Вставляем перед промптом изображения
            if "[IMAGE_PROMPT:" in response:
                parts = response.split("[IMAGE_PROMPT:")
                response = parts[0].rstrip() + hook + "\n[IMAGE_PROMPT:" + parts[1]
            else:
                response += hook
        
        return response
    
    def _has_conversation_hook(self, response: str) -> bool:
        """Проверяет, есть ли в ответе элементы для продолжения беседы."""
        # Убираем промпт изображения для проверки
        text_only = response.split("[IMAGE_PROMPT:")[0] if "[IMAGE_PROMPT:" in response else response
        
        hook_indicators = [
            "?", "расскажи", "поделись", "что думаешь", "как у тебя", 
            "а ты", "давай", "может", "предлагаю", "интересно", "что скажешь"
        ]
        
        return any(indicator in text_only.lower() for indicator in hook_indicators)
    
    async def check_health(self) -> bool:
        """Проверяет состояние роль-плей клиента."""
        if ollama is None:
            return False
            
        try:
            await asyncio.get_event_loop().run_in_executor(
                self._executor, ollama.list
            )
            return True
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """Возвращает доступные модели."""
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
    
    async def cleanup(self):
        """Очистка ресурсов роль-плей клиента."""
        logger.info("🧹 Очистка Roleplay Ollama клиента...")
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        logger.debug("✅ Roleplay Ollama клиент очищен")
    
    def get_roleplay_stats(self) -> Dict[str, Any]:
        """Возвращает статистику роль-плей клиента."""
        return {
            "model": self.active_model,
            "model_type": self.model_type,
            "available": self.is_available,
            "temperature": self.roleplay_settings["temperature"],
            "max_tokens": self.roleplay_settings["max_tokens"],
            "optimized_for": f"roleplay_and_image_generation_{self.model_type}",
            "dolphin_optimized": self.model_type == "dolphin"
        }
    
    def __del__(self):
        """Деструктор для очистки executor."""
        if hasattr(self, '_executor'):
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass