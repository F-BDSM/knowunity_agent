from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from enum import StrEnum

from ..models import TutorAgentInput
from ..config import settings
from .response_analyzer import ResponseAnalysis, Correctness


class QuestionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TutorOutput(BaseModel):
    """Structured output for tutor responses."""
    message: str = Field(
        description="The complete tutor message to send to the student"
    )
    message_type: str = Field(
        description="Type of message: 'question', 'explanation', 'hint', 'encouragement', or 'challenge'"
    )
    question: Optional[str] = Field(
        default=None,
        description="If asking a question, the specific question being asked"
    )
    difficulty: QuestionDifficulty = Field(
        description="The difficulty level of any question or content being presented"
    )


# Create the pydantic-ai agent
_tutor_agent = Agent(
    settings.MODEL_NAME,
    output_type=TutorOutput,
    instructions=(
        "You are an adaptive AI tutor for K12 students (ages 14-18, German Gymnasium). "
        "Your role is to both assess student understanding AND provide helpful tutoring.\n\n"
        "Guidelines:\n"
        "- Adapt your approach based on the student's estimated skill level\n"
        "- If a student answered incorrectly, provide a helpful explanation before the next question\n"
        "- If a student answered correctly, offer encouragement and increase difficulty\n"
        "- For struggling students (level 1-2): Use simpler language, break down concepts\n"
        "- For at-grade students (level 3): Balance challenge with support\n"
        "- For advanced students (level 4-5): Offer complex problems and deeper exploration\n"
        "- Always be encouraging and supportive\n"
        "- Keep responses focused and age-appropriate"
    ),
)


class TutorAgent:
    """Adaptive tutoring agent that generates personalized tutoring content."""

    def __init__(self):
        self.agent = _tutor_agent
        self._message_history: List[ModelMessage] = []

    def _build_prompt(self, request: TutorAgentInput) -> str:
        """Build the prompt from the request."""
        prompt_parts = [
            f"Subject: {request.subject_name}",
            f"Topic: {request.topic_name}",
            f"Grade Level: {request.grade_level}",
            f"Current Estimated Student Level: {request.current_level_estimate}/5",
        ]

        if request.previous_student_response:
            prompt_parts.append(f"\nPrevious Student Response: {request.previous_student_response}")

        if request.previous_response_analysis:
            analysis = request.previous_response_analysis
            prompt_parts.append(f"Response was: {analysis.correctness}")
            if analysis.knowledge_gaps:
                prompt_parts.append(f"Knowledge Gaps: {', '.join(analysis.knowledge_gaps)}")
            if analysis.strengths:
                prompt_parts.append(f"Strengths: {', '.join(analysis.strengths)}")

        if request.previous_question_difficulty:
            prompt_parts.append(f"Previous Question Difficulty: {request.previous_question_difficulty}")

        # Add guidance based on context
        if request.previous_response_analysis:
            if request.previous_response_analysis.correctness == Correctness.INCORRECT:
                prompt_parts.append("\nProvide a brief explanation to help the student understand, then ask an easier follow-up question.")
            elif request.previous_response_analysis.correctness == Correctness.PARTIAL:
                prompt_parts.append("\nAcknowledge what was correct, clarify any misconceptions, then ask a similarly difficult question.")
            else:
                prompt_parts.append("\nOffer brief encouragement and increase difficulty appropriately.")
        else:
            prompt_parts.append("\nThis is the start of the session. Ask an appropriate diagnostic question to gauge the student's level.")

        return "\n".join(prompt_parts)

    def generate(self, request: TutorAgentInput) -> Tuple[str, QuestionDifficulty]:
        """Generate a tutoring response."""
        prompt = self._build_prompt(request)

        result = self.agent.run_sync(
            prompt,
            message_history=self._message_history,
        )

        # Update message history for conversation continuity
        self._message_history = result.new_messages()

        output = result.output
        # Return the full message (or question if specified) and difficulty
        return output.message, output.difficulty

    def reset_history(self):
        """Reset the message history for a new session."""
        self._message_history = []


# Backward compatibility alias
QuestionAgent = TutorAgent
