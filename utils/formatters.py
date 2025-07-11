"""Форматирование сообщений."""

from typing import Dict, Any

def format_help_message(has_llm: bool = False, has_image: bool = False) -> str:
    """Форматирует справочное сообщение."""
    commands = [
        "/start - Знакомство со мной",
        "/help - Эта справка",
        "/info - Информация обо мне"
    ]
    
    if has_llm:
        commands.extend([
            "/clear - Очистить историю диалога",
            "/stats - Статистика работы"
        ])
    
    if has_image:
        commands.extend([
            "/image <описание> - Генерация изображения",
            "/style - Доступные стили изображений"
        ])
    
    help_text = f"""🤖 Справка по боту

Привет! Я Алиса, твой виртуальный помощник!

📋 Доступные команды:
{chr(10).join(commands)}

💬 Просто пиши мне сообщения, и я отвечу!

{'🧠 Умные ответы через LLM активны' if has_llm else '📝 Работаю в режиме шаблонов'}
{'🎨 Генерация изображений доступна' if has_image else ''}"""
    
    return help_text

def format_stats(services_stats: Dict[str, Any]) -> str:
    """Форматирует статистику сервисов."""
    lines = ["📊 Статистика сервисов:\n"]
    
    # LLM статистика
    llm_stats = services_stats.get('llm', {})
    if llm_stats.get('available'):
        lines.append(f"🧠 LLM: ✅ {llm_stats.get('model', 'Неизвестно')}")
    else:
        lines.append("🧠 LLM: ❌ Недоступно")
    
    # Изображения статистика  
    image_stats = services_stats.get('image', {})
    if image_stats.get('initialized'):
        lines.append(f"🎨 Изображения: ✅ {image_stats.get('model', 'Неизвестно')}")
    else:
        lines.append("🎨 Изображения: ❌ Недоступно")
    
    return "\n".join(lines)