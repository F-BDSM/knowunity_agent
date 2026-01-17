from pydantic import BaseModel, Field
from typing import Optional, List, Any


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
    conversations_remaining: Optional[int] = None


class InteractionResult(BaseModel):
    tutor_message: str
    conversation_id: str
    interaction_id: str
    student_response: str
    turn_number: int
    is_complete: bool


class Topic(BaseModel):
    id: str
    subject_id: str
    subject_name: str
    name: str
    grade_level: int

class TutorAgentInput(BaseModel):
    """Enhanced input for the adaptive tutor agent."""
    subject_name: str = Field(..., description="The subject name")
    topic_name: str = Field(..., description="The topic name")
    grade_level: int = Field(..., description="The grade level")
    current_turn: int = Field(default=1, ge=1, description="Current turn number (1-indexed)")
    max_turns: int = Field(default=10, ge=1, description="Maximum number of turns available")
    current_level_estimate: int = Field(
        default=3,
        ge=1, le=5,
        description="Current estimated skill level of the student (1-5)"
    )
    level_confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in the current level estimate (0.0 to 1.0)"
    )
    previous_student_response: Optional[str] = Field(None, description="The previous student response")
    previous_question_difficulty: Optional[str] = Field(None, description="The previous question difficulty")
    previous_response_analysis: Optional[Any] = Field(
        None,
        description="Analysis of the previous student response (ResponseAnalysis object)"
    )


class ConversationTurn(BaseModel):
    """A single turn in the tutoring conversation."""
    question: str
    student_response: str
    question_difficulty: Optional[str] = None
    response_analysis: Optional[dict] = None