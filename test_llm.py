#!/usr/bin/env python3
"""
Скрипт для тестирования LLM интеграции
"""

import asyncio
from character import Character
from llm_handler import LLMHandler

async def test_llm():
    """Тестирует LLM с персонажем"""
    
    print("=== Тестирование LLM интеграции ===\n")
    
    # Инициализируем персонажа и LLM
    character = Character()
    llm = LLMHandler(model_name="dolphin3:latest")  # Измени на свою модель
    
    # Устанавливаем промпт
    prompt = character.get_llm_prompt("Тестер")
    llm.set_system_prompt(prompt)
    
    print(f"Персонаж: {character.name}")
    print(f"Модель: {llm.model_name}")
    print(f"Системный промпт установлен: {len(prompt)} символов\n")
    
    # Тестовые сообщения
    test_messages = [
        "Привет! Как дела?",
        "Расскажи о себе",
        "Мне грустно сегодня",
        "Я выучил новый язык программирования!",
        "Что думаешь о космосе?",
        "Спасибо за помощь",
        "Как поднять настроение?",
        "Пока!"
    ]
    
    user_id = 12345  # Тестовый ID
    
    print("Начинаем диалог с LLM:\n")
    print("-" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. Пользователь: {message}")
        
        try:
            response = await llm.get_response(message, user_id, "Тестер")
            print(f"   {character.name}: {response}")
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        print()
    
    # Информация о модели
    print("\n=== Информация о модели ===")
    model_info = llm.get_model_info()
    for key, value in model_info.items():
        print(f"{key}: {value}")

def test_connection():
    """Тестирует подключение к Ollama"""
    try:
        import ollama
        
        # Попробуем получить список моделей
        models_response = ollama.list()
        print("✅ Подключение к Ollama успешно!")
        
        # Отладочная информация
        print(f"Тип ответа: {type(models_response)}")
        print(f"Ответ: {models_response}")
        
        # Попробуем разные варианты структуры
        models_list = []
        
        if isinstance(models_response, dict):
            if 'models' in models_response:
                models_list = models_response['models']
            elif 'model' in models_response:
                models_list = models_response['model']
        elif isinstance(models_response, list):
            models_list = models_response
        
        print("\nДоступные модели:")
        if models_list:
            for model in models_list:
                if isinstance(model, dict):
                    # Попробуем разные поля для имени
                    name = model.get('name') or model.get('model') or model.get('id') or str(model)
                    print(f"  - {name}")
                else:
                    print(f"  - {model}")
        else:
            print("  Модели не найдены или неизвестная структура данных")
            
        # Простая проверка - попробуем отправить тестовый запрос
        print("\n=== Тест простого запроса ===")
        try:
            # Попробуем найти доступную модель
            test_models = [ "dolphin3:latest", "llama3.2:3b", "llama3.2", "llama2", "mistral"]
            
            for test_model in test_models:
                try:
                    print(f"Тестируем модель: {test_model}")
                    response = ollama.generate(
                        model=test_model,
                        prompt="Скажи 'привет' на русском",
                        options={'num_predict': 10}
                    )
                    print(f"✅ Модель {test_model} работает!")
                    print(f"Ответ: {response.get('response', 'Нет ответа')}")
                    return True
                except Exception as model_error:
                    print(f"❌ Модель {test_model}: {model_error}")
                    continue
            
            print("❌ Ни одна тестовая модель не работает")
            return False
            
        except Exception as test_error:
            print(f"❌ Ошибка тестового запроса: {test_error}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к Ollama: {e}")
        print("\nПроверьте:")
        print("1. Установлен ли Ollama")
        print("2. Запущен ли сервер Ollama")
        print("3. Установлены ли модели (ollama pull dolphin3:latest)")
        return False

if __name__ == "__main__":
    print("=== Проверка подключения ===")
    if test_connection():
        print("\n=== Запуск тестов ===")
        asyncio.run(test_llm())
    else:
        print("Исправьте проблемы с Ollama и запустите тест снова.")