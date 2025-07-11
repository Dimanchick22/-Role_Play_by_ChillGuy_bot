"""Хранилище в памяти."""

from typing import Dict, Optional
from datetime import datetime
import uuid

from models.base import Conversation, User

class MemoryStorage:
    """Хранилище диалогов в памяти."""
    
    def __init__(self, max_conversations: int = 1000):
        self.conversations: Dict[int, Conversation] = {}
        self.max_conversations = max_conversations
    
    def get_conversation(self, user_id: int) -> Conversation:
        """Получает диалог пользователя."""
        if user_id not in self.conversations:
            self.conversations[user_id] = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                messages=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={}
            )
        
        return self.conversations[user_id]
    
    def save_conversation(self, conversation: Conversation) -> None:
        """Сохраняет диалог."""
        self.conversations[conversation.user_id] = conversation
        
        # Ограничиваем количество диалогов
        if len(self.conversations) > self.max_conversations:
            self._cleanup_old_conversations()
    
    def clear_conversation(self, user_id: int) -> None:
        """Очищает диалог пользователя."""
        if user_id in self.conversations:
            conversation = self.conversations[user_id]
            conversation.messages.clear()
            conversation.updated_at = datetime.now()
    
    def delete_conversation(self, user_id: int) -> None:
        """Удаляет диалог пользователя."""
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def get_stats(self) -> Dict:
        """Возвращает статистику."""
        total_messages = sum(
            len(conv.messages) 
            for conv in self.conversations.values()
        )
        
        return {
            "total_conversations": len(self.conversations),
            "total_messages": total_messages,
            "max_conversations": self.max_conversations
        }
    
    def _cleanup_old_conversations(self) -> None:
        """Удаляет старые диалоги."""
        # Сортируем по дате последнего обновления
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].updated_at
        )
        
        # Удаляем самые старые
        to_remove = len(sorted_conversations) - self.max_conversations + 100
        for user_id, _ in sorted_conversations[:to_remove]:
            del self.conversations[user_id]