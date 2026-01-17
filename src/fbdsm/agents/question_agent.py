import dspy
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import StrEnum

from ..models import QuestionAgentInput


class QuestionDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GenerateQuestion(dspy.Signature):
    """Generate an educational question appropriate for the grade level and topic to help assess the student's knowledge."""

    request: QuestionAgentInput = dspy.InputField(desc="The request for the question generator")
    history: Optional[dspy.History] = dspy.InputField(desc="The conversation history")

    question: str = dspy.OutputField(desc="The generated educational question that would be appropriate to evaluate the skill of the student.")
    estimated_difficulty: QuestionDifficulty = dspy.OutputField(desc="The estimated difficulty of the question.")


class QuestionAgent(dspy.Module):

    def __init__(self,):    
        self.generator = dspy.ChainOfThought(GenerateQuestion)

    def forward(self, request:QuestionAgentInput, history:Optional[dspy.History]=None) -> Tuple[str,QuestionDifficulty]:
        result = self.generator(request=request,history=history)
        return result.question, result.estimated_difficulty
    
    def generate(self, request:QuestionAgentInput, history:Optional[dspy.History]=None)->str:
        return self(request,history=history)
