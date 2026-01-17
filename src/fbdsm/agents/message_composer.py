"""Message composer sub-agent for generating student-facing messages."""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent

from ..config import settings
from .base import Agent


class ComposedMessage(BaseModel):
    """Output from the message composer."""
    message: str = Field(
        description="The complete tutoring message to send to the student"
    )
    question: Optional[str] = Field(
        default=None,
        description="The specific question being asked, if any"
    )
    message_type: str = Field(
        description="Type of message: 'question', 'explanation', 'hint', 'encouragement', or 'challenge'"
    )


_composer_agent = PydanticAgent(
    settings.MODEL_NAME,
    output_type=ComposedMessage,
    instructions="""\
You are an expert tutor crafting engaging messages for K12 students (ages 14-18, German Gymnasium).

Your goal: Create a clear, encouraging, age-appropriate tutoring message.

MESSAGE STRUCTURE:
1. If there was a previous response, start with brief feedback (1 sentence max)
2. If incorrect, provide a concise hint or explanation
3. Ask the question clearly and directly
4. Keep total length SHORT (2-4 sentences max)

TONE GUIDELINES:
- Be warm and encouraging, never condescending
- Use casual but professional language
- Celebrate correct answers briefly, then move on
- For incorrect answers, be supportive and constructive

DIFFICULTY-APPROPRIATE LANGUAGE:
- EASY questions: Simple vocabulary, concrete examples
- MEDIUM questions: Standard academic language
- HARD questions: Can use more technical terms

QUESTION FORMULATION:
- Make questions clear and unambiguous
- For the target skill, ask ONE focused question
- Avoid compound questions or multiple parts"""
)


class MessageComposer(Agent):
    """Sub-agent that formulates student-facing tutoring messages."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _composer_agent

    def _build_prompt(
        self,
        topic_name: str,
        grade_level: int,
        target_skill: str,
        difficulty: str,
        previous_response: Optional[str] = None,
        previous_correctness: Optional[str] = None,
        strengths: Optional[list] = None,
        knowledge_gaps: Optional[list] = None,
    ) -> str:
        """Build the prompt for message composition."""
        parts = [
            f"Topic: {topic_name}",
            f"Grade Level: {grade_level}",
            f"Target Skill: {target_skill}",
            f"Required Difficulty: {difficulty.upper()}",
        ]
        
        if previous_response:
            parts.append(f"\n--- PREVIOUS INTERACTION ---")
            parts.append(f"Student Said: \"{previous_response}\"")
            if previous_correctness:
                parts.append(f"That was: {previous_correctness.upper()}")
        
        if knowledge_gaps:
            parts.append(f"Knowledge Gaps to Address: {', '.join(knowledge_gaps)}")
        
        if strengths:
            parts.append(f"Strengths to Build On: {', '.join(strengths)}")
        
        parts.append("\nCompose a tutoring message that asks about the target skill at the specified difficulty.")
        
        return "\n".join(parts)

    async def run(
        self,
        topic_name: str,
        grade_level: int,
        target_skill: str,
        difficulty: str,
        previous_response: Optional[str] = None,
        previous_correctness: Optional[str] = None,
        strengths: Optional[list] = None,
        knowledge_gaps: Optional[list] = None,
    ) -> ComposedMessage:
        """Compose a tutoring message."""
        prompt = self._build_prompt(
            topic_name=topic_name,
            grade_level=grade_level,
            target_skill=target_skill,
            difficulty=difficulty,
            previous_response=previous_response,
            previous_correctness=previous_correctness,
            strengths=strengths,
            knowledge_gaps=knowledge_gaps,
        )
        result = await self._pydantic_agent.run(prompt)
        return result.output
