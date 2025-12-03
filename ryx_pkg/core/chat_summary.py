# -*- coding: utf-8 -*-
"""
Chat Summary - Kontext-Zusammenfassung für lange Konversationen
Inspiriert von Aider's history.py
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """Konfiguration für Chat Summary"""
    max_tokens: int = 8000  # Max Tokens für Kontext
    summary_threshold: float = 0.75  # Bei 75% Auslastung zusammenfassen
    keep_recent_turns: int = 3  # Immer die letzten N Turns behalten
    summary_model: Optional[str] = None  # Falls unterschiedliches Modell für Summary


@dataclass
class Message:
    """Eine Chat-Nachricht"""
    role: str  # "user", "assistant", "system"
    content: str
    tokens: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChatSummary:
    """
    Kontext-Manager für lange Konversationen
    
    Komprimiert ältere Nachrichten zu Zusammenfassungen,
    um Token-Limits einzuhalten.
    
    Usage:
        summary = ChatSummary(token_counter=count_tokens)
        
        # Füge Nachrichten hinzu
        summary.add_message(Message(role="user", content="Hello"))
        summary.add_message(Message(role="assistant", content="Hi!"))
        
        # Hole Kontext für LLM
        messages = summary.get_messages()
        
        # Automatische Komprimierung wenn nötig
        if summary.needs_compression():
            await summary.compress(llm_client)
    """
    
    def __init__(
        self,
        config: Optional[SummaryConfig] = None,
        token_counter: Optional[callable] = None
    ):
        self.config = config or SummaryConfig()
        self._token_counter = token_counter or self._default_token_count
        
        self._messages: List[Message] = []
        self._summaries: List[str] = []  # Vergangene Zusammenfassungen
        self._total_tokens: int = 0
        
    def _default_token_count(self, text: str) -> int:
        """Einfache Token-Schätzung (4 chars ≈ 1 token)"""
        return len(text) // 4
        
    def add_message(self, message: Message):
        """Füge Nachricht hinzu"""
        if message.tokens == 0:
            message.tokens = self._token_counter(message.content)
            
        self._messages.append(message)
        self._total_tokens += message.tokens
        
    def get_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Hole Nachrichten für LLM-Kontext
        
        Returns:
            Liste von Nachrichten im OpenAI-Format
        """
        result = []
        
        # Füge Zusammenfassung hinzu falls vorhanden
        if self._summaries:
            summary_text = "\n\n".join(self._summaries)
            result.append({
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary_text}"
            })
            
        # Füge aktuelle Nachrichten hinzu
        for msg in self._messages:
            if msg.role == "system" and not include_system:
                continue
            result.append({
                "role": msg.role,
                "content": msg.content
            })
            
        return result
        
    def needs_compression(self) -> bool:
        """Prüfe ob Komprimierung nötig ist"""
        threshold = int(self.config.max_tokens * self.config.summary_threshold)
        return self._total_tokens > threshold
        
    async def compress(self, llm_client) -> bool:
        """
        Komprimiere ältere Nachrichten
        
        Args:
            llm_client: LLM-Client mit generate() Methode
            
        Returns:
            True wenn erfolgreich
        """
        if not self.needs_compression():
            return True
            
        # Behalte die letzten N Turns
        keep_count = self.config.keep_recent_turns * 2  # User + Assistant
        
        if len(self._messages) <= keep_count:
            logger.warning("Not enough messages to compress")
            return False
            
        # Teile in zu komprimierende und zu behaltende Nachrichten
        to_compress = self._messages[:-keep_count]
        to_keep = self._messages[-keep_count:]
        
        # Erstelle Zusammenfassung
        summary = await self._create_summary(to_compress, llm_client)
        
        if summary:
            self._summaries.append(summary)
            self._messages = to_keep
            self._total_tokens = sum(m.tokens for m in to_keep)
            self._total_tokens += self._token_counter(summary)
            
            logger.info(f"Compressed {len(to_compress)} messages into summary")
            return True
            
        return False
        
    async def _create_summary(
        self,
        messages: List[Message],
        llm_client
    ) -> Optional[str]:
        """Erstelle Zusammenfassung der Nachrichten"""
        # Formatiere Nachrichten
        formatted = []
        for msg in messages:
            formatted.append(f"{msg.role.upper()}: {msg.content}")
            
        conversation = "\n\n".join(formatted)
        
        prompt = f"""Summarize the following conversation concisely.
Focus on:
- Key decisions made
- Important information shared
- Tasks completed or in progress
- Any code changes discussed

Keep the summary under 500 words.

CONVERSATION:
{conversation}

SUMMARY:"""

        try:
            # Generiere Zusammenfassung
            if hasattr(llm_client, 'generate'):
                response = await llm_client.generate(prompt)
            elif hasattr(llm_client, 'chat'):
                response = await llm_client.chat([
                    {"role": "user", "content": prompt}
                ])
            else:
                logger.error("LLM client has no generate or chat method")
                return None
                
            # Extrahiere Text
            if isinstance(response, dict):
                return response.get('content', response.get('text', ''))
            return str(response)
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None
            
    def get_token_count(self) -> int:
        """Aktuelle Token-Anzahl"""
        return self._total_tokens
        
    def get_message_count(self) -> int:
        """Anzahl Nachrichten"""
        return len(self._messages)
        
    def clear(self):
        """Lösche alle Nachrichten und Zusammenfassungen"""
        self._messages = []
        self._summaries = []
        self._total_tokens = 0
        
    def get_last_messages(self, count: int = 5) -> List[Message]:
        """Hole die letzten N Nachrichten"""
        return self._messages[-count:]
        
    def remove_last_message(self) -> Optional[Message]:
        """Entferne letzte Nachricht"""
        if self._messages:
            msg = self._messages.pop()
            self._total_tokens -= msg.tokens
            return msg
        return None
        
    def to_dict(self) -> dict:
        """Exportiere als Dict"""
        return {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in self._messages
            ],
            "summaries": self._summaries,
            "total_tokens": self._total_tokens
        }
        
    @classmethod
    def from_dict(cls, data: dict, token_counter=None) -> 'ChatSummary':
        """Importiere aus Dict"""
        instance = cls(token_counter=token_counter)
        
        for msg_data in data.get("messages", []):
            instance.add_message(Message(
                role=msg_data["role"],
                content=msg_data["content"]
            ))
            
        instance._summaries = data.get("summaries", [])
        
        return instance
