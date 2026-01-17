import asyncio
import aiohttp
from typing import List, Optional
from tqdm.asyncio import tqdm

from .student import Student
from .models import TutorAgentInput
from .agents import TutorAgent, ScoringAgent, ResponseAnalyzer, LevelInferrer
from .api import create_session


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

        for i in tqdm(range(self.max_turns), desc="Running tutoring session"):
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
            )
            tutor_message, question_difficulty = await self.tutor_agent.generate(request=tutor_input)

            # 2. Send message to student and get response
            result = await self.student.get_response(session, tutor_message)
            self.current_conversation_id = result.conversation_id
            last_student_response = result.student_response
            last_question_difficulty = question_difficulty

            # 3. Analyze the student's response
            response_analysis = await self.response_analyzer.analyze(
                question=tutor_message,
                student_response=last_student_response,
                question_difficulty=str(question_difficulty),
                topic_name=topic.name,
                grade_level=topic.grade_level,
            )
            last_response_analysis = response_analysis

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
                "request": tutor_input.model_dump(exclude={"previous_response_analysis"}),
            })

            # 5. Update level estimate (after first turn)
            if len(self.q_a_pairs) >= 1:
                level_estimate = await self.level_inferrer.infer(
                    topic_name=topic.name,
                    grade_level=topic.grade_level,
                    conversation_history=self.q_a_pairs,
                    current_estimate=current_level_estimate,
                )
                current_level_estimate = level_estimate.estimated_level
                level_confidence = level_estimate.confidence

        # 6. Final verification with scoring agent
        scoring_level = await self.scoring_agent.generate(conversation=self.q_a_pairs)
        
        # Average the two predictions and round to nearest integer
        # Weight by level_inferrer confidence (higher confidence = more weight to inferrer)
        inferrer_weight = 0.5 + (level_confidence * 0.3)  # Range: 0.5 to 0.8
        scorer_weight = 1.0 - inferrer_weight
        
        weighted_average = (current_level_estimate * inferrer_weight) + (scoring_level * scorer_weight)
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
        
        orchestrator = TutoringOrchestrator(student_id)
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