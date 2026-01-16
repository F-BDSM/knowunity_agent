
class TutoringOrchestrator:

    def __init__(self,max_turns:int=10):
        self.max_turns = max_turns
        

    def run_session(self,student_id:str, topic_id:str,):
        # 1. Call the question generator agent
        
        # 2. Send the question to the student

        # 3. wait for the student's answer

        # 4. If last_turn == max_turns, end the session

        # 5. Else, concatenate the student's answer with the previous context and go back to step 1

        pass

    def get_all_topics(self,):
        pass

    def get_all_students(self,):
        pass