import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from character import Character
from llm_handler import LLMHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализируем персонажа и LLM
character = Character()
llm = LLMHandler(model_name="dolphin3:latest")  # Измени на свою модель

# Устанавливаем системный промпт для LLM
llm.set_system_prompt(character.get_llm_prompt())

# Режимы работы
USE_LLM = True  # Переключатель между LLM и шаблонными ответами

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    
    # Устанавливаем персонализированный промпт
    personalized_prompt = character.get_llm_prompt(user_name)
    llm.set_system_prompt(personalized_prompt)
    
    welcome_message = f"Привет, {user_name}! 🌟\n\n{character.get_character_info()}"
    
    if USE_LLM:
        welcome_message += "\n\n🤖 Режим: Умные ответы (LLM включена)"
    else:
        welcome_message += "\n\n📝 Режим: Шаблонные ответы"
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = f"""
🤖 Помощь по боту

Привет! Я {character.name}, твой виртуальный друг! 

Основные команды:
/start - Познакомиться со мной
/help - Показать это сообщение
/info - Узнать больше обо мне
/question - Получить случайный вопрос
/clear - Очистить историю разговора
/mode - Переключить режим ответов
/model - Информация о модели

Просто пиши мне сообщения, и я отвечу! 💬

Текущий режим: {"🤖 LLM (умные ответы)" if USE_LLM else "📝 Шаблонные ответы"}
    """
    await update.message.reply_text(help_text)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /info"""
    info_text = character.get_character_info()
    await update.message.reply_text(info_text)

async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /question"""
    question = character.get_random_question()
    await update.message.reply_text(question)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищает историю разговора"""
    user_id = update.effective_user.id
    llm.clear_history(user_id)
    await update.message.reply_text("История нашего разговора очищена! 🧹✨")

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключает режим работы бота"""
    global USE_LLM
    USE_LLM = not USE_LLM
    
    mode_text = "🤖 LLM (умные ответы)" if USE_LLM else "📝 Шаблонные ответы"
    await update.message.reply_text(f"Режим изменен на: {mode_text}")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает информацию о модели"""
    model_info = llm.get_model_info()
    info_text = f"""
🤖 Информация о модели:

Название: {model_info['name']}
Размер: {model_info['size']}
Изменена: {model_info['modified']}

Максимум истории: {llm.max_history} сообщений
    """
    await update.message.reply_text(info_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик всех текстовых сообщений"""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    
    # Показываем, что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        if USE_LLM:
            # Используем LLM для умных ответов
            response = await llm.get_response(user_message, user_id, user_name)
        else:
            # Используем шаблонные ответы
            response = character.get_response(user_message, user_name)
        
        # Логируем диалог
        logger.info(f"Пользователь {user_name} ({user_id}): {user_message}")
        logger.info(f"Бот ответил ({'LLM' if USE_LLM else 'Template'}): {response}")
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        error_response = "Упс! 🙈 Что-то пошло не так. Попробуй еще раз!"
        await update.message.reply_text(error_response)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Универсальный обработчик для медиа-контента"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Определяем тип медиа
    if update.message.sticker:
        media_type = "стикер"
        user_message = "Пользователь прислал стикер"
    elif update.message.photo:
        media_type = "фото"
        user_message = "Пользователь прислал фото"
    elif update.message.voice:
        media_type = "голосовое сообщение"
        user_message = "Пользователь прислал голосовое сообщение"
    elif update.message.video:
        media_type = "видео"
        user_message = "Пользователь прислал видео"
    elif update.message.document:
        media_type = "документ"
        user_message = "Пользователь прислал документ"
    else:
        media_type = "медиа-файл"
        user_message = "Пользователь прислал медиа-файл"
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        if USE_LLM:
            # LLM может дать более креативный ответ на медиа
            response = await llm.get_response(user_message, user_id, user_name)
        else:
            # Шаблонные ответы для медиа
            if "стикер" in media_type:
                responses = ["Ой, классный стикер! 😄", "Люблю стикеры! 🤩", "Хаха, забавно! 😊"]
            elif "фото" in media_type:
                responses = ["Ого, классное фото! 📸✨", "Вау, красиво! 🤩", "Интересная картинка! 😊"]
            elif "голосовое" in media_type:
                responses = ["Получила твое голосовое! 🎤 Но я пока не умею их распознавать 😅"]
            else:
                responses = ["Интересно! 😊", "Получила! 👍", "Классно! ✨"]
            
            import random
            response = random.choice(responses)
        
        logger.info(f"Пользователь {user_name} отправил {media_type}")
        logger.info(f"Бот ответил: {response}")
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке медиа: {e}")
        await update.message.reply_text("Получила! 😊")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Произошла ошибка:", exc_info=context.error)
    
    if update and update.message:
        await update.message.reply_text("Упс! 🙈 Что-то пошло не так. Попробуй еще раз!")

def main() -> None:
    """Основная функция для запуска бота"""
    # Создаем приложение с токеном
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("question", question_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("model", model_command))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем универсальный обработчик медиа
    application.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_media))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    print(f"🤖 Бот {character.name} запущен с LLM поддержкой!")
    print(f"📋 Модель: {llm.model_name}")
    print(f"🎯 Режим: {'LLM' if USE_LLM else 'Шаблоны'}")
    print("Нажми Ctrl+C для остановки")
    
    application.run_polling()

if __name__ == '__main__':
    main()