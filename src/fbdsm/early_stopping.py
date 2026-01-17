"""Early stopping logic for tutoring sessions."""
from dataclasses import dataclass
from typing import Optional
from enum import StrEnum


class StopReason(StrEnum):
    """Reasons for early termination of a tutoring session."""
    LEVEL_PLATEAU = "level_plateau"
    HIGH_CONFIDENCE = "high_confidence"
    MAX_TURNS_REACHED = "max_turns_reached"


@dataclass
class StopDecision:
    """Result of an early stopping check."""
    should_stop: bool
    reason: Optional[StopReason] = None
    message: Optional[str] = None


class EarlyStopping:
    """
    Early stopping controller for tutoring sessions.
    
    Uses a binary-search approach: with 5 levels, we need ~3-5 questions to converge.
    Primary termination trigger is level plateau (same estimate for N turns).
    
    Args:
        min_turns: Minimum turns before early stopping is considered
        plateau_threshold: Number of stable turns to trigger level plateau stop
        high_confidence_threshold: Confidence level threshold (0-1)
        high_confidence_stability: Required stability for high confidence stop
    """
    
    def __init__(
        self,
        min_turns: int = 2,
        plateau_threshold: int = 3,
        high_confidence_threshold: float = 0.9,
        high_confidence_stability: int = 2,
    ):
        self.min_turns = min_turns
        self.plateau_threshold = plateau_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.high_confidence_stability = high_confidence_stability
    
    def check(
        self,
        turn: int,
        level_stability_count: int,
        level_confidence: float,
        current_level_estimate: int,
    ) -> StopDecision:
        """
        Check if the session should terminate early based on statistics.
        
        Args:
            turn: Current turn number (1-indexed)
            level_stability_count: Number of consecutive turns with same level estimate
            level_confidence: Current confidence in level estimate (0-1)
            current_level_estimate: Current estimated level (1-5)
            
        Returns:
            StopDecision with should_stop flag and reason if stopping
        """
        # Don't stop before minimum turns
        if turn < self.min_turns:
            return StopDecision(should_stop=False)
        
        # Primary: Level plateau - if estimate stable for N turns, we've converged
        if level_stability_count >= self.plateau_threshold:
            return StopDecision(
                should_stop=True,
                reason=StopReason.LEVEL_PLATEAU,
                message=f"Level plateau detected ({current_level_estimate}/5 stable for {level_stability_count} turns) at turn {turn}"
            )
        
        # Tertiary: High confidence + some stability
        if (level_confidence >= self.high_confidence_threshold and 
            level_stability_count >= self.high_confidence_stability):
            return StopDecision(
                should_stop=True,
                reason=StopReason.HIGH_CONFIDENCE,
                message=f"High confidence ({level_confidence:.0%}) + stable level at turn {turn}"
            )
        
        return StopDecision(should_stop=False)
