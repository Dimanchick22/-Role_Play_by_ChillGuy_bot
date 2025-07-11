"""Генератор изображений на Stable Diffusion - исправленная версия с псевдонимом."""

import asyncio
import time
import uuid
import logging
from pathlib import Path
from typing import List, Optional

from services.image.base_generator import BaseImageGenerator, ImagePrompt, GeneratedImage

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


class EnhancedStableDiffusionGenerator(BaseImageGenerator):
    """Улучшенный генератор с поддержкой кастомных моделей."""
    
    def __init__(self, model_path: str, output_dir: str, **kwargs):
        super().__init__(model_path, output_dir, **kwargs)
        self.pipe = None
        self.device = kwargs.get('device', 'auto')
        self.custom_model_configs = {
            'one-obsession': {
                'repo_id': 'stablediffusionapi/one-obsession-12-2-3d-details',
                'fallback': 'runwayml/stable-diffusion-v1-5',
                'optimal_steps': 25,
                'optimal_cfg': 8.0,
                'style_prefix': '3D detailed, high quality, obsession style',
                'negative_base': 'low quality, blurry, distorted, ugly, bad anatomy'
            },
            'dolphin-style': {
                'style_prefix': 'dolphin art style, creative, artistic',
                'optimal_steps': 20,
                'optimal_cfg': 7.5
            }
        }
    
    async def initialize(self) -> bool:
        """Инициализирует генератор с кастомной моделью."""
        try:
            logger.info(f"🎨 Инициализация кастомного генератора...")
            logger.info(f"🎯 Целевая модель: {self.model_path}")
            
            # Ленивый импорт
            from diffusers import StableDiffusionPipeline
            import torch
            
            # Определяем устройство
            if self.device == 'auto':
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # Пытаемся загрузить кастомную модель
            model_loaded = await self._try_load_custom_model()
            
            if not model_loaded:
                logger.warning("⚠️ Кастомная модель недоступна, используем fallback")
                model_loaded = await self._load_fallback_model()
            
            if model_loaded:
                self._setup_optimizations()
                self.output_dir.mkdir(parents=True, exist_ok=True)
                self.is_initialized = True
                logger.info(f"✅ Генератор инициализирован на {self.device}")
                return True
            else:
                logger.error("❌ Не удалось загрузить ни одну модель")
                return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации кастомного генератора: {e}")
            self.is_initialized = False
            return False
    
    async def _try_load_custom_model(self) -> bool:
        """Пытается загрузить кастомную модель."""
        try:
            from diffusers import StableDiffusionPipeline
            import torch
            
            # Проверяем известные кастомные модели
            model_config = None
            model_repo = self.model_path
            
            for key, config in self.custom_model_configs.items():
                if key in self.model_path.lower() or config.get('repo_id') == self.model_path:
                    model_config = config
                    model_repo = config.get('repo_id', self.model_path)
                    break
            
            logger.info(f"🔄 Загружаем кастомную модель: {model_repo}")
            
            # Загружаем модель
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_repo,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                safety_checker=None if not self.config.get('safety_check', True) else None,
                use_safetensors=True,
                variant="fp16" if self.device == 'cuda' else None
            )
            
            self.pipe = self.pipe.to(self.device)
            self.current_model_config = model_config
            
            logger.info(f"✅ Кастомная модель загружена: {model_repo}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить кастомную модель: {e}")
            return False
    
    async def _load_fallback_model(self) -> bool:
        """Загружает fallback модель."""
        try:
            from diffusers import StableDiffusionPipeline
            import torch
            
            # Определяем fallback модель
            fallback_model = "runwayml/stable-diffusion-v1-5"
            
            if hasattr(self, 'current_model_config') and self.current_model_config:
                fallback_model = self.current_model_config.get('fallback', fallback_model)
            
            logger.info(f"🔄 Загружаем fallback модель: {fallback_model}")
            
            self.pipe = StableDiffusionPipeline.from_pretrained(
                fallback_model,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                safety_checker=None if not self.config.get('safety_check', True) else None
            )
            
            self.pipe = self.pipe.to(self.device)
            
            logger.info(f"✅ Fallback модель загружена: {fallback_model}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки fallback модели: {e}")
            return False
    
    def _setup_optimizations(self):
        """Настраивает оптимизации для устройства."""
        try:
            if self.device == 'cuda':
                # GPU оптимизации
                if hasattr(self.pipe, 'enable_memory_efficient_attention'):
                    self.pipe.enable_memory_efficient_attention()
                    logger.info("✅ Memory efficient attention включен")
                
                if hasattr(self.pipe, 'enable_xformers_memory_efficient_attention'):
                    try:
                        self.pipe.enable_xformers_memory_efficient_attention()
                        logger.info("✅ XFormers attention включен")
                    except Exception:
                        logger.info("💡 XFormers недоступен, используем стандартный attention")
            else:
                # CPU оптимизации
                try:
                    if hasattr(self.pipe, 'enable_sequential_cpu_offload'):
                        self.pipe.enable_sequential_cpu_offload()
                        logger.info("✅ Sequential CPU offload включен")
                except Exception as e:
                    logger.warning(f"⚠️ CPU offload недоступен: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Некоторые оптимизации недоступны: {e}")
    
    async def generate(self, prompt: ImagePrompt) -> GeneratedImage:
        """Генерирует изображение с кастомными настройками."""
        if not self.is_initialized:
            raise RuntimeError("Генератор не инициализирован")
        
        if not self.validate_prompt(prompt):
            raise ValueError("Недопустимый промпт")
        
        start_time = time.time()
        
        try:
            logger.info(f"🎨 Генерация с кастомными настройками: '{prompt.text[:50]}...'")
            
            # Применяем кастомные настройки
            enhanced_prompt = self._enhance_prompt_for_model(prompt)
            
            # Генерируем изображение
            image = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, enhanced_prompt
            )
            
            # Сохраняем
            image_path = self._save_image(image, enhanced_prompt)
            
            generation_time = time.time() - start_time
            logger.info(f"✅ Кастомное изображение создано за {generation_time:.1f}с")
            
            return GeneratedImage(
                image_path=image_path,
                prompt=enhanced_prompt,
                metadata={
                    "model": self.model_path,
                    "device": self.device,
                    "custom_config": getattr(self, 'current_model_config', None),
                    "generation_time": generation_time
                },
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации кастомного изображения: {e}")
            raise
    
    def _enhance_prompt_for_model(self, prompt: ImagePrompt) -> ImagePrompt:
        """Улучшает промпт для конкретной модели."""
        enhanced_text = prompt.text
        enhanced_negative = prompt.negative_prompt or ""
        
        # Применяем настройки кастомной модели
        if hasattr(self, 'current_model_config') and self.current_model_config:
            config = self.current_model_config
            
            # Добавляем префикс стиля
            style_prefix = config.get('style_prefix', '')
            if style_prefix:
                enhanced_text = f"{style_prefix}, {enhanced_text}"
            
            # Улучшаем негативный промпт
            negative_base = config.get('negative_base', '')
            if negative_base:
                if enhanced_negative:
                    enhanced_negative = f"{negative_base}, {enhanced_negative}"
                else:
                    enhanced_negative = negative_base
            
            # Обновляем параметры генерации
            steps = config.get('optimal_steps', prompt.steps)
            cfg_scale = config.get('optimal_cfg', prompt.cfg_scale)
        else:
            steps = prompt.steps
            cfg_scale = prompt.cfg_scale
        
        return ImagePrompt(
            text=enhanced_text,
            negative_prompt=enhanced_negative,
            style=prompt.style,
            size=prompt.size,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=prompt.seed
        )
    
    def _generate_sync(self, prompt: ImagePrompt):
        """Синхронная генерация с кастомными параметрами."""
        logger.debug(f"Генерация: {prompt.text[:100]}...")
        logger.debug(f"Негатив: {prompt.negative_prompt[:100] if prompt.negative_prompt else 'Нет'}")
        logger.debug(f"Шаги: {prompt.steps}, CFG: {prompt.cfg_scale}")
        
        result = self.pipe(
            prompt=prompt.text,
            negative_prompt=prompt.negative_prompt,
            width=prompt.size[0],
            height=prompt.size[1],
            num_inference_steps=prompt.steps,
            guidance_scale=prompt.cfg_scale,
            generator=self._get_generator(prompt.seed)
        )
        
        return result.images[0]
    
    def _get_generator(self, seed: Optional[int]):
        """Создает генератор с seed."""
        import torch
        if seed is not None:
            return torch.Generator(device=self.device).manual_seed(seed)
        return None
    
    def _save_image(self, image, prompt: ImagePrompt) -> Path:
        """Сохраняет изображение с меткой модели."""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        # Добавляем информацию о модели в имя файла
        model_tag = "custom" if hasattr(self, 'current_model_config') else "standard"
        filename = f"img_{model_tag}_{timestamp}_{unique_id}.png"
        
        image_path = self.output_dir / filename
        image.save(image_path)
        
        logger.info(f"💾 Кастомное изображение сохранено: {image_path}")
        return image_path
    
    def get_available_styles(self) -> List[str]:
        """Возвращает доступные стили включая кастомные."""
        base_styles = [
            "realistic", "anime", "cartoon", "oil_painting",
            "watercolor", "sketch", "digital_art", "photographic"
        ]
        
        # Добавляем кастомные стили
        if hasattr(self, 'current_model_config') and self.current_model_config:
            base_styles.extend([
                "3d_detailed", "obsession_style", "high_contrast",
                "cinematic", "dramatic_lighting"
            ])
        
        return base_styles
    
    async def cleanup(self):
        """Очистка ресурсов кастомного генератора."""
        logger.info("🧹 Очистка кастомного генератора...")
        if self.pipe is not None:
            if hasattr(self.pipe, 'to'):
                self.pipe.to('cpu')
            del self.pipe
            self.pipe = None
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
        
        self.is_initialized = False
        logger.debug("✅ Кастомный генератор очищен")

# Добавь в конец файла services/image/stable_diffusion.py:

class LocalStableDiffusionGenerator(StableDiffusionGenerator):
    """Генератор для локальных моделей (.safetensors/.ckpt файлов)."""
    
    async def initialize(self) -> bool:
        """Инициализирует генератор с локальной моделью."""
        try:
            logger.info(f"🎨 Загрузка локальной модели: {self.model_path}")
            
            from diffusers import StableDiffusionPipeline
            import torch
            
            # Определяем устройство
            if self.device == 'auto':
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            logger.info(f"📁 Загружаем локальный файл на {self.device}...")
            
            # Загружаем из single file
            self.pipe = StableDiffusionPipeline.from_single_file(
                self.model_path,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                safety_checker=None if not self.config.get('safety_check', True) else None,
                use_safetensors=self.model_path.endswith('.safetensors'),
                load_safety_checker=False
            )
            
            self.pipe = self.pipe.to(self.device)
            
            # Оптимизации для CPU/GPU
            if self.device == 'cuda':
                try:
                    self.pipe.enable_memory_efficient_attention()
                    logger.info("✅ Memory efficient attention включен")
                except:
                    logger.info("💡 Memory efficient attention недоступен")
            else:
                try:
                    self.pipe.enable_sequential_cpu_offload()
                    logger.info("✅ Sequential CPU offload включен")
                except Exception as e:
                    logger.warning(f"⚠️ CPU offload недоступен: {e}")
            
            # Создаем выходную директорию
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.is_initialized = True
            logger.info(f"✅ Локальная модель One Obsession загружена на {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локальной модели: {e}")
            logger.info("💡 Проверь путь к файлу и формат модели")
            self.is_initialized = False
            return False
    
    def _build_full_prompt(self, prompt: ImagePrompt) -> str:
        """Строит промпт оптимизированный для One Obsession модели."""
        parts = []
        
        # Добавляем стилевые префиксы для One Obsession
        style_prefix = "3D detailed, high quality, obsession style"
        parts.append(style_prefix)
        parts.append(prompt.text)
        
        if prompt.style:
            style_modifiers = {
                "realistic": "photorealistic, highly detailed, professional",
                "anime": "anime style, detailed character design",
                "cartoon": "cartoon style, vibrant colors, detailed",
                "oil_painting": "oil painting style, artistic, detailed brushwork",
                "watercolor": "watercolor style, soft artistic colors",
                "sketch": "detailed sketch, artistic drawing",
                "digital_art": "digital art, modern style, highly detailed",
                "photographic": "photograph quality, professional lighting"
            }
            
            if prompt.style in style_modifiers:
                parts.append(style_modifiers[prompt.style])
        
        return ", ".join(parts)
    
    def _save_image(self, image, prompt: ImagePrompt) -> Path:
        """Сохраняет изображение с меткой One Obsession."""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        filename = f"img_oneobsession_{timestamp}_{unique_id}.png"
        
        image_path = self.output_dir / filename
        image.save(image_path)
        
        logger.info(f"💾 One Obsession изображение сохранено: {image_path}")
        return image_path