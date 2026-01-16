import requests
import urllib.parse
from pydantic import BaseModel

API_URL = "https://knowunity-agent-olympics-2026-api.vercel.app"

class Topic(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    grade_level: int


class Student:

    def __init__(self,id:str):
        self.id = id

        self._topics = self._set_topics()
        self._current_topic = None

    def _set_topics(self,):
        # load all available topics for the student
        payload = {
            "student_id": self.id
        }
        url = urllib.parse.urljoin(API_URL, f"/students/{self.id}/topics")
        response = requests.get(url, json=payload).json().get("topics",None)

        if response is None:
            raise ValueError(f"No topics found for student {self.id}")

        return [Topic(**topic) for topic in response]

    def set_current_topic(self,topic_id:str):
        # set the current topic for the student
        self._current_topic = topic_id
    
    def answer_question(self,question:str):
        # calls endpoint to answer the question
        pass

    @property
    def topics(self,):
        return self._topics
    
    @property
    def current_topic(self,):
        return self._current_topic
    

    