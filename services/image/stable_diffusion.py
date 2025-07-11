"""Генератор изображений на Stable Diffusion - исправленная версия."""

import asyncio
import time
import uuid
import logging
from pathlib import Path
from typing import List, Optional

from services.image.base_generator import BaseImageGenerator, ImagePrompt, GeneratedImage

# ИСПРАВЛЕНО: Добавлен отсутствующий импорт logger
logger = logging.getLogger(__name__)

class StableDiffusionGenerator(BaseImageGenerator):
    """Генератор на основе Stable Diffusion."""
    
    def __init__(self, model_path: str, output_dir: str, **kwargs):
        super().__init__(model_path, output_dir, **kwargs)
        self.pipe = None
        self.device = kwargs.get('device', 'cpu')
    
    async def initialize(self) -> bool:
        """Инициализирует генератор."""
        try:
            logger.info("🎨 Начало инициализации Stable Diffusion...")
            
            # Ленивый импорт для экономии памяти
            from diffusers import StableDiffusionPipeline
            import torch
            
            # Определяем устройство
            if self.device == 'auto':
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            logger.info(f"🔧 Загружаем модель {self.model_path} на {self.device}...")
            
            # Загружаем модель
            self.pipe = StableDiffusionPipeline.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                safety_checker=None if not self.config.get('safety_check', True) else None
            )
            
            self.pipe = self.pipe.to(self.device)
            
            # Оптимизации для CPU/GPU
            if self.device == 'cuda':
                self.pipe.enable_memory_efficient_attention()
                logger.info("✅ Включена memory efficient attention для GPU")
            else:
                # Для CPU используем более простую оптимизацию
                try:
                    self.pipe.enable_sequential_cpu_offload()
                    logger.info("✅ Включен sequential CPU offload")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось включить CPU offload: {e}")
                    logger.info("💡 Работаем без оптимизации CPU (для включения установите: pip install accelerate)")
            
            # Создаем выходную директорию
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.is_initialized = True
            logger.info(f"✅ Stable Diffusion инициализован на {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Stable Diffusion: {e}")
            self.is_initialized = False
            return False
    
    async def generate(self, prompt: ImagePrompt) -> GeneratedImage:
        """Генерирует изображение."""
        if not self.is_initialized:
            raise RuntimeError("Генератор не инициализирован")
        
        if not self.validate_prompt(prompt):
            raise ValueError("Недопустимый промпт")
        
        start_time = time.time()
        
        try:
            logger.info(f"🎨 Генерация изображения: '{prompt.text[:50]}...'")
            
            # Генерируем изображение в отдельном потоке
            image = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, prompt
            )
            
            # Сохраняем изображение
            image_path = self._save_image(image, prompt)
            
            generation_time = time.time() - start_time
            logger.info(f"✅ Изображение создано за {generation_time:.1f}с")
            
            return GeneratedImage(
                image_path=image_path,
                prompt=prompt,
                metadata={
                    "model": self.model_path,
                    "device": self.device,
                    "seed": prompt.seed
                },
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации изображения: {e}")
            raise
    
    def get_available_styles(self) -> List[str]:
        """Возвращает доступные стили."""
        return [
            "realistic", "anime", "cartoon", "oil_painting",
            "watercolor", "sketch", "digital_art", "photographic"
        ]
    
    def _generate_sync(self, prompt: ImagePrompt):
        """Синхронная генерация изображения."""
        # Формируем полный промпт
        full_prompt = self._build_full_prompt(prompt)
        
        logger.debug(f"Полный промпт: {full_prompt}")
        
        # Генерируем
        result = self.pipe(
            prompt=full_prompt,
            negative_prompt=prompt.negative_prompt,
            width=prompt.size[0],
            height=prompt.size[1],
            num_inference_steps=prompt.steps,
            guidance_scale=prompt.cfg_scale,
            generator=self._get_generator(prompt.seed)
        )
        
        return result.images[0]
    
    def _build_full_prompt(self, prompt: ImagePrompt) -> str:
        """Строит полный промпт с учетом стиля."""
        parts = [prompt.text]
        
        if prompt.style:
            style_modifiers = {
                "realistic": "photorealistic, high quality, detailed",
                "anime": "anime style, manga, japanese animation",
                "cartoon": "cartoon style, animated, colorful",
                "oil_painting": "oil painting, classical art, brushstrokes",
                "watercolor": "watercolor painting, soft colors, artistic",
                "sketch": "pencil sketch, black and white, artistic drawing",
                "digital_art": "digital art, modern, clean lines",
                "photographic": "photograph, camera shot, professional"
            }
            
            if prompt.style in style_modifiers:
                parts.append(style_modifiers[prompt.style])
        
        return ", ".join(parts)
    
    def _get_generator(self, seed: Optional[int]):
        """Создает генератор с seed."""
        import torch
        if seed is not None:
            return torch.Generator(device=self.device).manual_seed(seed)
        return None
    
    def _save_image(self, image, prompt: ImagePrompt) -> Path:
        """Сохраняет изображение."""
        # Генерируем уникальное имя файла
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        filename = f"img_{timestamp}_{unique_id}.png"
        
        image_path = self.output_dir / filename
        image.save(image_path)
        
        logger.info(f"💾 Изображение сохранено: {image_path}")
        return image_path
    
    async def cleanup(self):
        """Очистка ресурсов."""
        logger.info("🧹 Очистка Stable Diffusion...")
        if self.pipe is not None:
            # Освобождаем GPU память
            if hasattr(self.pipe, 'to'):
                self.pipe.to('cpu')
            del self.pipe
            self.pipe = None
            
            # Очищаем CUDA кеш если используется GPU
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
        
        self.is_initialized = False
        logger.debug("✅ Stable Diffusion очищен")