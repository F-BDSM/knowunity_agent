"""Evaluation agent for assessing student responses and determining cognitive level."""

import dspy
from typing import Optional, Dict, Any


class EvaluateResponse(dspy.Signature):
    """Evaluate a student's response to determine their understanding level and guide next steps."""

    question: str = dspy.InputField(desc="The question that was asked")
    student_response: str = dspy.InputField(desc="The student's response to the question")
    expected_answer: str = dspy.InputField(desc="The expected/correct answer")
    current_cognitive_level: str = dspy.InputField(desc="Current cognitive level: Recall & Facts, Procedural, Conceptual, Application, or Synthesis")
    topic: str = dspy.InputField(desc="The topic being tutored")
    conversation_history: Optional[str] = dspy.InputField(desc="Recent conversation history for context", default=None)

    understanding_score: int = dspy.OutputField(desc="Score from 1-5: 1=no understanding, 2=minimal, 3=partial, 4=good, 5=excellent understanding")
    is_correct: bool = dspy.OutputField(desc="Whether the answer is fundamentally correct")
    strengths: str = dspy.OutputField(desc="What the student understood well")
    weaknesses: str = dspy.OutputField(desc="What the student missed or misunderstood")
    suggested_action: str = dspy.OutputField(desc="One of: 'stay' (same level), 'advance' (next level), 'simplify' (easier question at same level)")
    reasoning: str = dspy.OutputField(desc="Brief explanation of the evaluation")


class EvaluationAgent:
    """Agent that evaluates student responses to determine understanding level."""

    def __init__(self, api_key: str, model: str):
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)
        self.evaluator = dspy.ChainOfThought(EvaluateResponse)

    def evaluate(
        self,
        question: str,
        student_response: str,
        expected_answer: str,
        current_cognitive_level: str,
        topic: str,
        conversation_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a student response and provide guidance.
        
        Returns:
            dict with understanding_score, is_correct, strengths, weaknesses,
            suggested_action, and reasoning
        """
        # Format conversation history if provided
        history_str = None
        if conversation_history:
            history_lines = []
            for entry in conversation_history[-3:]:  # Last 3 exchanges
                history_lines.append(f"Q: {entry['question']}")
                history_lines.append(f"A: {entry['response']}")
            history_str = "\n".join(history_lines) if history_lines else None

        result = self.evaluator(
            question=question,
            student_response=student_response,
            expected_answer=expected_answer,
            current_cognitive_level=current_cognitive_level,
            topic=topic,
            conversation_history=history_str,
        )

        return {
            "understanding_score": int(result.understanding_score),
            "is_correct": result.is_correct,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "suggested_action": result.suggested_action,
            "reasoning": result.reasoning,
        }
