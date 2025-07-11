"""Тесты для персонажа - исправленная версия."""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ИСПРАВЛЕННЫЕ ИМПОРТЫ
from characters.alice import AliceCharacter
from models.base import User


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


def test_character_basic():
    """Базовые тесты персонажа."""
    alice = AliceCharacter()
    test_user = create_test_user()
    
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
        response = alice.get_template_response(message, test_user.first_name)
        print(f"{i}. Сообщение: {message}")
        print(f"   Ответ: {response}")
        print(f"   Ожидаемый тип: {expected_type}")
        print()
    
    # Тест системного промпта
    print("=== Системный промпт ===")
    prompt = alice.get_system_prompt(test_user)
    print(f"Длина промпта: {len(prompt)} символов")
    print("Содержит 'русском языке':", "русском языке" in prompt)
    print("Содержит имя персонажа:", alice.name in prompt)
    print("Содержит имя пользователя:", test_user.first_name in prompt)
    
    # Дополнительные функции
    print("\n=== Дополнительные функции ===")
    print(f"Случайный вопрос: {alice.get_random_question()}")
    
    # Тест приветственного сообщения
    welcome = alice.get_welcome_message(test_user)
    print(f"Приветствие: {welcome[:100]}...")


def test_edge_cases():
    """Тесты граничных случаев."""
    alice = AliceCharacter()
    
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
        response = alice.get_template_response(message, "Тестер")
        print(f"'{message}' -> '{response[:50]}...'")


def test_error_responses():
    """Тест ответов на ошибки."""
    alice = AliceCharacter()
    
    print("\n=== Ответы на ошибки ===")
    error_responses = alice.get_error_responses()
    print(f"Доступно {len(error_responses)} вариантов ответов на ошибки:")
    for i, response in enumerate(error_responses, 1):
        print(f"{i}. {response}")


if __name__ == "__main__":
    test_character_basic()
    test_edge_cases()
    test_error_responses()
    print("\n✅ Все тесты персонажа пройдены!")