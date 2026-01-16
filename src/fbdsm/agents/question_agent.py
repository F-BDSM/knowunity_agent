import dspy
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import StrEnum

from ..models import QuestionAgentInput



class GenerateQuestion(dspy.Signature):
    """Generate an educational question appropriate for the grade level and topic to help tutor a student."""

    request: QuestionAgentInput = dspy.InputField(desc="The request for the question generator")
    history: Optional[dspy.History] = dspy.InputField(desc="The conversation history")

    question: str = dspy.OutputField(desc="The generated educational question that would be appropriate for the student's grade level and topic.")


class QuestionAgent(dspy.Module):

    def __init__(self,):    
        self.generator = dspy.ChainOfThought(GenerateQuestion)

    def forward(self, request:QuestionAgentInput, history:Optional[dspy.History]=None) -> str:
        result = self.generator(request=request,history=history)
        return result.question
    
    def generate(self, request:QuestionAgentInput, history:Optional[dspy.History]=None)->str:
        return self(request,history=history)
