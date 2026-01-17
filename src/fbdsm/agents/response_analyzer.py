from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from enum import StrEnum

from ..config import settings
from .base import Agent


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
_response_analyzer = PydanticAgent(
    settings.MODEL_NAME,
    output_type=ResponseAnalysis,
    instructions="""\
You are a decisive educational assessment expert specializing in analyzing student responses.

Your task is to evaluate a student's answer with precision and clarity.

CORRECTNESS CRITERIA (choose exactly ONE):
- **correct**: The answer is factually accurate and addresses the question's core requirements. Minor phrasing issues or tangential omissions do NOT make an answer partial.
- **partial**: The answer contains substantive correct elements BUT also has significant errors, missing key components, or demonstrates incomplete reasoning.
- **incorrect**: The answer is fundamentally wrong, shows major misconceptions, or fails to address the question.

CONFIDENCE LEVEL ASSESSMENT (1-5):
- 1: Very uncertain—hedging language, question marks, "I think maybe..."
- 2: Somewhat uncertain—tentative phrasing, lacks conviction
- 3: Neutral—straightforward answer without strong confidence indicators
- 4: Fairly confident—assertive language, clear explanations
- 5: Very confident—emphatic, detailed reasoning, no hesitation

ANALYSIS GUIDELINES:
1. Be decisive: a mostly-correct answer is "correct"—don't penalize minor imperfections.
2. Knowledge gaps should be SPECIFIC concepts, not vague observations (e.g., "confuses velocity with acceleration" not "doesn't understand physics").
3. Strengths should highlight concrete demonstrated understanding (e.g., "correctly applied the quadratic formula").
4. Consider grade level—judge against age-appropriate expectations.
5. Weigh question difficulty: errors on hard questions are less concerning than errors on easy ones.

Provide a concise, evidence-based reasoning that cites specific parts of the student's response.""",
)


class ResponseAnalyzer(Agent):
    """Agent that analyzes student responses to identify correctness and knowledge gaps."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _response_analyzer

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

    async def run(
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
        result = await self._pydantic_agent.run(prompt)
        return result.output
