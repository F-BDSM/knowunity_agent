from typing import List
from enum import StrEnum
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import llm


class Score(StrEnum):
    STRUGGLING = "Struggling"
    BELOW_GRADE = "Below-grade"
    AT_GRADE = "At-grade"
    ABOVE_GRADE = "Above-grade"
    ADVANCED = "Advanced"


MAPPING = {
    Score.STRUGGLING: 1,
    Score.BELOW_GRADE: 2,
    Score.AT_GRADE: 3,
    Score.ABOVE_GRADE: 4,
    Score.ADVANCED: 5
}


class ScoreOutput(BaseModel):
    """Output schema for the scoring agent."""
    score: Score = Field(description="The level of the student's understanding of the topic.")
    rationale: str = Field(description="The rationale for the score.")


SYSTEM_PROMPT = """You are an expert educational assessor. Your task is to evaluate a student's understanding based on their responses to questions.

Score levels:
- Struggling (1): Student shows significant difficulty with basic concepts
- Below-grade (2): Student understands some basics but struggles with grade-level material
- At-grade (3): Student demonstrates expected understanding for their grade level
- Above-grade (4): Student shows understanding beyond grade-level expectations
- Advanced (5): Student demonstrates exceptional mastery and deep understanding

Guidelines:
- Consider the difficulty of questions when evaluating responses
- Look for patterns across all Q&A pairs, not just individual responses
- Consider partial credit - a mostly correct answer shows more understanding than a wrong one
- Evaluate conceptual understanding, not just factual recall"""


class ScoringAgent:
    def __init__(self):
        self.llm = llm.with_structured_output(ScoreOutput)

    def _build_prompt(self, conversation: List[dict]) -> str:
        prompt_parts = ["Evaluate the student's understanding based on the following Q&A session:\n"]

        for i, turn in enumerate(conversation, 1):
            question = turn.get("question", "N/A")
            response = turn.get("student_response", "N/A")
            difficulty = turn.get("question_difficulty", "unknown")
            prompt_parts.append(f"Turn {i} (Difficulty: {difficulty}):")
            prompt_parts.append(f"  Question: {question}")
            prompt_parts.append(f"  Student Response: {response}\n")

        prompt_parts.append("Based on the above conversation, assess the student's overall understanding level.")

        return "\n".join(prompt_parts)

    def forward(self, conversation: List[dict]) -> int:
        prompt = self._build_prompt(conversation)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        result: ScoreOutput = self.llm.invoke(messages)
        return MAPPING[result.score]

    def generate(self, conversation: List[dict]) -> int:
        return self.forward(conversation=conversation)
