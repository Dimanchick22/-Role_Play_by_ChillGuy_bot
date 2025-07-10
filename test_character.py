#!/usr/bin/env python3
"""
Скрипт для тестирования персонажа бота
"""

from character import Character

def test_character():
    """Тестирует различные сценарии общения с персонажем"""
    
    # Создаем персонажа
    alice = Character()
    
    print(f"=== Тестирование персонажа {alice.name} ===\n")
    
    # Тестовые сообщения
    test_messages = [
        "Привет!",
        "Как дела?",
        "Спасибо за помощь",
        "Мне грустно",
        "У меня отличное настроение!",
        "Что такое любовь?",
        "Пока!",
        "Расскажи о себе",
        "Я устал",
        "Ты крутая!"
    ]
    
    print("Тестовые диалоги:")
    print("-" * 50)
    
    for i, message in enumerate(test_messages, 1):
        response = alice.get_response(message, "Тестер")
        message_type = alice.analyze_message(message)
        
        print(f"{i}. Пользователь: {message}")
        print(f"   Тип сообщения: {message_type}")
        print(f"   {alice.name}: {response}")
        print()
    
    print("=== Дополнительные функции ===")
    print(f"Случайный вопрос: {alice.get_random_question()}")
    print()
    print("Информация о персонаже:")
    print(alice.get_character_info())

if __name__ == "__main__":
    test_character()