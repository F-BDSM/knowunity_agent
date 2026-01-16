from f_bdsm.student import Student
from f_bdsm.interaction_result import InteractionResult
from typing import List

class TutoringOrchestrator:

    def __init__(self,max_turns:int=10):
        self.max_turns = max_turns
        self._current_session: List[InteractionResult] = []
        

    def run_session(self,student_id:str, topic_id:str,) -> List[InteractionResult]:

        self._current_session = []

        student = Student(student_id,topic_id)
        
        # 1. Call the question generator agent
        question = ...
        
        # 2. Send the question to the student
        answer = student.answer_tutor(question)

        # 4. If last_turn == max_turns, end the session
        if answer.turn_number == self.max_turns:
            return self._current_session
        
        # 5. Else, concatenate the student's answer with the previous context and go back to step 1
        else:
            self._current_session.append(answer)

        return self._current_session

    def get_all_topics(self,):
        pass

    def get_all_students(self,):
        pass