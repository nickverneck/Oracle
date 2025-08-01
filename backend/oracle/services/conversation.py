"""Conversation context management service."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from ..models.chat import ConversationContext

logger = structlog.get_logger(__name__)


class ConversationManager:
    """Manages conversation contexts and history."""
    
    def __init__(self, max_history_length: int = 10):
        """Initialize conversation manager.
        
        Args:
            max_history_length: Maximum number of messages to keep in history
        """
        self.max_history_length = max_history_length
        self._conversations: Dict[str, ConversationContext] = {}
        
        logger.info("Initialized conversation manager", max_history=max_history_length)
    
    def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new conversation context.
        
        Args:
            conversation_id: Optional custom conversation ID
            user_preferences: Optional user preferences
            
        Returns:
            Conversation ID
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        context = ConversationContext(
            conversation_id=conversation_id,
            messages=[],
            user_preferences=user_preferences or {}
        )
        
        self._conversations[conversation_id] = context
        
        logger.info("Created new conversation", conversation_id=conversation_id)
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationContext if found, None otherwise
        """
        return self._conversations.get(conversation_id)
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a message to conversation history.
        
        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            True if message was added, False if conversation not found
        """
        context = self._conversations.get(conversation_id)
        if not context:
            logger.warning("Conversation not found", conversation_id=conversation_id)
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        context.messages.append(message)
        
        # Trim history if it exceeds max length
        if len(context.messages) > self.max_history_length:
            removed_count = len(context.messages) - self.max_history_length
            context.messages = context.messages[-self.max_history_length:]
            logger.debug(
                "Trimmed conversation history",
                conversation_id=conversation_id,
                removed_messages=removed_count
            )
        
        logger.debug(
            "Added message to conversation",
            conversation_id=conversation_id,
            role=role,
            message_count=len(context.messages)
        )
        
        return True
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation message history.
        
        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages in chronological order
        """
        context = self._conversations.get(conversation_id)
        if not context:
            return []
        
        messages = context.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def update_user_preferences(
        self,
        conversation_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences for a conversation.
        
        Args:
            conversation_id: Conversation ID
            preferences: User preferences to update
            
        Returns:
            True if updated, False if conversation not found
        """
        context = self._conversations.get(conversation_id)
        if not context:
            return False
        
        if context.user_preferences is None:
            context.user_preferences = {}
        
        context.user_preferences.update(preferences)
        
        logger.debug(
            "Updated user preferences",
            conversation_id=conversation_id,
            preferences=preferences
        )
        
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation context.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info("Deleted conversation", conversation_id=conversation_id)
            return True
        
        return False
    
    def get_active_conversations(self) -> List[str]:
        """Get list of active conversation IDs.
        
        Returns:
            List of conversation IDs
        """
        return list(self._conversations.keys())
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about active conversations.
        
        Returns:
            Dictionary with conversation statistics
        """
        total_conversations = len(self._conversations)
        total_messages = sum(
            len(context.messages) 
            for context in self._conversations.values()
        )
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "max_history_length": self.max_history_length
        }
    
    def build_context_prompt(
        self,
        conversation_id: str,
        current_message: str,
        include_history: bool = True,
        max_context_messages: int = 5
    ) -> str:
        """Build a context-aware prompt for the AI model.
        
        Args:
            conversation_id: Conversation ID
            current_message: Current user message
            include_history: Whether to include conversation history
            max_context_messages: Maximum number of previous messages to include
            
        Returns:
            Context-aware prompt string
        """
        if not include_history:
            return current_message
        
        context = self._conversations.get(conversation_id)
        if not context or not context.messages:
            return current_message
        
        # Get recent messages for context
        recent_messages = context.messages[-max_context_messages:]
        
        # Build context prompt
        context_parts = ["Previous conversation context:"]
        
        for msg in recent_messages:
            role = msg["role"].capitalize()
            content = msg["content"][:200]  # Limit content length
            context_parts.append(f"{role}: {content}")
        
        context_parts.append(f"\nCurrent message: {current_message}")
        
        return "\n".join(context_parts)