#!/usr/bin/env python3
"""
CLI утилита для выбора модели Ollama.
Можно использовать независимо от бота.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.model_selector import ModelSelector, select_model_cli


def main():
    """Главная функция CLI."""
    print("🤖 Селектор моделей Ollama\n")
    
    try:
        # Создаем селектор
        selector = ModelSelector()
        
        if len(sys.argv) > 1:
            # Режим поиска модели
            query = " ".join(sys.argv[1:])
            
            if query == "--list":
                # Просто показать список
                print(selector.display_models())
                return
            
            # Поиск модели
            found = selector.find_model(query)
            if found:
                print(f"✅ Найдена модель: {found.name}")
                print(f"📊 Размер: {found.size_gb}")
                return
            else:
                print(f"❌ Модель '{query}' не найдена")
                print("\nДоступные модели:")
                print(selector.display_models())
                sys.exit(1)
        
        # Интерактивный режим
        selected = selector.select_interactive()
        if selected:
            print(f"\n✅ Выбрана модель: {selected}")
            
            # Сохраняем в файл для скриптов
            with open(".selected_model", "w") as f:
                f.write(selected)
            
            print("💾 Модель сохранена в .selected_model")
        else:
            print("❌ Модель не выбрана")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()