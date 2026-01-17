"""
Multi-Agent Tutoring System for Knowunity Agent Olympics.

Three-agent architecture:
1. Evaluator Agent - Analyzes student understanding (1-5)
2. Tutor Agent - Provides explanations when score < 4
3. Questioner Agent - Generates next question based on score
"""

import os
import json
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import dspy
from dotenv import load_dotenv

from api import get_students, get_students_topics, start_conversation, interact

load_dotenv()


# Subject mapping with topics and types
SUBJECT_MAP = {
    "Math": {"topics": ["Linear Functions", "Quadratics", "Fractions and Decimals"], "type": "STEM"},
    "History": {"topics": ["French Revolution", "WWII", "Ancient Rome"], "type": "HUMANITIES"},
    "Physics": {"topics": ["Newton's Laws", "Electricity"], "type": "STEM"},
    "Chemistry": {"topics": ["Atomic Structure", "Chemical Reactions"], "type": "STEM"},
    "Biology": {"topics": ["Cell Structure", "Genetics"], "type": "STEM"},
    "English": {"topics": ["Grammar", "Literature Analysis"], "type": "HUMANITIES"},
    "Geography": {"topics": ["Climate Zones", "Population"], "type": "HUMANITIES"},
}


@dataclass
class EvaluationResult:
    """Structured evaluation output."""
    understanding_score: int  # 1-5
    reasoning: str
    misconceptions: List[str]


class EvaluatorSignature(dspy.Signature):
    """Analyze student understanding from their response."""
    
    student_message: str = dspy.InputField(desc="The student's latest message")
    chat_history: str = dspy.InputField(desc="Previous conversation context")
    topic: str = dspy.InputField(desc="The subject topic being taught")
    
    understanding_score: int = dspy.OutputField(desc="Score 1-5: 1=no understanding, 2=minimal, 3=partial, 4=good, 5=excellent")
    reasoning: str = dspy.OutputField(desc="Evidence and explanation for the score")
    misconceptions: str = dspy.OutputField(desc="Comma-separated list of misconceptions or gaps identified")


class TutorSignature(dspy.Signature):
    """Generate empathetic explanation to address misconceptions."""
    
    misconceptions: str = dspy.InputField(desc="Student's misconceptions or gaps")
    topic: str = dspy.InputField(desc="The subject topic")
    subject_type: str = dspy.InputField(desc="Subject type: STEM or HUMANITIES")
    
    explanation: str = dspy.OutputField(desc="Short, empathetic explanation or hint to correct the student")


class QuestionerSignature(dspy.Signature):
    """Generate next question based on understanding level."""
    
    understanding_score: int = dspy.InputField(desc="Current understanding score 1-5")
    topic: str = dspy.InputField(desc="The subject topic")
    subject_type: str = dspy.InputField(desc="Subject type: STEM or HUMANITIES")
    chat_history: str = dspy.InputField(desc="Previous questions to avoid repetition")
    previous_questions: str = dspy.InputField(desc="List of all questions already asked. NEVER repeat these questions or ask about the same concept.")
    
    question: str = dspy.OutputField(desc="The next question to ask. MUST BE DIFFERENT from previous questions. Score 1-2: Recall/Definition. Score 3: Conceptual/Why. Score 4-5: Synthesis/What-If")


class EvaluatorAgent:
    """The Analyst - Analyzes student understanding."""
    
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.evaluator = dspy.ChainOfThought(EvaluatorSignature)
    
    def evaluate(self, student_message: str, chat_history: str, topic: str) -> EvaluationResult:
        """Analyze student's understanding and return structured result."""
        result = self.evaluator(
            student_message=student_message,
            chat_history=chat_history,
            topic=topic
        )
        
        # Parse misconceptions from comma-separated string
        misconceptions = [m.strip() for m in result.misconceptions.split(",") if m.strip()]
        
        return EvaluationResult(
            understanding_score=int(result.understanding_score),
            reasoning=result.reasoning,
            misconceptions=misconceptions
        )


class TutorAgent:
    """The Teacher - Provides explanations when score < 4."""
    
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.tutor = dspy.ChainOfThought(TutorSignature)
    
    def explain(self, misconceptions: List[str], topic: str, subject_type: str, score: int) -> Optional[str]:
        """Generate explanation. Returns None if score >= 4."""
        if score >= 4:
            return None
        
        if not misconceptions:
            return None
        
        result = self.tutor(
            misconceptions=", ".join(misconceptions),
            topic=topic,
            subject_type=subject_type
        )
        
        return result.explanation


class QuestionerAgent:
    """The Prober - Generates next question based on understanding level."""
    
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.questioner = dspy.ChainOfThought(QuestionerSignature)
    
    def generate_question(self, understanding_score: int, topic: str, subject_type: str, chat_history: str, previous_questions: str) -> str:
        """Generate next question appropriate for the understanding level."""
        result = self.questioner(
            understanding_score=understanding_score,
            topic=topic,
            subject_type=subject_type,
            chat_history=chat_history,
            previous_questions=previous_questions
        )
        
        return result.question


