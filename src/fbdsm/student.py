import requests
import urllib.parse
from pydantic import BaseModel
from typing import Optional,List

from fbdsm.config import settings

class Topic(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    grade_level: int

class InteractionStart(BaseModel):

    conversation_id: str
    student_id: str
    topic_id: str
    max_turns: int
    conversations_remaining: int

class InteractionResult(BaseModel):
    tutor_message: str
    conversation_id: str
    interaction_id: str
    student_response:str
    turn_number: int
    is_complete: bool
    
    


class Student:

    def __init__(self,id:str,topic_id:str):
        self.id:str = id
        self.topic_id:str = topic_id

        self._topics: List[Topic] = self._set_topics()
        self._current_topic: Topic = self.get_topic(topic_id)

        self._conversation_id: Optional[str] = None
        self.conversations_remaining: Optional[int] = None


    def _set_topics(self,):
        # load all available topics for the student
        payload = {
            "student_id": self.id
        }
        url = urllib.parse.urljoin(settings.KNOWUNITY_API_URL, f"/students/{self.id}/topics")
        headers = {
            "Authorization": "x-api-key " + settings.KNOWUNITY_API_KEY
        }
        response = requests.get(url, json=payload).json().get("topics",None)

        if response is None:
            raise ValueError(f"No topics found for student {self.id}")

        return [Topic(**topic) for topic in response]

    def get_topic(self,topic_id:str)->Topic:
        # set the current topic for the student
        current_topic = None
        for topic in self._topics:
            if topic.id == topic_id:
                current_topic = topic
                break
        if current_topic is None:
            raise ValueError(f"Topic {topic_id} not found for student {self.id}")
        return current_topic    
    
    def _start_session(self,):
        # calls endpoint to start a session
        payload = {
            "student_id": self.id,
            "topic_id": self._current_topic.id
        }
        url = urllib.parse.urljoin(settings.KNOWUNITY_API_URL, "/interact/start")
        headers = {
            "Authorization": "x-api-key " + settings.KNOWUNITY_API_KEY
        }
        response = requests.post(url, json=payload).json()
        interaction_start = InteractionStart(**response)

        self._conversation_id = interaction_start.conversation_id
        self.conversations_remaining = interaction_start.conversations_remaining

    def answer_tutor(self,tutor_message:str)->InteractionResult:

        # start a session if there is no conversation id
        if self._conversation_id is None:
            self._start_session()

        # calls endpoint to answer the tutor_message
        payload = {
            "conversation_id": self._conversation_id,
            "tutor_message": tutor_message
        }
        url = urllib.parse.urljoin(settings.KNOWUNITY_API_URL, "/interact")
        headers = {
            "Authorization": "x-api-key " + settings.KNOWUNITY_API_KEY
        }
        response = requests.post(url, json=payload).json()
        interaction_result = InteractionResult(tutor_message=tutor_message,**response)
        return interaction_result

    @property
    def topics(self,):
        return self._topics
    
    @property
    def current_topic(self,):
        return self._current_topic
    

    