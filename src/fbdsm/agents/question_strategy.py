"""Question strategy sub-agent for binary-search assessment."""
from typing import Tuple, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent

from ..config import settings
from .base import Agent


class QuestionStrategy(BaseModel):
    """Output from the question strategy advisor."""
    target_skill: str = Field(
        description="The specific skill or concept to test with the next question"
    )
    reasoning: str = Field(
        description="Why testing this skill helps narrow down the student's level"
    )
    level_range_low: int = Field(
        ge=1, le=5,
        description="Lower bound of the level range we're probing"
    )
    level_range_high: int = Field(
        ge=1, le=5,
        description="Upper bound of the level range we're probing"
    )
    probe_direction: str = Field(
        description="Direction of probing: 'higher' (student may be above estimate), 'lower' (student may be below), or 'confirm' (verifying current estimate)"
    )


_strategy_agent = PydanticAgent(
    settings.MODEL_NAME,
    output_type=QuestionStrategy,
    instructions="""\
You are an expert at designing efficient assessment strategies using binary search.

Your goal: Determine what skill/concept to test next to most efficiently narrow down the student's level (1-5).

BINARY SEARCH PRINCIPLES:
- With 5 levels, you need at most 3-4 well-chosen questions to converge
- Each question should halve the remaining uncertainty about the level
- If previous answer was CORRECT → probe HIGHER (test harder concepts)
- If previous answer was INCORRECT → probe LOWER (test easier concepts)
- If previous answer was PARTIAL → stay at similar level, test adjacent concept

LEVEL RANGES:
- Level 1-2: Basic recall, simple applications
- Level 3: Grade-appropriate understanding, standard problems
- Level 4-5: Advanced reasoning, complex applications, connections

OUTPUT GUIDELINES:
- target_skill: Be SPECIFIC (e.g., "solving quadratic equations by factoring" not "algebra")
- reasoning: Explain how this narrows the level uncertainty
- probe_direction: Match it to the previous response pattern"""
)


class QuestionStrategyAgent(Agent):
    """Sub-agent that decides what skill/concept to test next."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _strategy_agent

    def _build_prompt(
        self,
        topic_name: str,
        grade_level: int,
        current_level_estimate: int,
        level_confidence: float,
        previous_correctness: Optional[str] = None,
        previous_difficulty: Optional[str] = None,
        knowledge_gaps: Optional[list] = None,
        strengths: Optional[list] = None,
    ) -> str:
        """Build the prompt for strategy generation."""
        parts = [
            f"Topic: {topic_name}",
            f"Grade Level: {grade_level}",
            f"Current Level Estimate: {current_level_estimate}/5 (confidence: {level_confidence:.0%})",
        ]
        
        if previous_correctness:
            parts.append(f"\nPrevious Response: {previous_correctness.upper()}")
            if previous_difficulty:
                parts.append(f"Previous Difficulty: {previous_difficulty}")
        
        if knowledge_gaps:
            parts.append(f"Identified Knowledge Gaps: {', '.join(knowledge_gaps)}")
        
        if strengths:
            parts.append(f"Demonstrated Strengths: {', '.join(strengths)}")
        
        parts.append("\nDetermine the best skill to test next to narrow down the student's true level.")
        
        return "\n".join(parts)

    async def run(
        self,
        topic_name: str,
        grade_level: int,
        current_level_estimate: int,
        level_confidence: float,
        previous_correctness: Optional[str] = None,
        previous_difficulty: Optional[str] = None,
        knowledge_gaps: Optional[list] = None,
        strengths: Optional[list] = None,
    ) -> QuestionStrategy:
        """Get the recommended question strategy."""
        prompt = self._build_prompt(
            topic_name=topic_name,
            grade_level=grade_level,
            current_level_estimate=current_level_estimate,
            level_confidence=level_confidence,
            previous_correctness=previous_correctness,
            previous_difficulty=previous_difficulty,
            knowledge_gaps=knowledge_gaps,
            strengths=strengths,
        )
        result = await self._pydantic_agent.run(prompt)
        return result.output
