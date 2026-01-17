from typing import List, Optional
from tqdm import tqdm
import dspy
from .student import Student
from .models import InteractionResult, ConversationTurn,QuestionAgentInput
from .agents import QuestionAgent,ScoringAgent
from .api import get_students_topics


class TutoringOrchestrator:

    def __init__(self,student_id:str,max_turns:int=10):
        self.max_turns = max_turns
        self.student = Student(student_id)
        self.current_conversation_id: Optional[str] = None
        self.question_agent = QuestionAgent()
        self.scoring_agent = ScoringAgent()
        self._messages: List[dict] = []

        self.q_a_pairs = []

    def run_session(self,topic_id:str,) -> List[dict]:

        self._messages = []

        self.student.set_topic(topic_id)
        last_student_response = None
        
        for i in tqdm(range(self.max_turns),desc="Running tutoring session"):
            topic = self.student.topic
                
            # 1. Call the question generator agent
            question_agent_input = QuestionAgentInput(
                grade_level=topic.grade_level,
                topic_name=topic.name,
                subject_name=topic.subject_name,
                previous_student_response=last_student_response
            )
            history = dspy.History(messages=self._messages) if len(self._messages) > 0 else None
            question,question_difficulty = self.question_agent.generate(request=question_agent_input,history=history)
            
            # 2. Send the question to the student
            result = self.student.get_response(question)            
            self._messages.append({
                "question": question,
                "request": question_agent_input
            })
            self.current_conversation_id = result.conversation_id
            last_student_response = result.student_response
        
            # 3. Store the question and answer pair
            self.q_a_pairs.append({
                "question": question,
                "question_difficulty":question_difficulty,
                "student_response": last_student_response
            })

        # 4. Call the scoring agent
        score = self.scoring_agent.generate(conversation=self.q_a_pairs)
        
        return score

    def get_all_topics(self,):
        pass

    def get_all_students(self,):
        pass