class TutoringSession:
    """The Orchestrator - Manages the 10-turn tutoring session."""
    
    def __init__(
        self,
        evaluator: EvaluatorAgent,
        tutor: TutorAgent,
        questioner: QuestionerAgent,
        conversation_id: str,
        topic: str,
        subject_name: str,
    ):
        self.evaluator = evaluator
        self.tutor = tutor
        self.questioner = questioner
        self.conversation_id = conversation_id
        self.topic = topic
        self.subject_name = subject_name
        
        # Get subject type from SUBJECT_MAP
        subject_info = SUBJECT_MAP.get(subject_name, {"type": "STEM"})
        self.subject_type = subject_info["type"]
        
        # State variables
        self.chat_history: List[Dict[str, Any]] = []
        self.current_score: int = 0
        self.turn_count: int = 0
        self.evaluation_logs: List[Dict[str, Any]] = []
        self.questions_asked: List[str] = []  # Track all questions asked
    
    def _format_chat_history(self) -> str:
        """Format chat history for agent consumption."""
        if not self.chat_history:
            return "No previous conversation."
        
        lines = []
        for entry in self.chat_history[-5:]:  # Last 5 exchanges
            lines.append(f"Q: {entry['question']}")
            lines.append(f"A: {entry['student_response']}")
        return "\n".join(lines)
    
    def _format_previous_questions(self) -> str:
        """Format previous questions as a numbered list."""
        if not self.questions_asked:
            return "No previous questions yet."
        return "\n".join([f"{i}. {q}" for i, q in enumerate(self.questions_asked, 1)])
    
    def run_turn(self, student_input: str, tutor_question: str) -> tuple[str, str, EvaluationResult]:
        """
        Execute one turn of the tutoring session.
        
        Returns:
            tuple of (merged_response, next_question, evaluation_result)
        """
        self.turn_count += 1
        
        # Step 1: Evaluate student's understanding
        chat_context = self._format_chat_history()
        evaluation = self.evaluator.evaluate(
            student_message=student_input,
            chat_history=chat_context,
            topic=self.topic
        )
        
        self.current_score = evaluation.understanding_score
        
        # Log evaluation (for debugging)
        log_entry = {
            "turn": self.turn_count,
            "evaluation": asdict(evaluation),
            "student_message": student_input
        }
        self.evaluation_logs.append(log_entry)
        
        # Step 2: Generate tutor explanation (if score < 4)
        tutor_output = self.tutor.explain(
            misconceptions=evaluation.misconceptions,
            topic=self.topic,
            subject_type=self.subject_type,
            score=evaluation.understanding_score
        )
        
        # Step 3: Generate next question
        next_question = self.questioner.generate_question(
            understanding_score=evaluation.understanding_score,
            topic=self.topic,
            subject_type=self.subject_type,
            chat_history=chat_context,
            previous_questions=self._format_previous_questions()
        )
        
        # Track this question
        self.questions_asked.append(next_question)
        
        # Step 4: Merge outputs
        merged_response = self._merge_outputs(tutor_output, next_question)
        
        # Update chat history
        self.chat_history.append({
            "question": tutor_question,
            "student_response": student_input,
            "evaluation_score": evaluation.understanding_score,
            "next_question": next_question
        })
        
        return merged_response, next_question, evaluation
    
    def _merge_outputs(self, tutor_output: Optional[str], next_question: str) -> str:
        """Combine tutor explanation and next question into one message."""
        parts = []
        
        if tutor_output:
            parts.append(tutor_output)
            parts.append("")  # Empty line separator
        
        parts.append(next_question)
        
        return "\n".join(parts)
    
    def get_final_score(self) -> float:
        """Calculate average understanding score across all turns."""
        if not self.evaluation_logs:
            return 0.0
        
        scores = [log["evaluation"]["understanding_score"] for log in self.evaluation_logs]
        return sum(scores) / len(scores)
    
    def print_session_summary(self):
        """Print final session statistics."""
        final_avg = self.get_final_score()
        print(f"\n{'='*60}")
        print(f"SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"Topic: {self.topic}")
        print(f"Total Turns: {self.turn_count}")
        print(f"Final Understanding Score: {round(final_avg)}/5")
        print(f"\nTurn-by-Turn Scores:")
        for log in self.evaluation_logs:
            score = log["evaluation"]["understanding_score"]
            print(f"  Turn {log['turn']}: {score}/5 - {log['evaluation']['reasoning'][:80]}...")
        print(f"{'='*60}")


def _extract_list(raw: Any, key: str) -> list:
    """Extract list from API response."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        data = raw.get(key)
        if isinstance(data, list):
            return data
    raise ValueError(f"Unexpected {key} response shape")


def select_item(items: list, item_type: str) -> Dict[str, Any]:
    """Display items and let user select one."""
    print(f"\n=== Available {item_type.title()}s ===")
    for i, item in enumerate(items, 1):
        name = item.get("name", "<unnamed>")
        item_id = item.get("id", "<no-id>")
        
        if item_type == "topic":
            grade = item.get("grade_level", "?")
            subject = item.get("subject_name", "")
            print(f"{i}. {name} (grade {grade}, {subject}) [{item_id[:8]}...]")
        else:
            print(f"{i}. {name} [{item_id[:8]}...]")

    while True:
        try:
            choice = int(input(f"\nSelect {item_type} number: "))
            if 1 <= choice <= len(items):
                return items[choice - 1]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Tutoring System - 10 Turn Session"
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["gemini", "openai"],
        help="LLM provider"
    )
    parser.add_argument(
        "--set-type",
        default="mini_dev",
        help="Student set type"
    )
    args = parser.parse_args()
    
    # Initialize LLM
    if args.provider == "gemini":
        model = "gemini/gemini-2.5-flash-lite"
        api_key = os.getenv("GEMINI_API_KEY")
    else:
        model = "openai/gpt-4o-mini"
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print(f"Error: {args.provider.upper()}_API_KEY not found")
        return
    
    lm = dspy.LM(model=model, api_key=api_key)
    dspy.configure(lm=lm)
    
    # Initialize agents
    evaluator = EvaluatorAgent(lm)
    tutor = TutorAgent(lm)
    questioner = QuestionerAgent(lm)
    
    # Select student
    students_response = get_students(set_type=args.set_type)
    students = _extract_list(students_response, "students")
    if not students:
        print("No students found.")
        return
    
    student = select_item(students, "student")
    student_id = student.get("id")
    student_name = student.get("name", "<unnamed>")
    print(f"\nSelected student: {student_name}")
    
    # Select topic
    topics_response = get_students_topics(student_id)
    topics = _extract_list(topics_response, "topics")
    if not topics:
        print("No topics found.")
        return
    
    topic = select_item(topics, "topic")
    topic_id = topic.get("id")
    topic_name = topic.get("name", "<unnamed>")
    subject_name = topic.get("subject_name", "Math")
    
    # Start conversation
    print("\nStarting conversation...")
    conversation_response = start_conversation(student_id, topic_id)
    conversation_id = conversation_response.get("conversation_id")
    
    if not conversation_id:
        print("Failed to start conversation.")
        return
    
    # Create tutoring session
    session = TutoringSession(
        evaluator=evaluator,
        tutor=tutor,
        questioner=questioner,
        conversation_id=conversation_id,
        topic=topic_name,
        subject_name=subject_name
    )
    
    print(f"\n{'='*60}")
    print(f"TUTORING SESSION STARTED")
    print(f"Topic: {topic_name} ({subject_name} - {session.subject_type})")
    print(f"Total Turns: 10")
    print(f"{'='*60}\n")
    
    # Generate initial question
    initial_question = questioner.generate_question(
        understanding_score=0,
        topic=topic_name,
        subject_type=session.subject_type,
        chat_history="Starting conversation.",
        previous_questions="No previous questions yet."
    )
    
    print(f"Tutor: {initial_question}\n")
    current_question = initial_question
    
    # Main loop: exactly 10 turns
    for turn in range(1, 11):
        try:
            # Get student response from API
            response = interact(conversation_id, current_question)
            student_response = response.get("student_response", "<no response>")
            print(f"Student: {student_response}\n")
            
            # Run turn through orchestrator
            merged_output, next_question, evaluation = session.run_turn(student_response, current_question)
            
            # Log evaluation (hidden from student, for debugging)
            print(f"[DEBUG - Turn {turn}] Score: {evaluation.understanding_score}/5")
            print(f"[DEBUG - Turn {turn}] Reasoning: {evaluation.reasoning}")
            if evaluation.misconceptions:
                print(f"[DEBUG - Turn {turn}] Misconceptions: {', '.join(evaluation.misconceptions)}")
            print()
            
            # Display merged response (feedback + next question)
            print(f"Tutor: {merged_output}\n")
            
            # Prepare for next turn
            if turn < 10:  # Don't ask after last turn
                current_question = next_question
                
                # Pause for user (optional)
                user_input = input("Press Enter to continue (or 'q' to quit): ").strip()
                if user_input.lower() in ("q", "quit", "exit"):
                    print("\nSession ended by user.")
                    break
        
        except Exception as e:
            print(f"Error during turn {turn}: {e}")
            break
    
    # Print final summary
    session.print_session_summary()


if __name__ == "__main__":
    main()
