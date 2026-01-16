import dspy
import os
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

class ScoreStudent(dspy.Signature):
    """Evaluate """

    study_session: List[Dict[str,str]] = dspy.InputField(desc="The history of the study session consisting of the questions asked by the tutor and the answer by the student")
    score: int = dspy.OutputField(desc="""
        Based on the study session - score the student based on the scoring scale:                  
        1:	Struggling – needs fundamentals
        2:	Below grade – frequent mistakes
        3:	At grade – core concepts ok
        4:	Above grade – occasional gaps
        5:	Advanced – ready for more
        """
    )
    
class ScoringAgent:

    def __init__(self, api_key:str, model:str):
     
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)

        self.generator = dspy.ChainOfThought(ScoreStudent)

    def score(self, history: List[Dict[str,str]]) -> int:
        """Generate a question, optionally based on previous answers."""

        result = self.generator(
            study_session=history
        )

        return result.score
        
        
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

    history = [{"question": "what is 30% of 100?", "answer":"30% of 100 is 100*0.3 so that should be 30."},
    {"question":"What is often refered to as the powerhouse of the cell?","answer":"I think it is the Ribosomes."}]
    
    scoring_agent = ScoringAgent(api_key=api_key, model=model)
    print(scoring_agent.score(history=history))