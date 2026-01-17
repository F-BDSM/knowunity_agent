from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ..config import settings
from .response_analyzer import ResponseAnalysis, Correctness


class LevelEstimate(BaseModel):
    """Structured output for skill level estimation."""
    estimated_level: int = Field(
        ge=1, le=5,
        description="Estimated skill level: 1=Struggling, 2=Below-grade, 3=At-grade, 4=Above-grade, 5=Advanced"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the estimate (0.0 to 1.0)"
    )
    reasoning: str = Field(
        description="Brief explanation for the level estimate"
    )


# Create the pydantic-ai agent
_level_inferrer = Agent(
    settings.MODEL_NAME,
    output_type=LevelEstimate,
    instructions=(
        "You are an educational assessment expert estimating student skill levels. "
        "Based on the conversation history and response analyses, determine the student's "
        "understanding level on a scale of 1-5:\n"
        "- Level 1 (Struggling): Needs fundamentals, lacks basic knowledge\n"
        "- Level 2 (Below-grade): Frequent mistakes, inconsistent understanding\n"
        "- Level 3 (At-grade): Core concepts okay, may struggle with complexity\n"
        "- Level 4 (Above-grade): Good grasp of concepts, understands nuance\n"
        "- Level 5 (Advanced): Expert understanding, handles complex applications\n"
        "Your confidence should increase as you see more responses."
    ),
)


class LevelInferrer:
    """Agent that infers student skill level based on conversation history."""

    def __init__(self):
        self.agent = _level_inferrer

    def _build_prompt(
        self,
        topic_name: str,
        grade_level: int,
        conversation_history: List[dict],
        current_estimate: Optional[int] = None,
    ) -> str:
        """Build the prompt for level inference."""
        prompt_parts = [
            f"Topic: {topic_name}",
            f"Grade Level: {grade_level}",
            "",
            "Conversation History:",
        ]

        for i, turn in enumerate(conversation_history, 1):
            prompt_parts.append(f"\n--- Turn {i} ---")
            prompt_parts.append(f"Question ({turn.get('question_difficulty', 'unknown')} difficulty): {turn.get('question', '')}")
            prompt_parts.append(f"Student Response: {turn.get('student_response', '')}")
            
            if 'response_analysis' in turn:
                analysis = turn['response_analysis']
                if isinstance(analysis, ResponseAnalysis):
                    prompt_parts.append(f"Correctness: {analysis.correctness}")
                    prompt_parts.append(f"Confidence: {analysis.confidence_level}/5")
                    if analysis.knowledge_gaps:
                        prompt_parts.append(f"Knowledge Gaps: {', '.join(analysis.knowledge_gaps)}")
                elif isinstance(analysis, dict):
                    prompt_parts.append(f"Correctness: {analysis.get('correctness', 'unknown')}")

        if current_estimate:
            prompt_parts.append(f"\nPrevious estimate: Level {current_estimate}")

        prompt_parts.append("\nBased on all responses, estimate the student's skill level (1-5).")

        return "\n".join(prompt_parts)

    def infer(
        self,
        topic_name: str,
        grade_level: int,
        conversation_history: List[dict],
        current_estimate: Optional[int] = None,
    ) -> LevelEstimate:
        """Infer student skill level from conversation history."""
        prompt = self._build_prompt(
            topic_name=topic_name,
            grade_level=grade_level,
            conversation_history=conversation_history,
            current_estimate=current_estimate,
        )
        result = self.agent.run_sync(prompt)
        return result.output
