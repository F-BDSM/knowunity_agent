from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.messages import ModelMessage
from enum import StrEnum

from ..models import TutorAgentInput
from ..config import settings
from .base import Agent
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
    should_conclude: bool = Field(
        default=False,
        description="Set to True if you believe the assessment should end early because you have high confidence in the student's level"
    )


# Create the pydantic-ai agent
_tutor_agent = PydanticAgent(
    settings.MODEL_NAME,
    output_type=TutorOutput,
    instructions=(
        "You are an adaptive AI tutor for K12 students (ages 14-18, German Gymnasium). "
        "Your PRIMARY goal is to accurately determine the student's skill level (1-5) as quickly as possible, "
        "while ALSO providing helpful tutoring.\n\n"
        "ASSESSMENT STRATEGY (Binary Search):\n"
        "- With 5 levels, you should converge to the correct level within 3-5 questions using binary search\n"
        "- Turn 1: Start at medium difficulty (targets level 3)\n"
        "- If correct: Jump to hard difficulty (targets level 4-5)\n"
        "- If incorrect: Drop to easy difficulty (targets level 1-2)\n"
        "- Each subsequent question should halve the remaining uncertainty\n"
        "- By turn 3-4, your level estimate should be stable and accurate\n\n"
        "EARLY TERMINATION (Plateau Detection):\n"
        "- Long assessments frustrate students - aim to finish in 3-5 turns\n"
        "- Set should_conclude=True when level estimate has been stable for 2+ turns\n"
        "- If you see a plateau in the level estimate (same value 2-3 times), conclude immediately\n"
        "- Be decisive: if the pattern is clear, end early rather than exhausting all turns\n\n"
        "TUTORING GUIDELINES:\n"
        "- For struggling students (level 1-2): Use simpler language, break down concepts\n"
        "- For at-grade students (level 3): Balance challenge with support\n"
        "- For advanced students (level 4-5): Offer complex problems and deeper exploration\n"
        "- Always be encouraging and supportive\n"
        "- Keep responses focused and age-appropriate"
    ),
)


class TutorAgent(Agent):
    """Adaptive tutoring agent that generates personalized tutoring content."""

    def __init__(self):
        super().__init__()
        self._pydantic_agent = _tutor_agent
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
        
        # Add assessment statistics if available
        if request.assessment_stats:
            stats = request.assessment_stats
            prompt_parts.append("\n--- ASSESSMENT STATISTICS ---")
            prompt_parts.append(f"Questions Asked: {stats.total_questions}")
            prompt_parts.append(f"Difficulty Distribution: {stats.difficulty_distribution}")
            prompt_parts.append(f"Correctness Distribution: {stats.correctness_distribution}")
            prompt_parts.append(f"Avg Student Confidence: {stats.avg_confidence_level:.1f}/5 (trend: {stats.confidence_trend})")
            prompt_parts.append(f"Consecutive Correct: {stats.consecutive_correct}, Consecutive Incorrect: {stats.consecutive_incorrect}")
            prompt_parts.append(f"Level Stability: {stats.level_stability} turns")
            
            # Add early termination hints
            should_consider_concluding = (
                (request.level_confidence >= 0.85 and stats.level_stability >= 2) or
                stats.consecutive_correct >= 3 or
                stats.consecutive_incorrect >= 3
            )
            if should_consider_concluding and request.current_turn >= 3:
                prompt_parts.append("\n⚡ EARLY TERMINATION RECOMMENDED: Pattern is clear enough to conclude assessment.")
                prompt_parts.append("Set should_conclude=True if you are confident in the level estimate.")

        return "\n".join(prompt_parts)

    async def run(self, request: TutorAgentInput) -> Tuple[str, QuestionDifficulty, bool]:
        """Generate a tutoring response.
        
        Returns:
            Tuple of (message, difficulty, should_conclude)
        """
        prompt = self._build_prompt(request)

        result = await self._pydantic_agent.run(
            prompt,
            message_history=self._message_history,
        )

        # Update message history for conversation continuity
        self._message_history = result.new_messages()

        output = result.output
        return output.message, output.difficulty, output.should_conclude

    def reset_history(self):
        """Reset the message history for a new session."""
        self._message_history = []
