import requests
import urllib.parse
from pydantic import BaseModel
from typing import Optional,List

from fbdsm.config import settings
from fbdsm.api import get_students_topics,start_conversation,interact
from fbdsm.models import InteractionResult,Topic
 

class Student:

    def __init__(self,student_id:str,topic_id:Optional[str]=None):
        self.student_id:str = student_id
        self.topic_id:Optional[str] = topic_id

        self._topics: Optional[List[Topic]] = None
        self._current_topic: Optional[Topic] = None

        self._conversation_id: Optional[str] = None
        self.conversations_remaining: Optional[int] = None


    def _set_topics(self,):
        # load all available topics for the student
        self._topics = get_students_topics(self.student_id)
    
    def set_topic(self,topic_id:str):
        self.topic_id = topic_id
        self._current_topic = self._get_topic(self.topic_id)

    def _get_topic(self, topic_id: str) -> Topic:
        """Get a specific topic by ID for the student."""
        if self._topics is None:
            self._set_topics()
        for t in self._topics:
            if t.id == topic_id:
                return t
        raise ValueError(f"Topic {topic_id} not found for student {self.student_id}")    
    
    def _start_session(self,):
        assert self.topic_id is not None,"Topic ID is not set"
        print(f"Starting session for student {self.student_id} and topic {self.topic_id}")
        result = start_conversation(student_id=self.student_id,topic_id=self.topic_id)
        self._conversation_id = result.conversation_id
        self.conversations_remaining = result.conversations_remaining

    def get_response(self,question:str)->InteractionResult:
        if self._conversation_id is None:
            self._start_session()
        return interact(self._conversation_id,question)

    @property
    def topics(self,):
        if self._topics is None:
            self._set_topics()
        return self._topics
    
    @property
    def topic(self,):
        if self._current_topic is None:
            assert self.topic_id is not None,"Topic ID is not set"
            self.set_topic(self.topic_id)
        return self._current_topic
    

    