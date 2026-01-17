import aiohttp
from typing import Optional, List

from fbdsm.config import settings
from fbdsm.api import get_students_topics, start_conversation, interact
from fbdsm.models import InteractionResult, Topic, TopicInfo


class Student:
    """Represents a student in the tutoring system."""

    def __init__(self, student_id: str, topic_id: Optional[str] = None):
        self.student_id: str = student_id
        self.topic_id: Optional[str] = topic_id

        self._topics: Optional[List[TopicInfo]] = None
        self._current_topic: Optional[TopicInfo] = None

        self._conversation_id: Optional[str] = None
        self.conversations_remaining: Optional[int] = None

    async def _set_topics(self, session: aiohttp.ClientSession):
        """Load all available topics for the student."""
        self._topics = await get_students_topics(session, self.student_id)
    
    def set_topic(self, topic_id: str):
        """Set the current topic ID."""
        self.topic_id = topic_id
        if self._topics:
            self._current_topic = self._get_topic_from_cache(topic_id)

    def _get_topic_from_cache(self, topic_id: str) -> TopicInfo:
        """Get a specific topic by ID from the cached topics."""
        for t in self._topics:
            if t.id == topic_id:
                return t
        raise ValueError(f"Topic {topic_id} not found for student {self.student_id}")

    async def _get_topic(self, session: aiohttp.ClientSession, topic_id: str) -> TopicInfo:
        """Get a specific topic by ID for the student."""
        if self._topics is None:
            await self._set_topics(session)
        return self._get_topic_from_cache(topic_id)
    
    async def _start_session(self, session: aiohttp.ClientSession):
        """Start a new tutoring session."""
        assert self.topic_id is not None, "Topic ID is not set"
        print(f"Starting session for student {self.student_id} and topic {self.topic_id}")
        result = await start_conversation(session, student_id=self.student_id, topic_id=self.topic_id)
        self._conversation_id = result.conversation_id
        self.conversations_remaining = result.conversations_remaining

    async def get_response(self, session: aiohttp.ClientSession, question: str) -> InteractionResult:
        """Get the student's response to a question."""
        if self._conversation_id is None:
            await self._start_session(session)
        return await interact(session, self._conversation_id, question)

    async def get_topics(self, session: aiohttp.ClientSession) -> List[TopicInfo]:
        """Get all topics for the student."""
        if self._topics is None:
            await self._set_topics(session)
        return self._topics
    
    @property
    def topic(self) -> Optional[TopicInfo]:
        """Get the current topic."""
        return self._current_topic

    def reset_session(self):
        """Reset the conversation session."""
        self._conversation_id = None