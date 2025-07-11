"""Базовый генератор изображений."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ImagePrompt:
    """Промпт для генерации изображения."""
    text: str
    negative_prompt: Optional[str] = None
    style: Optional[str] = None
    size: tuple = (512, 512)
    steps: int = 20
    cfg_scale: float = 7.5
    seed: Optional[int] = None

@dataclass
class GeneratedImage:
    """Результат генерации изображения."""
    image_path: Path
    prompt: ImagePrompt
    metadata: Dict[str, Any]
    generation_time: float
    
class BaseImageGenerator(ABC):
    """Базовый генератор изображений."""
    
    def __init__(self, model_path: str, output_dir: str, **kwargs):
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.config = kwargs
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Инициализирует генератор."""
        pass
    
    @abstractmethod
    async def generate(self, prompt: ImagePrompt) -> GeneratedImage:
        """Генерирует изображение."""
        pass
    
    @abstractmethod
    def get_available_styles(self) -> List[str]:
        """Возвращает доступные стили."""
        pass
    
    def validate_prompt(self, prompt: ImagePrompt) -> bool:
        """Валидирует промпт."""
        if not prompt.text or len(prompt.text.strip()) < 3:
            return False
        
        # Проверка на неподходящий контент
        forbidden_words = ["nsfw", "nude", "explicit"]
        text_lower = prompt.text.lower()
        
        return not any(word in text_lower for word in forbidden_words)