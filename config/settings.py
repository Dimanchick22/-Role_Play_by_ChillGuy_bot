# config/settings.py
"""Центральная конфигурация приложения."""

import os
from typing import Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TelegramConfig:
    """Конфигурация Telegram."""
    bot_token: str
    webhook_url: Optional[str] = None
    max_connections: int = 40

@dataclass 
class LLMConfig:
    """Конфигурация LLM."""
    provider: str = "ollama"  # ollama, openai, anthropic
    model_name: str = "auto"
    max_history: int = 10
    temperature: float = 0.7
    max_tokens: int = 200
    auto_select: bool = True

@dataclass
class ImageConfig:
    """Конфигурация генерации изображений."""
    enabled: bool = False
    provider: str = "stable_diffusion"  # stable_diffusion, dall_e_mini
    model_path: str = "runwayml/stable-diffusion-v1-5"
    output_dir: str = "data/generated_images"
    max_size: tuple = field(default_factory=lambda: (512, 512))
    safety_check: bool = True

@dataclass
class StorageConfig:
    """Конфигурация хранилища."""
    type: str = "memory"  # memory, file, redis
    data_dir: str = "data"
    max_conversations: int = 1000

@dataclass
class AppConfig:
    """Основная конфигурация приложения."""
    # Обязательные поля (без значений по умолчанию)
    telegram: TelegramConfig
    
    # Опциональные поля (со значениями по умолчанию)
    debug: bool = False
    log_level: str = "INFO"
    rate_limit: int = 60  # сообщений в минуту
    llm: LLMConfig = field(default_factory=LLMConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

def load_config() -> AppConfig:
    """Загружает конфигурацию из переменных окружения."""
    
    # Проверяем обязательные параметры
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
    
    return AppConfig(
        # Обязательные поля
        telegram=TelegramConfig(
            bot_token=bot_token,
            webhook_url=os.getenv("WEBHOOK_URL"),
            max_connections=int(os.getenv("MAX_CONNECTIONS", "40"))
        ),
        
        # Опциональные поля
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        rate_limit=int(os.getenv("RATE_LIMIT", "60")),
        
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "ollama"),
            model_name=os.getenv("LLM_MODEL", "auto"),
            max_history=int(os.getenv("MAX_HISTORY", "10")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "200")),
            auto_select=os.getenv("LLM_AUTO_SELECT", "true").lower() == "true"
        ),
        
        image=ImageConfig(
            enabled=os.getenv("IMAGE_GENERATION", "false").lower() == "true",
            provider=os.getenv("IMAGE_PROVIDER", "stable_diffusion"),
            model_path=os.getenv("IMAGE_MODEL", "runwayml/stable-diffusion-v1-5"),
            output_dir=os.getenv("IMAGE_OUTPUT_DIR", "data/generated_images"),
            safety_check=os.getenv("IMAGE_SAFETY_CHECK", "true").lower() == "true"
        ),
        
        storage=StorageConfig(
            type=os.getenv("STORAGE_TYPE", "memory"),
            data_dir=os.getenv("DATA_DIR", "data"),
            max_conversations=int(os.getenv("MAX_CONVERSATIONS", "1000"))
        )
    )