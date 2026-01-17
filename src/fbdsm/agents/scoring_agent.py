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
    instructions="""\
You are a decisive educational assessment expert specializing in evaluating student understanding.

Your task is to assign ONE definitive score based on the student's Q&A performance:

SCORING CRITERIA (choose the BEST match):
- **Struggling**: Student shows fundamental misconceptions, incorrect answers on basic questions, or inability to engage with core concepts.
- **Below-grade**: Student grasps some basics but makes significant errors, struggles with medium-difficulty questions, or shows shallow understanding.
- **At-grade**: Student demonstrates solid understanding of core concepts, answers most questions correctly, with minor gaps in reasoning.
- **Above-grade**: Student shows strong mastery, handles difficult questions well, and demonstrates connections between concepts.
- **Advanced**: Student exhibits exceptional understanding, provides insightful answers beyond expectations, and shows deep conceptual mastery.

EVALUATION GUIDELINES:
1. Weight answers by question difficulty—success on harder questions indicates stronger understanding.
2. Look for patterns: consistent correctness vs. isolated mistakes.
3. Assess depth of reasoning, not just correctness—superficial correct answers suggest lower levels.
4. Be decisive: do NOT average or hedge. Pick the single level that best represents overall performance.
5. When in doubt between two adjacent levels, consider the student's performance on the hardest questions attempted.

Provide a clear, specific rationale citing evidence from the student's responses.""",
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