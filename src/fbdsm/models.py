from pydantic import BaseModel
from typing import Optional

class StudentInfo(BaseModel):
    id: str
    name: str
    grade_level: int

class TopicInfo(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    grade_level: int

class InteractionStartResult(BaseModel):

    conversation_id: str
    student_id: str
    topic_id: str
    max_turns: int
    conversations_remaining: Optional[int]=None

class InteractionResult(BaseModel):
    tutor_message: str
    conversation_id: str
    interaction_id: str
    student_response:str
    turn_number: int
    is_complete: bool

class Topic(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    grade_level: int