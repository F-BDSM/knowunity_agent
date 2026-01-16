import dspy
import os
from dotenv import load_dotenv
load_dotenv()

class EvaluateAnswer(dspy.Signature):
    """Evaluate if the reasoning and the final answer of the student is correct."""

    student_answer: str = dspy.InputField(desc="The answer that the student provided")
    correct_answer: str = dspy.InputField(desc="The correct answer to the posed question")

    scoring: float = dspy.OutputField(desc="The degree to which the student is correct, ranging from [0 (completely wrong), 1(everything is correct.)]")
    explanation: str = dspy.OutputField(desc="If the student made an error, correct the student and explain where his mistake lies.")
    
    
class EvaluationAgent:

    def __init__(self, api_key:str, model:str):
     
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)

        self.generator = dspy.ChainOfThought(EvaluateAnswer)

    def evaluate(self, student_answer, correct_answer) -> dict:
        """Generate a question, optionally based on previous answers."""

        result = self.generator(
            student_answer=student_answer,
            correct_answer=correct_answer
        )

        return {
            "scoring": result.scoring,
            "explanation": result.explanation,
        }
        
        
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

    student_answer = "30% of 100 is 100*0.3 so that should be 30."
    correct_answer = "30% of 100 is 30."
    evaluation_agent = EvaluationAgent(api_key=api_key, model=model)
    print(evaluation_agent.evaluate(student_answer=student_answer, correct_answer=correct_answer))