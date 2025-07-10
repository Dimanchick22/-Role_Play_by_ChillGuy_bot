"""Конфигурация бота."""

import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """Класс конфигурации."""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # LLM
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "auto")  # "auto" для автовыбора
    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "10"))
    INTERACTIVE_MODEL_SELECT: bool = os.getenv("INTERACTIVE_MODEL_SELECT", "true").lower() == "true"
    
    # Режимы
    USE_LLM: bool = os.getenv("USE_LLM", "true").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> None:
        """Проверяет обязательные настройки."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
    
    @classmethod
    def get_log_level(cls) -> str:
        """Возвращает уровень логирования."""
        return "DEBUG" if cls.DEBUG else "INFO"

# Проверяем конфигурацию при импорте
Config.validate()