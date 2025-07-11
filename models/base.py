"""Базовые модели данных."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum

class MessageType(Enum):
    """Типы сообщений."""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    STICKER = "sticker"
    COMMAND = "command"

class MessageRole(Enum):
    """Роли в диалоге."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class BaseMessage:
    """Базовое сообщение."""
    id: str
    content: str
    role: MessageRole
    message_type: MessageType
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class User:
    """Пользователь."""
    id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: Optional[str]
    created_at: datetime
    last_seen: datetime
    is_premium: bool = False
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        parts = [self.first_name]
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts)

@dataclass
class Conversation:
    """Диалог."""
    id: str
    user_id: int
    messages: List[BaseMessage]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    def add_message(self, message: BaseMessage) -> None:
        """Добавляет сообщение в диалог."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, limit: int = 10) -> List[BaseMessage]:
        """Получает последние сообщения."""
        return self.messages[-limit:] if limit > 0 else self.messages