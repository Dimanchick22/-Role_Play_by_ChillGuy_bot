"""Обработчики команд - обновленная версия с роль-плеем."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from handlers.base_handler import ImprovedBaseHandler
from core.registry import registry
from models.base import MessageRole

logger = logging.getLogger(__name__)

class CommandHandlers(ImprovedBaseHandler):
    """Обработчики команд бота."""
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        user = self.get_user_from_update(update)
        
        # Получаем сервис персонажа через улучшенный метод
        character_service = self.get_character_service()
        
        if character_service:
            welcome_message = character_service.get_welcome_message(user)
        else:
            welcome_message = f"Привет, {user.first_name}! 🌟 Я Алиса, твоя виртуальная помощница!"
        
        await self.safe_reply(update, welcome_message)
        await self.log_interaction(update, "start_command")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        # Проверяем доступные сервисы через улучшенные методы
        commands = [
            "/start - Знакомство со мной",
            "/help - Эта справка",
            "/info - Информация обо мне"
        ]
        
        # Роль-плей команды (если доступны)
        character_service = self.get_character_service()
        if character_service and hasattr(character_service, 'mood'):
            commands.extend([
                "/mood - Изменить мое настроение",
                "/scene - Изменить сцену общения",
                "/rpstats - Статистика роль-плея"
            ])
        
        if self.is_llm_available():
            commands.extend([
                "/clear - Очистить историю диалога",
                "/stats - Статистика работы"
            ])
        
        if self.is_image_generation_available():
            commands.extend([
                "/image <описание> - Генерация изображения"
            ])
        
        # Определяем тип бота
        if character_service and hasattr(character_service, 'mood'):
            bot_type = "🎭 Роль-плей режим: живое общение с генерацией изображений"
            extra_info = "\n💡 Я всегда отвечаю с вопросом, чтобы поддержать беседу!"
        else:
            bot_type = "🤖 Обычный режим"
            extra_info = ""
        
        help_text = f"""🤖 Справка по боту

Привет! Я Алиса, твой виртуальный помощник!

📋 Доступные команды:
{chr(10).join(commands)}

💬 Просто пиши мне сообщения, и я отвечу!

