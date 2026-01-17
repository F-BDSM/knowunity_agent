from typing import List, Optional
from tqdm import tqdm
from .student import Student
from .models import InteractionResult, TutorAgentInput
from .agents import TutorAgent, ScoringAgent, ResponseAnalyzer, LevelInferrer
from .api import get_students_topics
from concurrent.futures import ThreadPoolExecutor


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

    def run_session(self, topic_id: str) -> int:
        """
        Run an adaptive tutoring session for a given topic.
        
        Returns the predicted skill level (1-5).
        """
        # Reset state for new session
        self._messages = []
        self.q_a_pairs = []
        self.tutor_agent.reset_history()

        self.student.set_topic(topic_id)
        topic = self.student.topic

        # Initialize tracking variables
        last_student_response: Optional[str] = None
        last_question_difficulty: Optional[str] = None
        last_response_analysis = None
        current_level_estimate: int = 3  # Start with "at-grade" assumption

        for i in tqdm(range(self.max_turns), desc="Running tutoring session"):
            # 1. Generate adaptive tutor response
            tutor_input = TutorAgentInput(
                grade_level=topic.grade_level,
                topic_name=topic.name,
                subject_name=topic.subject_name,
                current_level_estimate=current_level_estimate,
                previous_student_response=last_student_response,
                previous_question_difficulty=last_question_difficulty,
                previous_response_analysis=last_response_analysis,
            )
            tutor_message, question_difficulty = self.tutor_agent.generate(request=tutor_input)

            # 2. Send message to student and get response
            result = self.student.get_response(tutor_message)
            self.current_conversation_id = result.conversation_id
            last_student_response = result.student_response
            last_question_difficulty = question_difficulty

            # 3. Analyze the student's response
            response_analysis = self.response_analyzer.analyze(
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
                level_estimate = self.level_inferrer.infer(
                    topic_name=topic.name,
                    grade_level=topic.grade_level,
                    conversation_history=self.q_a_pairs,
                    current_estimate=current_level_estimate,
                )
                current_level_estimate = level_estimate.estimated_level

        # Return the final predicted level
        return current_level_estimate

    def run_sessions(self) -> List[dict]:
        """Run tutoring sessions for all topics assigned to the student."""
        scores = []
        topic_ids = [topic.id for topic in self.student.topics]

        with ThreadPoolExecutor(max_workers=3) as executor:
            for score, topic_id in zip(executor.map(self.run_session, topic_ids), topic_ids):
                scores.append({
                    "student_id": self.student.student_id,
                    "topic_id": topic_id,
                    "predicted_level": score,
                })

        return scores

    def get_all_topics(self):
        """Get all topics for the current student."""
        return self.student.topics

    def get_all_students(self):
        """Placeholder for getting all students."""
        pass