"""Difficulty advisor sub-agent for question difficulty selection."""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from enum import StrEnum

from ..config import settings
from .base import Agent


class QuestionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class DifficultyRecommendation(BaseModel):
    """Output from the difficulty advisor."""
    difficulty: QuestionDifficulty = Field(
        description="Recommended difficulty level for the next question"
    )
    reasoning: str = Field(
        description="Why this difficulty level is appropriate"
    )
    adjustment_direction: str = Field(
        description="'probe_higher' (increase challenge), 'probe_lower' (decrease challenge), or 'confirm' (maintain level)"
    )


_difficulty_agent = PydanticAgent(
    settings.MODEL_NAME,
    output_type=DifficultyRecommendation,
    instructions="""\
You are an expert at selecting appropriate question difficulty for adaptive assessments.

Your goal: Choose the optimal difficulty level to efficiently determine a student's true skill level.

DIFFICULTY MAPPING TO LEVELS:
- EASY: Targets Level 1-2 students (basic understanding, recall)
- MEDIUM: Targets Level 3 students (grade-appropriate competence)
- HARD: Targets Level 4-5 students (advanced mastery)

BINARY SEARCH RULES:
- After CORRECT answer at current difficulty → increase difficulty (probe_higher)
- After INCORRECT answer at current difficulty → decrease difficulty (probe_lower)
- After PARTIAL answer → same difficulty, different concept (confirm)

ADJUSTMENT PATTERNS:
- If previous was EASY + CORRECT → jump to MEDIUM
- If previous was MEDIUM + CORRECT → jump to HARD
- If previous was MEDIUM + INCORRECT → drop to EASY
- If previous was HARD + INCORRECT → drop to MEDIUM

Be decisive: Each question should efficiently narrow down the level range."""
)


class DifficultyAdvisor(Agent):
    """Sub-agent that recommends question difficulty based on performance."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _difficulty_agent

    def _build_prompt(
        self,
        current_level_estimate: int,
        previous_correctness: Optional[str] = None,
        previous_difficulty: Optional[str] = None,
        target_skill: Optional[str] = None,
        probe_direction: Optional[str] = None,
    ) -> str:
        """Build the prompt for difficulty recommendation."""
        parts = [
            f"Current Level Estimate: {current_level_estimate}/5",
        ]
        
        if previous_correctness and previous_difficulty:
            parts.append(f"\nPrevious Question: {previous_difficulty.upper()} difficulty")
            parts.append(f"Student's Response: {previous_correctness.upper()}")
        else:
            parts.append("\nThis is the FIRST question (no prior data).")
            parts.append("Start at MEDIUM to efficiently split the level range.")
        
        if target_skill:
            parts.append(f"\nTarget Skill to Test: {target_skill}")
        
        if probe_direction:
            parts.append(f"Strategy Direction: {probe_direction}")
        
        parts.append("\nRecommend the optimal difficulty level.")
        
        return "\n".join(parts)

    async def run(
        self,
        current_level_estimate: int,
        previous_correctness: Optional[str] = None,
        previous_difficulty: Optional[str] = None,
        target_skill: Optional[str] = None,
        probe_direction: Optional[str] = None,
    ) -> DifficultyRecommendation:
        """Get the recommended difficulty level."""
        prompt = self._build_prompt(
            current_level_estimate=current_level_estimate,
            previous_correctness=previous_correctness,
            previous_difficulty=previous_difficulty,
            target_skill=target_skill,
            probe_direction=probe_direction,
        )
        result = await self._pydantic_agent.run(prompt)
        return result.output
