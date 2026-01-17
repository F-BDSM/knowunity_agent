"""Tutor agent for answering student questions and providing explanations."""

import dspy
from typing import Optional, List


class AnswerStudentQuestion(dspy.Signature):
    """Answer a student's question with clear explanations appropriate for their level."""

    student_question: str = dspy.InputField(desc="The question the student is asking")
    topic: str = dspy.InputField(desc="The current topic being studied")
    grade_level: str = dspy.InputField(desc="The student's grade level")
    cognitive_level: str = dspy.InputField(desc="Current cognitive level: Recall & Facts, Procedural, Conceptual, Application, or Synthesis")
    conversation_history: Optional[str] = dspy.InputField(desc="Recent conversation context", default=None)

    answer: str = dspy.OutputField(desc="Clear, grade-appropriate answer to the student's question")
    follow_up_guidance: str = dspy.OutputField(desc="Brief guidance on what the student should focus on next")


class ProvideTutoringResponse(dspy.Signature):
    """Provide tutoring response to student's answer with feedback and guidance."""

    tutor_question: str = dspy.InputField(desc="The question that was asked by the tutor")
    student_answer: str = dspy.InputField(desc="The student's answer")
    expected_answer: str = dspy.InputField(desc="The expected/correct answer")
    evaluation: str = dspy.InputField(desc="Evaluation of the student's answer (strengths, weaknesses, score)")
    topic: str = dspy.InputField(desc="The current topic")
    grade_level: str = dspy.InputField(desc="The student's grade level")
    cognitive_level: str = dspy.InputField(desc="Current cognitive level")

    feedback: str = dspy.OutputField(desc="Constructive feedback on the student's answer")
    explanation: str = dspy.OutputField(desc="Explanation of the correct answer if needed")
    encouragement: str = dspy.OutputField(desc="Encouraging message to motivate the student")


class TutorAgent:
    """Agent that provides tutoring responses, answers questions, and gives feedback."""

    def __init__(self, api_key: str, model: str):
        self.lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self.lm)
        self.answer_generator = dspy.ChainOfThought(AnswerStudentQuestion)
        self.feedback_generator = dspy.ChainOfThought(ProvideTutoringResponse)

    def answer_question(
        self,
        student_question: str,
        topic: str,
        grade_level: str,
        cognitive_level: str,
        conversation_history: Optional[List] = None,
    ) -> dict:
        """
        Answer a question from the student.
        
        Returns:
            dict with 'answer' and 'follow_up_guidance'
        """
        # Format conversation history if provided
        history_str = None
        if conversation_history:
            history_lines = []
            for entry in conversation_history[-3:]:
                history_lines.append(f"Q: {entry['question']}")
                history_lines.append(f"A: {entry['response']}")
            history_str = "\n".join(history_lines) if history_lines else None

        result = self.answer_generator(
            student_question=student_question,
            topic=topic,
            grade_level=str(grade_level),
            cognitive_level=cognitive_level,
            conversation_history=history_str,
        )

        return {
            "answer": result.answer,
            "follow_up_guidance": result.follow_up_guidance,
        }

    def provide_feedback(
        self,
        tutor_question: str,
        student_answer: str,
        expected_answer: str,
        evaluation: dict,
        topic: str,
        grade_level: str,
        cognitive_level: str,
    ) -> dict:
        """
        Provide tutoring feedback on student's answer.
        
        Returns:
            dict with 'feedback', 'explanation', and 'encouragement'
        """
        # Format evaluation for the prompt
        eval_str = f"Score: {evaluation['understanding_score']}/5. "
        eval_str += f"Strengths: {evaluation['strengths']}. "
        eval_str += f"Weaknesses: {evaluation['weaknesses']}. "
        eval_str += f"Reasoning: {evaluation['reasoning']}"

        result = self.feedback_generator(
            tutor_question=tutor_question,
            student_answer=student_answer,
            expected_answer=expected_answer,
            evaluation=eval_str,
            topic=topic,
            grade_level=str(grade_level),
            cognitive_level=cognitive_level,
        )

        return {
            "feedback": result.feedback,
            "explanation": result.explanation,
            "encouragement": result.encouragement,
        }
