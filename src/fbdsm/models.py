from pydantic import BaseModel, Field
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

class QuestionAgentInput(BaseModel):

    subject_name: str = Field(..., description="The subject name for the question")
    topic_name: str = Field(..., description="The topic name for the question")
    grade_level: int = Field(..., description="The grade level for the question")
    previous_student_response: Optional[str] = Field(None, description="The previous student response for the question")
    previous_question_difficulty: Optional[str] = Field(None, description="The previous question difficulty for the question")

class ConversationTurn(BaseModel):

    question: str
    student_response:str
    request:QuestionAgentInput