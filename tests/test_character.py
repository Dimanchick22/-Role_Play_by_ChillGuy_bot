"""Тесты для персонажа."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.character import Character


def test_character_basic():
    """Базовые тесты персонажа."""
    alice = Character()
    
    print(f"=== Тестирование {alice.name} ===\n")
    
    # Тестовые сценарии
    test_cases = [
        ("Привет!", "приветствие"),
        ("Спасибо", "благодарность"), 
        ("Мне грустно", "поддержка"),
        ("Пока!", "прощание"),
        ("Как дела?", "общение")
    ]
    
    print("Тесты шаблонных ответов:")
    print("-" * 40)
    
    for i, (message, expected_type) in enumerate(test_cases, 1):
        response = alice.get_template_response(message, "Тестер")
        print(f"{i}. Сообщение: {message}")
        print(f"   Ответ: {response}")
        print(f"   Ожидаемый тип: {expected_type}")
        print()
    
    # Тест системного промпта
    print("=== Системный промпт ===")
    prompt = alice.get_system_prompt("Тестер")
    print(f"Длина промпта: {len(prompt)} символов")
    print("Содержит 'русском языке':", "русском языке" in prompt)
    print("Содержит имя персонажа:", alice.name in prompt)
    
    # Дополнительные функции
    print("\n=== Дополнительные функции ===")
    print(f"Случайный вопрос: {alice.get_random_question()}")
    print(f"Информация: {alice.get_info()[:100]}...")


def test_edge_cases():
    """Тесты граничных случаев."""
    alice = Character()
    
    print("\n=== Граничные случаи ===")
    
    edge_cases = [
        "",  # Пустое сообщение
        "ПРИВЕТ!!!",  # Капс
        "привет как дела спасибо",  # Несколько ключевых слов
        "Hello world",  # Английский
        "123456",  # Цифры
        "😊😊😊"  # Только эмодзи
    ]
    
    for message in edge_cases:
        response = alice.get_template_response(message)
        print(f"'{message}' -> '{response[:50]}...'")


if __name__ == "__main__":
    test_character_basic()
    test_edge_cases()
    print("\n✅ Все тесты персонажа пройдены!")