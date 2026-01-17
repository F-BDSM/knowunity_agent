import asyncio
import aiohttp
from typing import List, Optional, Dict
from tqdm.asyncio import tqdm

from .student import Student
from .models import TutorAgentInput, AssessmentStats
from .agents import TutorAgent, ScoringAgent, ResponseAnalyzer, LevelInferrer
from .api import create_session
from .early_stopping import EarlyStopping


class TutoringOrchestrator:
    """Orchestrates adaptive tutoring sessions with real-time level inference."""

    def __init__(self, student_id: str, max_turns: int = 10):
        self.max_turns = max_turns
        self.student = Student(student_id)
        self.current_conversation_id: Optional[str] = None

        # Initialize agents
        self.tutor_agent = TutorAgent()
        self.scoring_agent = ScoringAgent()
        self.response_analyzer = ResponseAnalyzer()
        self.level_inferrer = LevelInferrer()

        self._messages: List[dict] = []
        self.q_a_pairs: List[dict] = []

    async def run_session(
        self,
        session: aiohttp.ClientSession,
        topic_id: str
    ) -> int:
        """
        Run an adaptive tutoring session for a given topic.
        
        Returns the predicted skill level (1-5).
        """
        # Reset state for new session
        self._messages = []
        self.q_a_pairs = []
        self.tutor_agent.reset_history()
        self.student.reset_session()

        # Load topics and set current
        topics = await self.student.get_topics(session)
        self.student.set_topic(topic_id)
        topic = self.student.topic

        # Initialize tracking variables
        last_student_response: Optional[str] = None
        last_question_difficulty: Optional[str] = None
        last_response_analysis = None
        current_level_estimate: int = 3  # Start with "at-grade" assumption
        level_confidence: float = 0.0  # Start with no confidence
        level_estimates = []
        level_estimates_confidences = []
        
        # Assessment statistics tracking
        difficulty_counts: Dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        correctness_counts: Dict[str, int] = {"correct": 0, "partial": 0, "incorrect": 0}
        confidence_levels: List[int] = []
        consecutive_correct: int = 0
        consecutive_incorrect: int = 0
        level_stability_count: int = 0
        previous_level_estimate: int = 3
        
        # Early stopping controller
        early_stopping = EarlyStopping()

        for i in tqdm(range(self.max_turns), desc="Running tutoring session"):
            # Build current assessment stats
            avg_confidence = sum(confidence_levels) / len(confidence_levels) if confidence_levels else 3.0
            
            # Compute confidence trend
            if len(confidence_levels) >= 3:
                recent = confidence_levels[-3:]
                if recent[-1] > recent[0]:
                    confidence_trend = "increasing"
                elif recent[-1] < recent[0]:
                    confidence_trend = "decreasing"
                else:
                    confidence_trend = "stable"
            else:
                confidence_trend = "stable"
            
            assessment_stats = AssessmentStats(
                total_questions=len(self.q_a_pairs),
                difficulty_distribution=difficulty_counts.copy(),
                correctness_distribution=correctness_counts.copy(),
                avg_confidence_level=avg_confidence,
                confidence_trend=confidence_trend,
                consecutive_correct=consecutive_correct,
                consecutive_incorrect=consecutive_incorrect,
                level_stability=level_stability_count,
            )
            
            # 1. Generate adaptive tutor response
            tutor_input = TutorAgentInput(
                grade_level=topic.grade_level,
                topic_name=topic.name,
                subject_name=topic.subject_name,
                current_turn=i + 1,
                max_turns=self.max_turns,
                current_level_estimate=current_level_estimate,
                level_confidence=level_confidence,
                previous_student_response=last_student_response,
                previous_question_difficulty=last_question_difficulty,
                previous_response_analysis=last_response_analysis,
                assessment_stats=assessment_stats,
            )
            tutor_message, question_difficulty = await self.tutor_agent.run(request=tutor_input)
            
            # Update difficulty counts
            diff_key = str(question_difficulty).lower()
            if diff_key in difficulty_counts:
                difficulty_counts[diff_key] += 1

            # 2. Send message to student and get response
            result = await self.student.get_response(session, tutor_message)
            self.current_conversation_id = result.conversation_id
            last_student_response = result.student_response
            last_question_difficulty = question_difficulty

            # 3. Analyze the student's response
            response_analysis = await self.response_analyzer.run(
                question=tutor_message,
                student_response=last_student_response,
                question_difficulty=str(question_difficulty),
                topic_name=topic.name,
                grade_level=topic.grade_level,
            )
            last_response_analysis = response_analysis
            
            # Update correctness counts and consecutive streaks
            correctness_key = str(response_analysis.correctness).lower()
            if correctness_key in correctness_counts:
                correctness_counts[correctness_key] += 1
            
            if response_analysis.correctness.value == "correct":
                consecutive_correct += 1
                consecutive_incorrect = 0
            elif response_analysis.correctness.value == "incorrect":
                consecutive_incorrect += 1
                consecutive_correct = 0
            else:  # partial
                consecutive_correct = 0
                consecutive_incorrect = 0
            
            # Track confidence level from response analysis
            confidence_levels.append(response_analysis.confidence_level)

            # 4. Store the turn data
            turn_data = {
                "question": tutor_message,
                "question_difficulty": str(question_difficulty),
                "student_response": last_student_response,
                "response_analysis": response_analysis.model_dump(),
            }
            self.q_a_pairs.append(turn_data)
            self._messages.append({
                "turn": i + 1,
                "tutor_message": tutor_message,
                "student_response": last_student_response,
                "request": tutor_input.model_dump(exclude={"previous_response_analysis", "assessment_stats"}),
            })

            # 5. Update level estimate (after first turn)
            if len(self.q_a_pairs) >= 1:
                level_estimate = await self.level_inferrer.run(
                    topic_name=topic.name,
                    grade_level=topic.grade_level,
                    conversation_history=self.q_a_pairs,
                    current_estimate=current_level_estimate,
                )
                
                # Track level stability
                if level_estimate.estimated_level == previous_level_estimate:
                    level_stability_count += 1
                else:
                    level_stability_count = 0
                previous_level_estimate = current_level_estimate
                
                current_level_estimate = level_estimate.estimated_level
                level_confidence = level_estimate.confidence
                level_estimates.append(level_estimate.estimated_level)
                level_estimates_confidences.append(level_estimate.confidence)
                
            # 6. Check for early termination
            stop_decision = early_stopping.check(
                turn=i + 1,
                level_stability_count=level_stability_count,
                level_confidence=level_confidence,
                current_level_estimate=current_level_estimate,
            )
            
            if stop_decision.should_stop:
                print(f"[Early Termination] {stop_decision.message}")
                break

        # 7. Final verification with scoring agent
        scoring_level = await self.scoring_agent.run(conversation=self.q_a_pairs)
        
        # Average the two predictions and round to nearest integer
        # Weight by level_inferrer confidence (higher confidence = more weight to inferrer)
        avg_confidence = sum(level_estimates_confidences) / len(level_estimates_confidences)
        inferrer_weight = 0.5 + (avg_confidence * 0.3)  # Range: 0.5 to 0.8
        scorer_weight = 1.0 - inferrer_weight
        
        # Average the level estimates from the level_inferrer
        estimated_level = sum(level_estimates) / len(level_estimates)
        weighted_average = (estimated_level * inferrer_weight) + (scoring_level * scorer_weight)
        final_level = round(weighted_average)
        
        # Clamp to valid range
        final_level = max(1, min(5, final_level))

        # Return the final predicted level
        return final_level

    async def run_sessions(self, session: aiohttp.ClientSession) -> List[dict]:
        """Run tutoring sessions for all topics assigned to the student."""
        topics = await self.student.get_topics(session)
        
        results = []
        for topic in topics:
            score = await self.run_session(session, topic.id)
            results.append({
                "student_id": self.student.student_id,
                "topic_id": topic.id,
                "predicted_level": score,
            })

        return results

    async def get_all_topics(self, session: aiohttp.ClientSession):
        """Get all topics for the current student."""
        return await self.student.get_topics(session)


async def run_quick_test(student_id: Optional[str] = None, topic_id: Optional[str] = None) -> int:
    """
    Quick test with a single student/topic combination.
    
    Useful for debugging and rapid iteration.
    """
    from .api import get_students
    
    async with create_session() as session:
        students = await get_students(session, set_type="mini_dev")
        
        if not student_id:
            student_id = students[0].id
        
        orchestrator = TutoringOrchestrator(student_id,max_turns=3)
        topics = await orchestrator.get_all_topics(session)
        
        if not topic_id:
            topic_id = topics[0].id
        
        print(f"Running quick test: student={student_id}, topic={topic_id}")
        import time
        start = time.time()
        level = await orchestrator.run_session(session, topic_id)
        duration = time.time() - start
        
        print(f"\nResult: Predicted Level = {level}")
        print(f"Duration: {duration:.1f}s")
        
        return level