"""Селектор моделей Ollama."""

import logging
from typing import List, Optional, Dict, Any
import ollama

logger = logging.getLogger(__name__)


class ModelInfo:
    """Информация о модели."""
    
    def __init__(self, name: str, size: int = 0, modified: str = ""):
        self.name = name
        self.size = size
        self.modified = modified
    
    @property
    def size_gb(self) -> str:
        """Размер в GB."""
        if self.size > 0:
            return f"{self.size / (1024**3):.1f} GB"
        return "Неизвестно"
    
    @property
    def display_name(self) -> str:
        """Красивое отображение."""
        base_name = self.name.split(':')[0]
        tag = self.name.split(':')[1] if ':' in self.name else 'latest'
        return f"{base_name} ({tag})"
    
    def __str__(self) -> str:
        return f"{self.display_name} - {self.size_gb}"


class ModelSelector:
    """Класс для выбора модели Ollama."""
    
    def __init__(self):
        self.available_models: List[ModelInfo] = []
        self._scan_models()
    
    def _scan_models(self) -> None:
        """Сканирует доступные модели."""
        try:
            logger.info("Сканирование доступных моделей Ollama...")
            
            models_response = ollama.list()
            
            # Обрабатываем разные форматы ответа
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                logger.error(f"Неизвестный формат ответа: {type(models_response)}")
                return
            
            # Парсим модели
            for model in models_list:
                try:
                    model_info = self._parse_model(model)
                    if model_info:
                        self.available_models.append(model_info)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга модели {model}: {e}")
            
            logger.info(f"Найдено моделей: {len(self.available_models)}")
            
        except Exception as e:
            logger.error(f"Ошибка сканирования моделей: {e}")
            raise
    
    def _parse_model(self, model: Any) -> Optional[ModelInfo]:
        """Парсит информацию о модели."""
        # Извлекаем имя
        name = None
        if hasattr(model, 'model'):
            name = model.model
        elif hasattr(model, 'name'):
            name = model.name
        elif isinstance(model, dict):
            name = model.get('model') or model.get('name')
        
        if not name:
            return None
        
        # Извлекаем размер
        size = 0
        if hasattr(model, 'size'):
            size = model.size or 0
        elif isinstance(model, dict) and 'size' in model:
            size = model['size'] or 0
        
        # Извлекаем дату
        modified = ""
        if hasattr(model, 'modified_at'):
            modified = str(model.modified_at) if model.modified_at else ""
        elif isinstance(model, dict) and 'modified_at' in model:
            modified = str(model['modified_at']) if model['modified_at'] else ""
        
        return ModelInfo(name, size, modified)
    
    def get_models(self) -> List[ModelInfo]:
        """Возвращает список моделей."""
        return self.available_models
    
    def get_model_names(self) -> List[str]:
        """Возвращает только имена моделей."""
        return [model.name for model in self.available_models]
    
    def find_model(self, query: str) -> Optional[ModelInfo]:
        """Ищет модель по запросу."""
        query_lower = query.lower()
        
        # Точное совпадение
        for model in self.available_models:
            if model.name.lower() == query_lower:
                return model
        
        # Частичное совпадение
        for model in self.available_models:
            if query_lower in model.name.lower():
                return model
        
        return None
    
    def get_recommended_model(self) -> Optional[ModelInfo]:
        """Возвращает рекомендуемую модель."""
        if not self.available_models:
            return None
        
        # Приоритет рекомендуемых моделей
        preferred = [
            'llama3.2:3b',
            'llama3.2:1b', 
            'llama3.2',
            'llama3.1:8b',
            'llama3.1',
            'mistral:7b',
            'mistral',
            'qwen2.5:7b',
            'qwen2.5',
            'dolphin-llama3',
            'dolphin3'
        ]
        
        # Ищем по приоритету
        for pref in preferred:
            for model in self.available_models:
                if pref.lower() in model.name.lower():
                    return model
        
        # Возвращаем первую доступную
        return self.available_models[0]
    
    def display_models(self) -> str:
        """Форматированный список моделей."""
        if not self.available_models:
            return "❌ Модели не найдены"
        
        lines = ["📋 Доступные модели Ollama:\n"]
        
        for i, model in enumerate(self.available_models, 1):
            lines.append(f"{i:2d}. {model}")
        
        recommended = self.get_recommended_model()
        if recommended:
            lines.append(f"\n⭐ Рекомендуемая: {recommended.display_name}")
        
        return "\n".join(lines)
    
    def select_interactive(self) -> Optional[str]:
        """Интерактивный выбор модели."""
        if not self.available_models:
            print("❌ Модели не найдены!")
            return None
        
        print(self.display_models())
        print()
        
        while True:
            try:
                choice = input("Выберите модель (номер или Enter для рекомендуемой): ").strip()
                
                # Пустой ввод - рекомендуемая модель
                if not choice:
                    recommended = self.get_recommended_model()
                    if recommended:
                        return recommended.name
                    continue
                
                # Проверяем номер
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(self.available_models):
                        return self.available_models[index].name
                    else:
                        print(f"❌ Номер должен быть от 1 до {len(self.available_models)}")
                        continue
                
                # Поиск по имени
                found = self.find_model(choice)
                if found:
                    return found.name
                else:
                    print(f"❌ Модель '{choice}' не найдена")
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 Отмена выбора")
                return None
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                continue
    
    def validate_model(self, model_name: str) -> bool:
        """Проверяет, что модель доступна."""
        return any(model.name == model_name for model in self.available_models)


def select_model_cli() -> Optional[str]:
    """CLI интерфейс для выбора модели."""
    try:
        selector = ModelSelector()
        return selector.select_interactive()
    except Exception as e:
        print(f"❌ Ошибка подключения к Ollama: {e}")
        print("\nПроверьте:")
        print("1. Запущен ли сервер Ollama")
        print("2. Установлены ли модели (ollama pull <model>)")
        return None


if __name__ == "__main__":
    # Тест селектора
    model = select_model_cli()
    if model:
        print(f"✅ Выбрана модель: {model}")
    else:
        print("❌ Модель не выбрана")