{bot_type}
{'🧠 Умные ответы через LLM активны' if self.is_llm_available() else '📝 Работаю в режиме шаблонов'}
{'🎨 Генерация изображений к каждому ответу' if self.is_image_generation_available() else ''}{extra_info}"""
        
        await self.safe_reply(update, help_text)
        await self.log_interaction(update, "help_command")
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info."""
        character_service = self.get_character_service()
        
        if character_service and hasattr(character_service, 'get_info'):
            info_text = character_service.get_info()
        elif character_service and hasattr(character_service, 'mood'):
            # Роль-плей персонаж
            mood = getattr(character_service, 'mood', 'веселая')
            scene = getattr(character_service, 'current_scene', 'обычная беседа')
            
            info_text = f"""🎭 Привет! Меня зовут Алиса!

О себе:
• Возраст: 19 лет
• Характер: {character_service.personality}
• Настроение сейчас: {mood}
• Текущая сцена: {scene}
• Увлечения: музыка, фильмы, фотография

Я обожаю живое общение и всегда поддерживаю диалог вопросами! 🤗

Давай поговорим о чем-то интересном! ✨"""
        else:
            info_text = """🌟 Привет! Меня зовут Алиса!

О себе:
• Дружелюбная и энергичная помощница
• Люблю общаться и помогать
• Всегда готова поддержать
• Обожаю узнавать новое

Давай дружить! 🤗"""
        
        await self.safe_reply(update, info_text)
        await self.log_interaction(update, "info_command")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats."""
        # Получаем статус всех сервисов
        services_health = self.get_services_status_summary()
        
        stats_lines = ["📊 Статистика сервисов:\n"]
        
        # LLM статистика
        if services_health['llm']:
            llm_service = self.get_llm_service()
            model_name = getattr(llm_service, 'active_model', 
                               getattr(llm_service, 'model_name', 'неизвестно'))
            # Проверяем роль-плей настройки
            if hasattr(llm_service, 'roleplay_settings'):
                temp = llm_service.roleplay_settings.get('temperature', 'неизвестно')
                stats_lines.append(f"🧠 LLM: ✅ {model_name} (роль-плей, temp: {temp})")
            else:
                stats_lines.append(f"🧠 LLM: ✅ {model_name}")
        else:
            stats_lines.append("🧠 LLM: ❌ Недоступно")
        
        # Статистика изображений
        if services_health['image']:
            image_service = self.get_image_service()
            model_path = getattr(image_service, 'model_path', 'неизвестно')
            stats_lines.append(f"🎨 Изображения: ✅ {model_path}")
        else:
            stats_lines.append("🎨 Изображения: ❌ Неактивно")
        
        # Статистика хранилища
        if services_health['storage']:
            storage_service = self.get_storage_service()
            if hasattr(storage_service, 'get_stats'):
                try:
                    storage_stats = storage_service.get_stats()
                    total_conversations = storage_stats.get('total_conversations', 0)
                    total_messages = storage_stats.get('total_messages', 0)
                    stats_lines.append(f"💾 Хранилище: ✅ {total_conversations} диалогов, {total_messages} сообщений")
                except:
                    stats_lines.append("💾 Хранилище: ⚠️ Ошибка получения статистики")
            else:
                stats_lines.append("💾 Хранилище: ✅ Активно")
        else:
            stats_lines.append("💾 Хранилище: ❌ Не найден")
        
        stats_text = "\n".join(stats_lines)
        await self.safe_reply(update, stats_text)
        await self.log_interaction(update, "stats_command")
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear - очистить историю."""
        user = self.get_user_from_update(update)
        
        storage_service = self.get_storage_service()
        if storage_service and hasattr(storage_service, 'clear_conversation'):
            try:
                storage_service.clear_conversation(user.id)
                await self.safe_reply(update, "🧹 История диалога очищена!")
                await self.log_interaction(update, "history_cleared")
            except Exception as e:
                logger.error(f"Ошибка очистки истории: {e}")
                await self.safe_reply(update, self.get_error_response("service_error"))
        else:
            await self.safe_reply(update, "❌ Сервис хранилища недоступен")
    
    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /image <prompt>."""
        if not context.args:
            await self.safe_reply(
                update,
                "📝 Использование: /image <описание>\n\n"
                "Пример: /image красивый закат над морем"
            )
            return
        
        # Проверяем сервис генерации изображений
        if not self.is_image_generation_available():
            await self.safe_reply(update, "❌ Генерация изображений недоступна")
            return
        
        image_service = self.get_image_service()
        prompt_text = " ".join(context.args)
        
        # Валидация промпта
        if not self.validate_message_length(prompt_text, 500):
            await self.safe_reply(update, "❌ Описание слишком длинное (максимум 500 символов)")
            return
        
        # Очищаем ввод
        prompt_text = self.sanitize_text_input(prompt_text)
        
        # Показываем статус генерации
        status_message = await update.message.reply_text(
            "🎨 Генерирую изображение... Это может занять несколько минут"
        )
        
        try:
            # Создаем промпт
            from services.image.base_generator import ImagePrompt
            prompt = ImagePrompt(
                text=prompt_text,
                size=(512, 512),
                steps=20
            )
            
            # Генерируем изображение
            result = await image_service.generate(prompt)
            
            # Отправляем результат
            with open(result.image_path, 'rb') as image_file:
                await update.message.reply_photo(
                    photo=image_file,
                    caption=f"🎨 Промпт: {prompt_text}\n⏱️ Время: {result.generation_time:.1f}с"
                )
            
            # Удаляем статусное сообщение
            await status_message.delete()
            
            await self.log_interaction(
                update, "image_generated", 
                prompt=prompt_text, 
                time=result.generation_time
            )
            
        except Exception as e:
            await status_message.edit_text(f"❌ Ошибка генерации: {str(e)}")
            logger.error(f"Ошибка генерации изображения: {e}")
            await self.log_interaction(update, "image_generation_failed", error=str(e))


class RoleplayCommandHandlers:
    """Дополнительные команды для роль-плея."""
    
    async def mood_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mood - изменить настроение персонажа."""
        character_service = registry.get('character', None)
        
        if not character_service:
            await update.message.reply_text("❌ Персонаж недоступен")
            return
        
        if not context.args:
            current_mood = getattr(character_service, 'mood', 'неизвестно')
            await update.message.reply_text(
                f"🎭 Текущее настроение: {current_mood}\n\n"
                "Доступные настроения:\n"
                "• веселая 😊\n• грустная 😢\n• игривая 😏\n• взволнованная 😮\n• задумчивая 🤔\n\n"
                "Использование: /mood веселая"
            )
            return
        
        new_mood = context.args[0].lower()
        valid_moods = ["веселая", "грустная", "игривая", "взволнованная", "задумчивая"]
        
        if new_mood not in valid_moods:
            await update.message.reply_text(
                f"❌ Неизвестное настроение: {new_mood}\n"
                f"Доступные: {', '.join(valid_moods)}"
            )
            return
        
        # Меняем настроение
        character_service.mood = new_mood
        
        # Генерируем ответ в новом настроении
        mood_responses = {
            "веселая": ("Ура! Теперь я в отличном настроении! 😊 Давай поговорим о чем-то классном!", 
                       "cheerful young woman, bright smile, happy mood, energetic"),
            "грустная": ("Хм, стало немного грустно... 😢 Может, поговорим о чем-то душевном?", 
                        "melancholic young woman, thoughtful expression, soft lighting"),
            "игривая": ("Ой, я в игривом настроении! 😏 Давай придумаем что-то веселое!", 
                       "playful young woman, mischievous smile, flirtatious mood"),
            "взволнованная": ("Ого, я так взволнована! 😮 Что-то интересное происходит!", 
                            "excited young woman, surprised expression, energetic gesture"),
            "задумчивая": ("Мм, я в задумчивом настроении... 🤔 О чем поразмышляем?", 
                          "contemplative young woman, thoughtful pose, philosophical mood")
        }
        
        response, image_prompt = mood_responses[new_mood]
        await update.message.reply_text(response)
        
        # Генерируем изображение для нового настроения
        try:
            await self._generate_mood_image(update, context, image_prompt, new_mood)
        except Exception as e:
            logger.error(f"Ошибка генерации изображения настроения: {e}")
    
    async def scene_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /scene - изменить сцену роль-плея."""
        character_service = registry.get('character', None)
        
        if not character_service:
            await update.message.reply_text("❌ Персонаж недоступен")
            return
        
        if not context.args:
            current_scene = getattr(character_service, 'current_scene', 'неизвестно')
            await update.message.reply_text(
                f"🎬 Текущая сцена: {current_scene}\n\n"
                "Доступные сцены:\n"
                "• кафе - уютная беседа в кафе\n"
                "• парк - прогулка в парке\n"
                "• дома - домашняя обстановка\n"
                "• офис - рабочая встреча\n"
                "• путешествие - в дороге\n\n"
                "Использование: /scene кафе"
            )
            return
        
        new_scene = " ".join(context.args).lower()
        
        scene_responses = {
            "кафе": ("Отлично! Представь, мы сидим в уютном кафе ☕ Что будешь заказывать?", 
                    "young woman in cozy cafe, warm lighting, coffee atmosphere"),
            "парк": ("Как здорово! Мы гуляем по парку 🌳 Такая прекрасная погода, не правда ли?", 
                    "young woman walking in park, natural lighting, outdoor setting"),
            "дома": ("Мм, домашняя обстановка! 🏠 Устраивайся поудобнее, что будем делать?", 
                    "young woman at home, cozy interior, relaxed atmosphere"),
            "офис": ("Деловая встреча! 💼 Надеюсь, у тебя все хорошо с работой?", 
                    "young woman in office setting, professional atmosphere"),
            "путешествие": ("Ого, мы путешествуем! ✈️ Куда направляемся? Так захватывающе!", 
                           "young woman traveling, adventure mood, journey atmosphere")
        }
        
        if new_scene not in scene_responses:
            await update.message.reply_text(
                f"❌ Неизвестная сцена: {new_scene}\n"
                f"Доступные: {', '.join(scene_responses.keys())}"
            )
            return
        
        # Меняем сцену
        character_service.current_scene = new_scene
        response, image_prompt = scene_responses[new_scene]
        
        await update.message.reply_text(response)
        
        # Генерируем изображение для новой сцены
        try:
            await self._generate_scene_image(update, context, image_prompt, new_scene)
        except Exception as e:
            logger.error(f"Ошибка генерации изображения сцены: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Расширенная команда /rpstats для роль-плея."""
        # Получаем сервисы
        character_service = registry.get('character', None)
        llm_service = registry.get('llm', None)
        storage_service = registry.get('storage', None)
        image_service = registry.get('image', None)
        
        stats_lines = ["🎭 Статистика роль-плея:\n"]
        
        # Информация о персонаже
        if character_service:
            mood = getattr(character_service, 'mood', 'неизвестно')
            scene = getattr(character_service, 'current_scene', 'неизвестно')
            relationship = getattr(character_service, 'relationship_level', 'неизвестно')
            
            stats_lines.append(f"👩 Персонаж: ✅ Алиса")
            stats_lines.append(f"  • Настроение: {mood}")
            stats_lines.append(f"  • Сцена: {scene}")
            stats_lines.append(f"  • Отношения: {relationship}")
        else:
            stats_lines.append("👩 Персонаж: ❌ Недоступен")
        
        # LLM статистика
        if llm_service and hasattr(llm_service, 'get_roleplay_stats'):
            llm_stats = llm_service.get_roleplay_stats()
            stats_lines.append(f"🧠 LLM: ✅ {llm_stats.get('model', 'неизвестно')}")
            stats_lines.append(f"  • Температура: {llm_stats.get('temperature', 'неизвестно')}")
            stats_lines.append(f"  • Макс. токенов: {llm_stats.get('max_tokens', 'неизвестно')}")
        elif llm_service:
            model_name = getattr(llm_service, 'active_model', 
                               getattr(llm_service, 'model_name', 'неизвестно'))
            stats_lines.append(f"🧠 LLM: ✅ {model_name}")
        else:
            stats_lines.append("🧠 LLM: ❌ Недоступно (режим шаблонов)")
        
        # Статистика изображений
        if image_service and getattr(image_service, 'is_initialized', False):
            model_path = getattr(image_service, 'model_path', 'неизвестно')
            stats_lines.append(f"🎨 Изображения: ✅ {model_path}")
        else:
            stats_lines.append("🎨 Изображения: ❌ Недоступно")
        
        # Статистика диалога
        if storage_service:
            try:
                user = update.effective_user
                conversation = storage_service.get_conversation(user.id)
                message_count = len(conversation.messages)
                user_messages = len([m for m in conversation.messages if m.role == MessageRole.USER])
                
                stats_lines.append(f"💬 Диалог:")
                stats_lines.append(f"  • Всего сообщений: {message_count}")
                stats_lines.append(f"  • От пользователя: {user_messages}")
                stats_lines.append(f"  • Создан: {conversation.created_at.strftime('%d.%m.%Y %H:%M')}")
            except Exception:
                stats_lines.append("💬 Диалог: ❌ Ошибка получения статистики")
        else:
            stats_lines.append("💬 Диалог: ❌ Хранилище недоступно")
        
        stats_text = "\n".join(stats_lines)
        await update.message.reply_text(stats_text)
    
    async def _generate_mood_image(self, update, context, image_prompt, mood):
        """Генерирует изображение для настроения."""
        image_service = registry.get('image', None)
        if not image_service or not getattr(image_service, 'is_initialized', False):
            return
        
        try:
            from services.image.base_generator import ImagePrompt
            
            prompt = ImagePrompt(
                text=f"{image_prompt}, {mood} mood, high quality, portrait",
                negative_prompt="ugly, distorted, blurry, low quality",
                size=(512, 512),
                steps=20
            )
            
            result = await image_service.generate(prompt)
            
            with open(result.image_path, 'rb') as image_file:
                await update.message.reply_photo(
                    photo=image_file,
                    caption=f"🎭 Настроение: {mood}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка генерации изображения настроения: {e}")
    
    async def _generate_scene_image(self, update, context, image_prompt, scene):
        """Генерирует изображение для сцены."""
        image_service = registry.get('image', None)
        if not image_service or not getattr(image_service, 'is_initialized', False):
            return
        
        try:
            from services.image.base_generator import ImagePrompt
            
            prompt = ImagePrompt(
                text=f"{image_prompt}, {scene} setting, cinematic, high quality",
                negative_prompt="ugly, distorted, blurry, low quality",
                size=(512, 512),
                steps=25  # Больше шагов для сцен
            )
            
            result = await image_service.generate(prompt)
            
            with open(result.image_path, 'rb') as image_file:
                await update.message.reply_photo(
                    photo=image_file,
                    caption=f"🎬 Сцена: {scene}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка генерации изображения сцены: {e}")