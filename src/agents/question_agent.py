import dspy
import os
from typing import Optional, List
from dotenv import load_dotenv
load_dotenv()

class GenerateQuestion(dspy.Signature):
    """Generate an educational question appropriate for the grade level and topic to help tutor a student."""

    grade_level: str = dspy.InputField(desc="The student's grade level (e.g., '5th grade', 'high school')")
    topic: str = dspy.InputField(desc="The subject/topic for the question")
    difficulty: str = dspy.OutputField(desc="Difficulty level: very easy, easy, medium, hard, or very hard")
    previous_answers: Optional[str] = dspy.InputField(desc="Previous answers to build upon, if any", default=None)

    question: str = dspy.OutputField(desc="The generated educational question")
    answer: str = dspy.OutputField(desc="The correct answer to the question that a student should give.")


class QuestionAgent:

    def __init__(self, api_key:str, model:str):
     
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)

        self.answer_history: List[str] = []
        self.generator = dspy.ChainOfThought(GenerateQuestion)

    def generate(self, grade_level:str, topic:str, difficulty:str, previous_answers: Optional[List[str]] = None) -> dict:
        
        difficulty = {1:"very easy", 2:"easy", 3:"medium", 4:"hard", 5:"very hard"}
        """Generate a question, optionally based on previous answers."""

        answers = previous_answers or self.answer_history
        answers_str = "\n".join(answers) if answers else None
        print("answer_string", answers_str)
        result = self.generator(
            grade_level=grade_level,
            topic=topic,
            difficulty=difficulty,
            previous_answers=answers_str
        )

        return {
            "question": result.question,
            "answer": result.answer
        }

    def add_answer(self, answer: str):
        """Track an answer for adaptive question generation."""
        self.answer_history.append(answer)

if __name__ == "__main__": 
    
    provider = "gemini"
    grade_level = 8
    topic = "Linear Algebra"
    difficulty = 1
    
    if provider == "gemini":
        model = "gemini/gemini-2.5-flash"
        api_key = os.getenv("GEMINI_API_KEY")
    elif provider == "openai":
        model = "openai/gpt-5-mini"
        api_key = os.getenv("OPENAI_API_KEY")

    question_agent = QuestionAgent(api_key=api_key, model=model)
    print(question_agent.generate(grade_level=grade_level, difficulty=1, topic=topic))