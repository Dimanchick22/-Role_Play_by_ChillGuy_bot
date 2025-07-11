"""Хранилище в памяти - улучшенная версия."""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
import threading

from models.base import Conversation, User

logger = logging.getLogger(__name__)

class MemoryStorage:
    """Хранилище диалогов в памяти с thread-safe операциями."""
    
    def __init__(self, max_conversations: int = 1000):
        self.conversations: Dict[int, Conversation] = {}
        self.max_conversations = max_conversations
        self._lock = threading.RLock()  # Реентрантная блокировка для thread-safety
        
        logger.info(f"💾 MemoryStorage инициализирован (макс. диалогов: {max_conversations})")
    
    def get_conversation(self, user_id: int) -> Conversation:
        """Получает диалог пользователя."""
        with self._lock:
            if user_id not in self.conversations:
                self.conversations[user_id] = Conversation(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    messages=[],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    metadata={}
                )
                logger.debug(f"📝 Создан новый диалог для пользователя {user_id}")
            
            return self.conversations[user_id]
    
    def save_conversation(self, conversation: Conversation) -> None:
        """Сохраняет диалог."""
        with self._lock:
            conversation.updated_at = datetime.now()
            self.conversations[conversation.user_id] = conversation
            
            # Ограничиваем количество диалогов
            if len(self.conversations) > self.max_conversations:
                self._cleanup_old_conversations()
            
            logger.debug(f"💾 Диалог пользователя {conversation.user_id} сохранен")
    
    def clear_conversation(self, user_id: int) -> None:
        """Очищает диалог пользователя."""
        with self._lock:
            if user_id in self.conversations:
                conversation = self.conversations[user_id]
                conversation.messages.clear()
                conversation.updated_at = datetime.now()
                logger.info(f"🧹 Очищен диалог пользователя {user_id}")
    
    def delete_conversation(self, user_id: int) -> None:
        """Удаляет диалог пользователя."""
        with self._lock:
            if user_id in self.conversations:
                del self.conversations[user_id]
                logger.info(f"🗑️ Удален диалог пользователя {user_id}")
    
    def get_stats(self) -> Dict:
        """Возвращает статистику."""
        with self._lock:
            total_messages = sum(
                len(conv.messages) 
                for conv in self.conversations.values()
            )
            
            # Статистика по времени
            now = datetime.now()
            active_today = sum(
                1 for conv in self.conversations.values()
                if (now - conv.updated_at).days < 1
            )
            
            return {
                "total_conversations": len(self.conversations),
                "total_messages": total_messages,
                "active_today": active_today,
                "max_conversations": self.max_conversations,
                "memory_usage_mb": self._estimate_memory_usage()
            }
    
    def cleanup_old_conversations(self, days_old: int = 7) -> int:
        """Удаляет диалоги старше указанного количества дней."""
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            to_remove = []
            
            for user_id, conv in self.conversations.items():
                if conv.updated_at < cutoff_date:
                    to_remove.append(user_id)
            
            for user_id in to_remove:
                del self.conversations[user_id]
            
            if to_remove:
                logger.info(f"🧹 Удалено {len(to_remove)} старых диалогов (старше {days_old} дней)")
            
            return len(to_remove)
    
    def _cleanup_old_conversations(self) -> None:
        """Удаляет старые диалоги когда превышен лимит."""
        # Сортируем по дате последнего обновления
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].updated_at
        )
        
        # Удаляем самые старые (оставляем место для новых)
        to_remove = len(sorted_conversations) - self.max_conversations + 100
        
        if to_remove > 0:
            for user_id, _ in sorted_conversations[:to_remove]:
                del self.conversations[user_id]
            
            logger.info(f"🧹 Автоочистка: удалено {to_remove} старых диалогов")
    
    def _estimate_memory_usage(self) -> float:
        """Оценивает использование памяти в MB."""
        try:
            import sys
            
            # Проверяем, не завершается ли Python
            if sys.meta_path is None:
                return 0.0  # Python завершается, не считаем память
            
            total_size = 0
            
            # Размер самого словаря
            total_size += sys.getsizeof(self.conversations)
            
            # Размер всех диалогов
            for conv in self.conversations.values():
                total_size += sys.getsizeof(conv)
                total_size += sum(sys.getsizeof(msg) for msg in conv.messages)
                total_size += sum(
                    sys.getsizeof(msg.content) + sys.getsizeof(msg.metadata)
                    for msg in conv.messages
                )
            
            return total_size / (1024 * 1024)  # Конвертируем в MB
            
        except Exception:
            # Просто возвращаем 0 если что-то пошло не так
            return 0.0
    
    def backup_to_dict(self) -> Dict:
        """Создает резервную копию в виде словаря."""
        with self._lock:
            backup = {
                "conversations": {},
                "created_at": datetime.now().isoformat(),
                "stats": self.get_stats()
            }
            
            for user_id, conv in self.conversations.items():
                backup["conversations"][str(user_id)] = {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "messages": [
                        {
                            "id": msg.id,
                            "content": msg.content,
                            "role": msg.role.value,
                            "message_type": msg.message_type.value,
                            "timestamp": msg.timestamp.isoformat(),
                            "metadata": msg.metadata
                        }
                        for msg in conv.messages
                    ],
                    "metadata": conv.metadata
                }
            
            logger.info(f"💾 Создана резервная копия ({len(self.conversations)} диалогов)")
            return backup
    
    def cleanup(self):
        """Очистка ресурсов при завершении работы."""
        with self._lock:
            stats = self.get_stats()
            logger.info(f"🧹 Финальная статистика: {stats}")
            self.conversations.clear()
            logger.info("💾 MemoryStorage очищен")