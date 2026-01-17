import dspy
from typing import List
from enum import StrEnum

class Score(StrEnum):
    STRUGGLING = "Struggling"
    BELOW_GRADE = "Below-grade"
    AT_GRADE = "At-grade"
    ABOVE_GRADE = "Above-grade"
    ADVANCED = "Advanced"


class GenerateScore(dspy.Signature):
    """Generate an educational question appropriate for the grade level and topic to help assess the student's knowledge."""

    conversation: List[dict] = dspy.InputField(desc="The question and answer turn.")

    score:Score = dspy.OutputField(desc="The level of the students understanding of the topic.")
    rationale:str = dspy.OutputField(desc="The rationales for the score.")

class ScoringAgent(dspy.Module):

    def __init__(self,):    
        self.generator = dspy.ChainOfThought(GenerateScore)

    def forward(self, conversation:List) -> Score:
        result = self.generator(conversation=conversation)
        return result.score
    
    def generate(self, conversation:List)->Score:
        return self(conversation=conversation)