import dspy
import os
from typing import Optional, List
from dotenv import load_dotenv
load_dotenv()

class GenerateQuestion(dspy.Signature):
    """Generate an educational question appropriate for the grade level and topic to help tutor a student."""

    grade_level: str = dspy.InputField(desc="The student's grade level (e.g., '5th grade', 'high school')")
    topic: str = dspy.InputField(desc="The subject/topic for the question")
    cognitive_level: str = dspy.InputField(desc="Cognitive level: Recall & Facts, Procedural, Conceptual, Application, or Synthesis")
    level_description: str = dspy.InputField(desc="Description of what type of question to ask at this level")
    previous_answers: Optional[str] = dspy.InputField(desc="Recent conversation history (Q&A pairs) to build upon and adapt to student's understanding level", default=None)

    question: str = dspy.OutputField(desc="The generated educational question, adapted based on the student's previous responses")
    answer: str = dspy.OutputField(desc="The correct answer to the question that a student should give.")


class QuestionAgent:

    def __init__(self, api_key:str, model:str):
     
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)

        self.answer_history: List[str] = []
        self.generator = dspy.ChainOfThought(GenerateQuestion)

    def generate(self, grade_level: str, topic: str, cognitive_level: str, level_description: str, previous_answers: Optional[List[str]] = None) -> dict:
        """Generate a question, optionally based on previous answers."""

        answers = previous_answers or self.answer_history
        answers_str = "\n".join(answers) if answers else None
        
        result = self.generator(
            grade_level=str(grade_level),
            topic=topic,
            cognitive_level=cognitive_level,
            level_description=level_description,
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
    cognitive_level = "Recall & Facts"
    level_description = "Simple definitions. What is X?"
    
    if provider == "gemini":
        model = "gemini/gemini-2.5-flash-lite"
        api_key = os.getenv("GEMINI_API_KEY")
    elif provider == "openai":
        model = "openai/gpt-4.1-nano"
        api_key = os.getenv("OPENAI_API_KEY")

    question_agent = QuestionAgent(api_key=api_key, model=model)
    print(question_agent.generate(
        grade_level=grade_level,
        topic=topic,
        cognitive_level=cognitive_level,
        level_description=level_description
    ))