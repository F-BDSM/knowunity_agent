from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from enum import StrEnum
from langchain_core.messages import HumanMessage, SystemMessage

from ..models import QuestionAgentInput
from ..config import llm


class QuestionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionOutput(BaseModel):
    """Output schema for the question generator."""
    question: str = Field(description="The generated educational question that would be appropriate to evaluate the skill of the student.")
    estimated_difficulty: QuestionDifficulty = Field(description="The estimated difficulty of the question.")
    reasoning: str = Field(description="Brief reasoning for why this question is appropriate.")


SYSTEM_PROMPT = """You are an expert educational question generator. Your task is to generate appropriate questions to assess a student's knowledge level.

Guidelines:
- Generate questions appropriate for the given grade level and topic
- If a previous student response is provided, use it to calibrate difficulty
- If the previous response was correct/good, make the next question slightly harder
- If the previous response was incorrect/poor, make the next question slightly easier
- Questions should be clear, educational, and help assess true understanding
- Vary question types (conceptual, application, analysis) based on difficulty"""


class QuestionAgent:
    def __init__(self):
        self.llm = llm.with_structured_output(QuestionOutput)

    def _build_prompt(self, request: QuestionAgentInput, history: Optional[List[dict]] = None) -> str:
        prompt_parts = [
            f"Subject: {request.subject_name}",
            f"Topic: {request.topic_name}",
            f"Grade Level: {request.grade_level}",
        ]

        if request.previous_student_response:
            prompt_parts.append(f"\nPrevious student response: {request.previous_student_response}")

        if request.previous_question_difficulty:
            prompt_parts.append(f"Previous question difficulty: {request.previous_question_difficulty}")

        if history:
            prompt_parts.append("\nConversation history:")
            for i, turn in enumerate(history, 1):
                prompt_parts.append(f"  Turn {i}: Q: {turn.get('question', 'N/A')}")

        prompt_parts.append("\nGenerate an appropriate educational question to assess the student's understanding.")

        return "\n".join(prompt_parts)

    def forward(self, request: QuestionAgentInput, history: Optional[List[dict]] = None) -> Tuple[str, QuestionDifficulty]:
        prompt = self._build_prompt(request, history)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        result: QuestionOutput = self.llm.invoke(messages)
        return result.question, result.estimated_difficulty

    def generate(self, request: QuestionAgentInput, history: Optional[List[dict]] = None) -> Tuple[str, QuestionDifficulty]:
        return self.forward(request, history=history)
