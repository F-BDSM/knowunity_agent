import requests
import urllib.parse
from pydantic import BaseModel
from typing import Optional,List

from fbdsm.config import settings
from fbdsm.api import get_students_topics,start_conversation,interact
from fbdsm.models import InteractionResult,Topic
 

class Student:

    def __init__(self,student_id:str,topic_id:str, grade_level:int, name:str):
        self.student_id:str = student_id
        self.topic_id:str = topic_id
        self.grade_level:int = grade_level
        self.name:str = name

        self._topics: Optional[List[Topic]] = None
        self._current_topic: Optional[Topic] = None

        self._conversation_id: Optional[str] = None
        self.conversations_remaining: Optional[int] = None


    def _set_topics(self,):
        # load all available topics for the student
        self._topics = get_students_topics(self.student_id)

    def _get_topic(self,topic_id:str)->Topic:
        # set the current topic for the student
        if self._topics is None:
            self._set_topics()
        topic = None
        for topic in self._topics:
            if topic.id == topic_id:
                topic = topic
                break
        if topic is None:
            raise ValueError(f"Topic {topic_id} not found for student {self.id}")
        return topic    
    
    def _start_session(self,):

        result = start_conversation(student_id=self.student_id,topic_id=self.topic_id)
        self._conversation_id = result.conversation_id
        self.conversations_remaining = result.conversations_remaining

    def answer_tutor(self,tutor_message:str)->InteractionResult:

        # start a session if there is no conversation id
        if self._conversation_id is None:
            self._start_session()
        return interact(self._conversation_id,tutor_message)

    @property
    def topics(self,):
        return self._topics
    
    @property
    def current_topic(self,):
        if self._current_topic is None:
            self._current_topic = self._get_topic(self.topic_id)
        return self._current_topic
    

    