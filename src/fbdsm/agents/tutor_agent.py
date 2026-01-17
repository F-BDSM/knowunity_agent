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
        "Your PRIMARY goal is to accurately determine the student's skill level (1-5) as quickly as possible, "
        "while ALSO providing helpful tutoring.\n\n"
        "ASSESSMENT STRATEGY:\n"
        "- Use strategic questions that efficiently narrow down the skill level\n"
        "- Early turns: Use diagnostic questions at medium difficulty to quickly gauge level\n"
        "- If student answers correctly: Increase difficulty to probe upper bounds\n"
        "- If student answers incorrectly: Decrease difficulty to find their floor\n"
        "- Use binary-search style questioning to converge on the true level quickly\n"
        "- By turn 5-6, you should have high confidence in the level estimate\n"
        "- Later turns: Confirm your estimate with targeted questions at that level\n\n"
        "TUTORING GUIDELINES:\n"
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
        remaining_turns = request.max_turns - request.current_turn + 1
        
        prompt_parts = [
            f"Subject: {request.subject_name}",
            f"Topic: {request.topic_name}",
            f"Grade Level: {request.grade_level}",
            f"\n--- TURN STATUS ---",
            f"Current Turn: {request.current_turn} of {request.max_turns}",
            f"Remaining Turns: {remaining_turns}",
            f"Current Level Estimate: {request.current_level_estimate}/5 (confidence: {request.level_confidence:.0%})",
        ]

        # Add strategic guidance based on turn number
        if request.current_turn == 1:
            prompt_parts.append("\n--- STRATEGY: DIAGNOSTIC ---")
            prompt_parts.append("This is your first question. Ask a MEDIUM difficulty diagnostic question to efficiently gauge the student's level.")
            prompt_parts.append("Choose a question that a level-3 student would answer correctly, but a level-1-2 student would struggle with.")
        elif request.current_turn <= 3:
            prompt_parts.append("\n--- STRATEGY: RAPID ASSESSMENT ---")
            prompt_parts.append("You're in early assessment phase. Use questions that help you quickly narrow down the skill level.")
            prompt_parts.append("If previous answers were correct, probe higher. If incorrect, probe lower.")
        elif request.current_turn <= 6:
            prompt_parts.append("\n--- STRATEGY: REFINEMENT ---")
            prompt_parts.append(f"You should be converging on a level estimate. Current estimate: {request.current_level_estimate}/5")
            prompt_parts.append("Ask questions targeted at confirming or adjusting your estimate.")
        else:
            prompt_parts.append("\n--- STRATEGY: CONFIRMATION ---")
            prompt_parts.append(f"Final turns. Confirm your level estimate of {request.current_level_estimate}/5.")
            prompt_parts.append("Focus on tutoring quality while maintaining your assessment accuracy.")

        if remaining_turns <= 2:
            prompt_parts.append(f"\n⚠️ ONLY {remaining_turns} TURN(S) LEFT - finalize your assessment!")

        if request.previous_student_response:
            prompt_parts.append(f"\n--- PREVIOUS INTERACTION ---")
            prompt_parts.append(f"Student Response: {request.previous_student_response}")

        if request.previous_response_analysis:
            analysis = request.previous_response_analysis
            prompt_parts.append(f"Response Correctness: {analysis.correctness}")
            if analysis.knowledge_gaps:
                prompt_parts.append(f"Knowledge Gaps: {', '.join(analysis.knowledge_gaps)}")
            if analysis.strengths:
                prompt_parts.append(f"Strengths: {', '.join(analysis.strengths)}")

        if request.previous_question_difficulty:
            prompt_parts.append(f"Previous Difficulty: {request.previous_question_difficulty}")

        # Add guidance based on response analysis
        prompt_parts.append("\n--- ACTION GUIDANCE ---")
        if request.previous_response_analysis:
            if request.previous_response_analysis.correctness == Correctness.INCORRECT:
                prompt_parts.append("Previous answer was INCORRECT. Provide a brief explanation, then ask an EASIER question.")
                prompt_parts.append("This suggests student level may be LOWER than estimated - adjust accordingly.")
            elif request.previous_response_analysis.correctness == Correctness.PARTIAL:
                prompt_parts.append("Previous answer was PARTIAL. Clarify any misconceptions, then ask a similar difficulty question.")
            else:
                prompt_parts.append("Previous answer was CORRECT. Offer brief encouragement, then INCREASE difficulty.")
                prompt_parts.append("This suggests student level may be HIGHER than estimated - adjust accordingly.")
        else:
            prompt_parts.append("Ask an appropriate diagnostic question to gauge the student's level.")

        return "\n".join(prompt_parts)

    async def generate(self, request: TutorAgentInput) -> Tuple[str, QuestionDifficulty]:
        """Generate a tutoring response."""
        prompt = self._build_prompt(request)

        result = await self.agent.run(
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
