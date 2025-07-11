"""Тесты для LLM клиента - исправленная версия."""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ИСПРАВЛЕННЫЕ ИМПОРТЫ
from characters.alice import AliceCharacter
from services.llm.ollama_client import OllamaClient
from models.base import User, BaseMessage, MessageRole, MessageType


def create_test_user() -> User:
    """Создает тестового пользователя."""
    return User(
        id=12345,
        username="tester",
        first_name="Тестер",
        last_name="Тестович",
        language_code="ru",
        created_at=datetime.now(),
        last_seen=datetime.now(),
        is_premium=False
    )


def test_ollama_connection():
    """Тест подключения к Ollama."""
    print("=== Тест подключения к Ollama ===")
    
    try:
        import ollama
        
        # Проверяем список моделей
        models_response = ollama.list()
        print("✅ Подключение к Ollama успешно!")
        
        # Обработка разных форматов ответа
        if hasattr(models_response, 'models'):
            models_list = models_response.models
        elif isinstance(models_response, dict) and 'models' in models_response:
            models_list = models_response['models']
        else:
            print(f"Неизвестный формат ответа: {type(models_response)}")
            return False
        
        print(f"Найдено моделей: {len(models_list)}")
        
        # Показываем первые 3 модели
        for i, model in enumerate(models_list[:3]):
            if hasattr(model, 'model'):
                name = model.model
            elif isinstance(model, dict) and 'model' in model:
                name = model['model']
            elif hasattr(model, 'name'):
                name = model.name
            else:
                name = str(model)
            print(f"  {i+1}. {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("\nРекомендации:")
        print("1. Установите Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Запустите сервер: ollama serve")
        print("3. Скачайте модель: ollama pull llama3.2:3b")
        return False


async def test_llm_client():
    """Тест LLM клиента."""
    print("\n=== Тест LLM клиента ===")
    
    try:
        # Инициализация
        character = AliceCharacter()
        llm = OllamaClient(
            model_name="auto",
            temperature=0.7,
            max_tokens=200
        )
        
        print(f"✅ LLM клиент создан")
        print(f"Модель: {llm.model_name}")
        
        # Пытаемся инициализировать
        print("🔄 Попытка инициализации...")
        initialized = await llm.initialize()
        
        if not initialized:
            print("❌ Не удалось инициализировать LLM клиент")
            return False
        
        print(f"✅ LLM клиент инициализирован с моделью: {llm.model_name}")
        
        # Создаем тестового пользователя
        test_user = create_test_user()
        
        # Тестовые сообщения
        test_messages_text = [
            "Привет! Как дела?",
            "Расскажи о себе кратко",
            "Спасибо!"
        ]
        
        print("\n--- Диалог с LLM ---")
        for i, message_text in enumerate(test_messages_text, 1):
            print(f"\n{i}. Пользователь: {message_text}")
            
            try:
                # Создаем объект сообщения
                test_message = BaseMessage(
                    id=f"test_{i}",
                    content=message_text,
                    role=MessageRole.USER,
                    message_type=MessageType.TEXT,
                    timestamp=datetime.now(),
                    metadata={"user_id": test_user.id}
                )
                
                # Генерируем ответ
                response = await llm.generate_response(
                    messages=[test_message],
                    user=test_user
                )
                
                print(f"   Алиса: {response}")
                
                # Проверяем, что ответ на русском
                if any(char in response.lower() for char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
                    print("   ✅ Ответ на русском языке")
                else:
                    print("   ⚠️ Возможно не на русском языке")
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        # Тест проверки здоровья
        print(f"\n--- Проверка состояния ---")
        health = await llm.check_health()
        print(f"Состояние LLM: {'✅ Здоров' if health else '❌ Недоступен'}")
        
        # Тест получения доступных моделей
        available_models = llm.get_available_models()
        print(f"Доступно моделей: {len(available_models)}")
        for model in available_models[:3]:
            print(f"  - {model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования LLM: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_tests():
    """Запуск всех тестов."""
    print("🧪 Запуск тестов LLM\n")
    
    # Тест подключения
    if not test_ollama_connection():
        print("\n❌ Тесты остановлены из-за проблем с подключением")
        return
    
    # Тест клиента
    success = await test_llm_client()
    
    if success:
        print("\n✅ Все тесты LLM пройдены!")
    else:
        print("\n❌ Некоторые тесты не прошли")


if __name__ == "__main__":
    asyncio.run(run_tests())