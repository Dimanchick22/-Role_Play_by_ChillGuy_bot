"""Тесты для LLM клиента."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.character import Character
from bot.llm_client import LLMClient


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
        character = Character()
        llm = LLMClient("llama3.2:3b", max_history=5)
        
        print(f"✅ LLM клиент создан")
        print(f"Модель: {llm.model_name}")
        
        # Установка промпта
        prompt = character.get_system_prompt("Тестер")
        llm.set_system_prompt(prompt)
        print("✅ Системный промпт установлен")
        
        # Тестовые сообщения
        test_messages = [
            "Привет! Как дела?",
            "Расскажи о себе кратко",
            "Спасибо!"
        ]
        
        user_id = 12345
        
        print("\n--- Диалог с LLM ---")
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Пользователь: {message}")
            
            try:
                response = await llm.get_response(message, user_id)
                print(f"   Алиса: {response}")
                
                # Проверяем, что ответ на русском
                if any(char in response for char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
                    print("   ✅ Ответ на русском языке")
                else:
                    print("   ⚠️ Возможно не на русском языке")
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        # Тест статистики
        print(f"\n--- Статистика ---")
        stats = llm.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Тест очистки истории
        llm.clear_history(user_id)
        print("✅ История очищена")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования LLM: {e}")
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