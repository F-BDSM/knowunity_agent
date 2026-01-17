from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from enum import StrEnum

from ..config import settings
from .base import Agent


class Score(StrEnum):
    STRUGGLING = "Struggling"
    BELOW_GRADE = "Below-grade"
    AT_GRADE = "At-grade"
    ABOVE_GRADE = "Above-grade"
    ADVANCED = "Advanced"


MAPPING = {
    Score.STRUGGLING: 1,
    Score.BELOW_GRADE: 2,
    Score.AT_GRADE: 3,
    Score.ABOVE_GRADE: 4,
    Score.ADVANCED: 5
}


class ScoringOutput(BaseModel):
    """Structured output for scoring evaluation."""
    score: Score = Field(description="The level of the student's understanding of the topic.")
    rationale: str = Field(description="The rationale for the score.")


# Create the pydantic-ai agent
_scoring_agent = PydanticAgent(
    settings.MODEL_NAME,
    output_type=ScoringOutput,
    instructions=(
        "You are an educational assessment expert. "
        "Evaluate the student's understanding based on their responses to questions. "
        "Consider the difficulty of questions, accuracy of responses, and depth of understanding."
    ),
)


class ScoringAgent(Agent):
    """Agent for final scoring of student understanding."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _scoring_agent

    def _build_prompt(self, conversation: List[dict]) -> str:
        """Build the prompt from the conversation Q&A pairs."""
        prompt_parts = ["Evaluate the student's performance based on the following Q&A session:\n"]
        
        for i, qa in enumerate(conversation, 1):
            prompt_parts.append(f"Question {i}: {qa.get('question', '')}")
            prompt_parts.append(f"Difficulty: {qa.get('question_difficulty', 'unknown')}")
            prompt_parts.append(f"Student Response: {qa.get('student_response', '')}")
            prompt_parts.append("")
        
        prompt_parts.append("Based on these responses, evaluate the student's overall understanding.")
        
        return "\n".join(prompt_parts)

    async def run(self, conversation: List[dict]) -> int:
        """Generate a score for the conversation."""
        prompt = self._build_prompt(conversation)
        result = await self._pydantic_agent.run(prompt)
        return MAPPING[result.output.score]