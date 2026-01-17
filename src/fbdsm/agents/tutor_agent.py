"""
Refactored TutorAgent that orchestrates specialized sub-agents.

The TutorAgent delegates to:
1. QuestionStrategyAgent - decides what skill to test next
2. DifficultyAdvisor - recommends appropriate difficulty
3. MessageComposer - formulates the student-facing message
"""
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage
from enum import StrEnum

from ..models import TutorAgentInput
from .base import Agent
from .question_strategy import QuestionStrategyAgent, QuestionStrategy
from .difficulty_advisor import DifficultyAdvisor, DifficultyRecommendation, QuestionDifficulty
from .message_composer import MessageComposer, ComposedMessage


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
        description="Set to True if the assessment should end early"
    )
    # Metadata from sub-agents for observability
    strategy: Optional[QuestionStrategy] = Field(
        default=None,
        description="The strategy used for this turn"
    )


class TutorAgent(Agent):
    """
    Adaptive tutoring agent that orchestrates specialized sub-agents.
    
    Architecture:
    1. QuestionStrategyAgent → decides what to test (binary search)
    2. DifficultyAdvisor → recommends difficulty level
    3. MessageComposer → formulates the message
    """

    def __init__(self):
        super().__init__()
        # Sub-agents
        self._strategy_agent = QuestionStrategyAgent()
        self._difficulty_advisor = DifficultyAdvisor()
        self._message_composer = MessageComposer()
        
        # Conversation history for context
        self._message_history: List[dict] = []

    def _build_prompt(self, *args, **kwargs) -> str:
        """Not used - each sub-agent has its own prompt building."""
        raise NotImplementedError("TutorAgent uses sub-agents, not direct prompts")

    def _should_conclude(self, request: TutorAgentInput) -> bool:
        """
        Determine if the assessment should conclude early.
        
        Delegates to the EarlyStopping logic in the orchestrator,
        but provides a hint here based on assessment stats.
        """
        if not request.assessment_stats:
            return False
        
        stats = request.assessment_stats
        
        # High confidence + stability → conclude
        if request.level_confidence >= 0.85 and stats.level_stability >= 2:
            return True
        
        # Clear plateau → conclude
        if stats.level_stability >= 3:
            return True
        
        return False

    async def run(self, request: TutorAgentInput) -> Tuple[str, QuestionDifficulty, bool]:
        """
        Generate a tutoring response by orchestrating sub-agents.
        
        Returns:
            Tuple of (message, difficulty, should_conclude)
        """
        # Extract context from request
        previous_correctness = None
        previous_difficulty = request.previous_question_difficulty
        knowledge_gaps = None
        strengths = None
        
        if request.previous_response_analysis:
            analysis = request.previous_response_analysis
            previous_correctness = str(analysis.correctness.value) if hasattr(analysis.correctness, 'value') else str(analysis.correctness)
            knowledge_gaps = analysis.knowledge_gaps if hasattr(analysis, 'knowledge_gaps') else None
            strengths = analysis.strengths if hasattr(analysis, 'strengths') else None

        # Step 1: Get question strategy (what to test)
        strategy = await self._strategy_agent.run(
            topic_name=request.topic_name,
            grade_level=request.grade_level,
            current_level_estimate=request.current_level_estimate,
            level_confidence=request.level_confidence,
            previous_correctness=previous_correctness,
            previous_difficulty=previous_difficulty,
            knowledge_gaps=knowledge_gaps,
            strengths=strengths,
        )

        # Step 2: Get difficulty recommendation
        difficulty_rec = await self._difficulty_advisor.run(
            current_level_estimate=request.current_level_estimate,
            previous_correctness=previous_correctness,
            previous_difficulty=previous_difficulty,
            target_skill=strategy.target_skill,
            probe_direction=strategy.probe_direction,
        )

        # Step 3: Compose the message
        composed = await self._message_composer.run(
            topic_name=request.topic_name,
            grade_level=request.grade_level,
            target_skill=strategy.target_skill,
            difficulty=difficulty_rec.difficulty.value,
            previous_response=request.previous_student_response,
            previous_correctness=previous_correctness,
            strengths=strengths,
            knowledge_gaps=knowledge_gaps,
        )

        # Step 4: Determine if we should conclude
        should_conclude = self._should_conclude(request)

        # Store turn for history (for potential future context)
        self._message_history.append({
            "turn": request.current_turn,
            "strategy": strategy.model_dump(),
            "difficulty": difficulty_rec.difficulty.value,
            "message_type": composed.message_type,
        })

        return composed.message, difficulty_rec.difficulty, should_conclude

    def reset_history(self):
        """Reset the message history for a new session."""
        self._message_history = []
