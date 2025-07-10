import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from character import Character

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализируем персонажа
character = Character()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_name = update.effective_user.first_name
    welcome_message = f"Привет, {user_name}! 🌟\n\n{character.get_character_info()}"
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = f"""
🤖 Помощь по боту

Привет! Я {character.name}, твой виртуальный друг! 

Доступные команды:
/start - Познакомиться со мной
/help - Показать это сообщение
/info - Узнать больше обо мне
/question - Получить случайный вопрос для разговора

Просто пиши мне сообщения, и я отвечу! 💬
Я умею:
• Поддерживать беседу
• Отвечать на разные темы
• Поднимать настроение
• Быть хорошим собеседником

Давай общаться! 😊
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик всех текстовых сообщений"""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    # Получаем ответ от персонажа
    response = character.get_response(user_message, user_name)
    
    # Логируем диалог
    logger.info(f"Пользователь {user_name}: {user_message}")
    logger.info(f"Бот ответил: {response}")
    
    await update.message.reply_text(response)

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик стикеров"""
    responses = [
        "Ой, классный стикер! 😄",
        "Люблю стикеры! 🤩",
        "Хаха, забавно! 😊",
        "Стикер супер! ✨"
    ]
    import random
    response = random.choice(responses)
    await update.message.reply_text(response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фотографий"""
    responses = [
        "Ого, классное фото! 📸✨",
        "Вау, красиво! 🤩",
        "Интересная картинка! 😊",
        "Спасибо за фото! 🌟"
    ]
    import random
    response = random.choice(responses)
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик голосовых сообщений"""
    responses = [
        "Получила твое голосовое! 🎤 Но я пока не умею их распознавать 😅",
        "Слышу, слышу! 👂 Правда, не понимаю, что говоришь 😊",
        "Голосовое сообщение! 🎵 Жаль, что не могу ответить голосом 😄"
    ]
    import random
    response = random.choice(responses)
    await update.message.reply_text(response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Произошла ошибка:", exc_info=context.error)
    
    # Отправляем дружелюбное сообщение об ошибке
    if update and update.message:
        await update.message.reply_text(
            "Упс! 🙈 Что-то пошло не так. Попробуй еще раз!"
        )

def main() -> None:
    """Основная функция для запуска бота"""
    # Создаем приложение с токеном
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("question", question_command))
    
    # Добавляем обработчики разных типов сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    print(f"Бот {character.name} запущен! 🌟")
    print("Нажми Ctrl+C для остановки")
    application.run_polling()

if __name__ == '__main__':
    main()