from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from enum import StrEnum

from ..config import settings


class Correctness(StrEnum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class ResponseAnalysis(BaseModel):
    """Structured output for response analysis."""
    correctness: Correctness = Field(
        description="Whether the student's answer was correct, partially correct, or incorrect"
    )
    confidence_level: int = Field(
        ge=1, le=5,
        description="How confident the student seemed in their response (1=very uncertain, 5=very confident)"
    )
    knowledge_gaps: List[str] = Field(
        default_factory=list,
        description="Specific concepts or areas where the student showed misunderstanding"
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Concepts the student demonstrated good understanding of"
    )
    reasoning: str = Field(
        description="Brief explanation of the analysis"
    )


# Create the pydantic-ai agent
_response_analyzer = Agent(
    settings.MODEL_NAME,
    output_type=ResponseAnalysis,
    instructions=(
        "You are an educational assessment expert analyzing student responses. "
        "Evaluate the student's answer for correctness, identifying what they understood well "
        "and where they have gaps in understanding. Consider the question difficulty and "
        "the student's apparent confidence level based on their response patterns."
    ),
)


class ResponseAnalyzer:
    """Agent that analyzes student responses to identify correctness and knowledge gaps."""

    def __init__(self):
        self.agent = _response_analyzer

    def _build_prompt(
        self,
        question: str,
        student_response: str,
        question_difficulty: str,
        topic_name: str,
        grade_level: int,
    ) -> str:
        """Build the prompt for response analysis."""
        return f"""Analyze this student's response:

Topic: {topic_name}
Grade Level: {grade_level}
Question Difficulty: {question_difficulty}

Question: {question}

Student's Response: {student_response}

Evaluate the correctness of the response and identify any knowledge gaps or strengths."""

    async def analyze(
        self,
        question: str,
        student_response: str,
        question_difficulty: str,
        topic_name: str,
        grade_level: int,
    ) -> ResponseAnalysis:
        """Analyze a student's response."""
        prompt = self._build_prompt(
            question=question,
            student_response=student_response,
            question_difficulty=question_difficulty,
            topic_name=topic_name,
            grade_level=grade_level,
        )
        result = await self.agent.run(prompt)
        return result.output
