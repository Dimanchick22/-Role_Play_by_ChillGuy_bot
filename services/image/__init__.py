"""Пакет сервисов генерации изображений."""

from .base_generator import BaseImageGenerator, ImagePrompt, GeneratedImage
from .stable_diffusion import StableDiffusionGenerator

__all__ = [
    "BaseImageGenerator", 
    "ImagePrompt", 
    "GeneratedImage",
    "StableDiffusionGenerator"
]