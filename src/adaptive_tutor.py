"""Adaptive tutoring system with cognitive level progression."""

import argparse
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from api import get_students, get_students_topics, start_conversation, interact
from agents.question_agent import QuestionAgent
from agents.evaluation_agent import EvaluationAgent
from agents.tutor_agent import TutorAgent
from subject_categories import (
    get_subject_category,
    get_level_for_turn,
    get_level_config,
    SubjectCategory,
)

load_dotenv()


def _extract_list(raw: Any, key: str) -> list:
    """Extract list from API response (handles wrapped and direct formats)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        data = raw.get(key)
        if isinstance(data, list):
            return data
    raise ValueError(f"Unexpected {key} response shape; expected list or {{'{key}': [...]}}")


class AdaptiveTutor:
    """Adaptive tutoring system that progresses through cognitive levels."""

    def __init__(self, question_agent: QuestionAgent, evaluation_agent: EvaluationAgent, tutor_agent: TutorAgent):
        self.question_agent = question_agent
        self.evaluation_agent = evaluation_agent
        self.tutor_agent = tutor_agent
        self.turn_number = 0
        self.current_level = 1
        self.conversation_history = []
        self.final_rating: Optional[int] = None
        self.questions_at_current_level = []
        self.previous_level = None
        self.cumulative_scores = []  # Track understanding scores
        self.last_evaluation = None  # Store last evaluation for context

    def get_current_cognitive_level(self) -> int:
        """Determine current cognitive level based on turn number."""
        return get_level_for_turn(self.turn_number)

    def compute_understanding_score(self) -> Optional[float]:
        """Average understanding score across turns."""
        if not self.cumulative_scores:
            return None
        return sum(self.cumulative_scores) / len(self.cumulative_scores)

    def is_student_asking_question(self, response: str) -> bool:
        """Detect if student response contains a question."""
        # Simple heuristics to detect questions
        response = response.strip()
        if not response:
            return False
        
        # Check for question mark
        if "?" in response:
            return True
        
        # Check for common question starters
        question_words = [
            "what", "why", "how", "when", "where", "who",
            "can you", "could you", "would you", "is it", "are there",
            "do you", "does it", "explain", "help me", "i don't understand"
        ]
        response_lower = response.lower()
        for word in question_words:
            if response_lower.startswith(word):
                return True
        
        return False

    def evaluate_student_response(
        self,
        question: str,
        student_response: str,
        expected_answer: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        Use evaluation agent to assess student response and determine next steps.
        """
        level_config = get_level_config(self.current_level)
        cognitive_level = level_config["level"].value
        
        evaluation = self.evaluation_agent.evaluate(
            question=question,
            student_response=student_response,
            expected_answer=expected_answer,
            current_cognitive_level=cognitive_level,
            topic=topic,
            conversation_history=self.conversation_history,
        )
        
        self.last_evaluation = evaluation
        self.cumulative_scores.append(evaluation["understanding_score"])
        
        return evaluation

    def generate_question(self, topic: str, grade_level: int, subject_name: str, last_student_response: Optional[str] = None) -> Dict[str, str]:
        """Generate a question appropriate for current cognitive level."""
        self.turn_number += 1
        self.current_level = self.get_current_cognitive_level()
        
        # Reset question tracking when moving to a new level
        if self.previous_level != self.current_level:
            self.questions_at_current_level = []
            self.previous_level = self.current_level
        
        level_config = get_level_config(self.current_level)
        cognitive_level = level_config["level"]
        level_description = level_config["description"]
        
        subject_category = get_subject_category(subject_name)
        
        # Determine which turn within this level (1st or 2nd)
        min_turn, max_turn = level_config["turns"]
        turn_within_level = self.turn_number - min_turn + 1
        
        # Add variety instructions for 2nd turn at same level
        variety_instruction = ""
        if turn_within_level == 2:
            variety_instruction = " IMPORTANT: Ask a DIFFERENT style of question than before. Vary the format, angle, or specific aspect being tested."
        elif len(self.questions_at_current_level) > 0:
            variety_instruction = f" IMPORTANT: Do NOT repeat this question: '{self.questions_at_current_level[0]}'. Ask something different."
        
        # Add evaluation feedback if available
        eval_guidance = ""
        if self.last_evaluation:
            eval_guidance = f" Based on last evaluation: Student strengths: {self.last_evaluation['strengths']}. Student weaknesses: {self.last_evaluation['weaknesses']}. Action: {self.last_evaluation['suggested_action']}."
        
        # Add context about subject category to help question generation
        enhanced_description = f"{level_description} (Subject: {subject_name}, Category: {subject_category.value}){variety_instruction}{eval_guidance}"
        
        # Build conversation context for adaptive questioning
        conversation_context = []
        for entry in self.conversation_history[-3:]:  # Last 3 exchanges
            conversation_context.append(f"Q: {entry['question']}")
            conversation_context.append(f"A: {entry['response']}")
            if 'evaluation' in entry:
                conversation_context.append(f"Eval: Score {entry['evaluation']['understanding_score']}/5, {entry['evaluation']['reasoning']}")
        
        question_data = self.question_agent.generate(
            grade_level=str(grade_level),
            topic=topic,
            cognitive_level=cognitive_level.value,
            level_description=enhanced_description,
            previous_answers=conversation_context if conversation_context else None,
        )
        
        # Track this question
        self.questions_at_current_level.append(question_data["question"])
        
        return question_data

    def process_turn(self, student_response: str, tutor_question: str, expected_answer: str, topic: str) -> Dict[str, Any]:
        """
        Process a turn and determine next action using evaluation agent.
        
        Returns:
            dict with 'action' (continue/stop), 'rating', 'next_turn', etc.
        """
        # Evaluate the student response
        evaluation = self.evaluate_student_response(
            question=tutor_question,
            student_response=student_response,
            expected_answer=expected_answer,
            topic=topic,
        )
        
        # Store conversation history with evaluation
        self.conversation_history.append({
            "question": tutor_question,
            "response": student_response,
            "turn": self.turn_number,
            "level": self.current_level,
            "evaluation": evaluation,
        })
        
        level_config = get_level_config(self.current_level)
        suggested_action = evaluation["suggested_action"]
        understanding_score = evaluation["understanding_score"]
        
        min_turn, max_turn = level_config["turns"]
        
        result = {
            "current_turn": self.turn_number,
            "current_level": self.current_level,
            "cognitive_level": level_config["level"].value,
            "understanding_score": understanding_score,
            "evaluation": evaluation,
        }
        
        # Determine action based on evaluation agent's suggestion
        if suggested_action == "advance" and self.turn_number >= max_turn:
            # Advance to next level
            result["action"] = "advance"
            result["rating"] = level_config["rating_on_success"]
            result["next_turn"] = level_config["next_turn_on_success"]
            
            if result["next_turn"] is None:
                # Completed all levels
                result["action"] = "complete"
                self.final_rating = result["rating"]
        elif suggested_action == "simplify" or (understanding_score < 3 and self.turn_number >= max_turn):
            # Student struggling - stop here
            result["action"] = "stop"
            result["rating"] = max(1, self.current_level - 1)  # Rate based on last successful level
            self.final_rating = result["rating"]
        elif self.turn_number >= max_turn:
            # At end of level range but not clearly advancing - stay and reassess
            if understanding_score >= 3:
                result["action"] = "advance"
                result["rating"] = level_config["rating_on_success"]
                result["next_turn"] = level_config["next_turn_on_success"]
                
                if result["next_turn"] is None:
                    result["action"] = "complete"
                    self.final_rating = result["rating"]
            else:
                result["action"] = "stop"
                result["rating"] = max(1, self.current_level - 1)
                self.final_rating = result["rating"]
        else:
            # Continue at current level
            result["action"] = "continue"
        
        return result

    def format_progress_message(self, turn_result: Dict[str, Any]) -> str:
        """Format a progress message for the user."""
        action = turn_result["action"]
        level = turn_result["cognitive_level"]
        turn = turn_result["current_turn"]
        score = turn_result.get("understanding_score", "?")
        evaluation = turn_result.get("evaluation", {})
        reasoning = evaluation.get("reasoning", "")
        
        if action == "advance":
            return f"\n✓ Turn {turn} ({level}): Score {score}/5 - Advancing! {reasoning}"
        elif action == "stop":
            rating = turn_result.get("rating", "?")
            return f"\n⊗ Turn {turn} ({level}): Score {score}/5 - Stopping. Final rating: {rating}. {reasoning}"
        elif action == "complete":
            rating = turn_result.get("rating", "?")
            return f"\n★ Turn {turn} ({level}): Score {score}/5 - Completed! Final rating: {rating}. {reasoning}"
        else:
            return f"\n→ Turn {turn} ({level}): Score {score}/5 - Continuing. {reasoning}"


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


def run_adaptive_tutoring(
    conversation_id: str,
    topic_name: str,
    grade_level: int,
    subject_name: str,
    tutor: AdaptiveTutor,
) -> None:
    """Run adaptive tutoring session with cognitive level progression."""
    print(f"\n=== Adaptive Tutoring Session ===")
    print(f"Topic: {topic_name}")
    print(f"Subject: {subject_name}")
    print(f"Grade: {grade_level}")
    print("\nType 'quit' to exit early\n")

    while tutor.turn_number < 10:  # Max 10 turns
        # Generate question at appropriate level
        question_data = tutor.generate_question(topic_name, grade_level, subject_name)
        tutor_question = question_data["question"]
        expected_answer = question_data["answer"]
        
        print(f"\n[Turn {tutor.turn_number} - Level {tutor.current_level}]")
        print(f"Tutor: {tutor_question}")
        
        # Get student response via API
        try:
            response = interact(conversation_id, tutor_question)
            student_response = response.get("student_response", "<no response>")
            print(f"Student: {student_response}")
        except Exception as e:
            print(f"Error communicating with student: {e}")
            break
        
        # Check if student is asking a question instead of answering
        if tutor.is_student_asking_question(student_response):
            print("\n[Detected student question - providing answer...]")
            level_config = get_level_config(tutor.current_level)
            cognitive_level = level_config["level"].value
            
            answer_data = tutor.tutor_agent.answer_question(
                student_question=student_response,
                topic=topic_name,
                grade_level=str(grade_level),
                cognitive_level=cognitive_level,
                conversation_history=tutor.conversation_history,
            )
            
            print(f"\nTutor: {answer_data['answer']}")
            print(f"Guidance: {answer_data['follow_up_guidance']}")
            
            # Send tutor's answer back to student
            try:
                interact(conversation_id, answer_data['answer'])
            except Exception as e:
                print(f"Error sending answer: {e}")

            # Immediately re-ask the original tutor question to gather an answer for evaluation
            try:
                follow_up_prompt = f"Let's apply that. Please answer this question now: {tutor_question}"
                follow_response = interact(conversation_id, follow_up_prompt)
                student_response = follow_response.get("student_response", "<no response>")
                print(f"Student (after help): {student_response}")
            except Exception as e:
                print(f"Error getting follow-up response: {e}")
                break
        
        # Process turn and determine next action
        turn_result = tutor.process_turn(student_response, tutor_question, expected_answer, topic_name)
        
        # Provide tutoring feedback using tutor agent
        level_config = get_level_config(tutor.current_level)
        cognitive_level = level_config["level"].value
        evaluation = turn_result["evaluation"]
        
        feedback_data = tutor.tutor_agent.provide_feedback(
            tutor_question=tutor_question,
            student_answer=student_response,
            expected_answer=expected_answer,
            evaluation=evaluation,
            topic=topic_name,
            grade_level=str(grade_level),
            cognitive_level=cognitive_level,
        )
        
        # Display feedback to user (not sent to student API)
        print(f"\n--- Feedback ---")
        print(f"Assessment: {feedback_data['feedback']}")
        if evaluation['understanding_score'] < 4:
            print(f"Explanation: {feedback_data['explanation']}")
        print(f"Note: {feedback_data['encouragement']}")
        
        progress_msg = tutor.format_progress_message(turn_result)
        print(progress_msg)
        
        # Check if user wants to quit
        user_input = input("\nPress Enter to continue (or 'q' to quit): ").strip()
        if user_input.lower() in ("q", "quit", "exit"):
            print("Session ended by user.")
            final_score = tutor.compute_understanding_score()
            if final_score is not None:
                print(f"Final understanding score: {final_score:.2f}/5 over {len(tutor.cumulative_scores)} turns")
            break
        
        action = turn_result["action"]
        if action == "stop":
            print(f"\nSession ended. Final rating: {tutor.final_rating}")
            final_score = tutor.compute_understanding_score()
            if final_score is not None:
                print(f"Final understanding score: {final_score:.2f}/5 over {len(tutor.cumulative_scores)} turns")
            break
        elif action == "complete":
            print(f"\nSession completed! Final rating: {tutor.final_rating}")
            final_score = tutor.compute_understanding_score()
            if final_score is not None:
                print(f"Final understanding score: {final_score:.2f}/5 over {len(tutor.cumulative_scores)} turns")
            break
        elif action == "advance":
            next_turn = turn_result.get("next_turn")
            if next_turn:
                tutor.turn_number = next_turn - 1  # Will be incremented at start of next loop


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adaptive tutoring with cognitive level progression.",
    )
    parser.add_argument(
        "--set-type",
        default="mini_dev",
        help="Student set type (default: mini_dev)",
    )
    parser.add_argument(
        "--provider",
        default="gemini",
        choices=["gemini", "openai"],
        help="LLM provider for question generation",
    )
    args = parser.parse_args()

    # Initialize question and evaluation agents
    if args.provider == "gemini":
        model = "gemini/gemini-2.5-flash-lite"
        api_key = os.getenv("GEMINI_API_KEY")
    else:
        model = "openai/gpt-4.1-nano"
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print(f"Error: {args.provider.upper()}_API_KEY not found in environment")
        return

    question_agent = QuestionAgent(api_key=api_key, model=model)
    evaluation_agent = EvaluationAgent(api_key=api_key, model=model)
    tutor_agent = TutorAgent(api_key=api_key, model=model)
    tutor = AdaptiveTutor(question_agent, evaluation_agent, tutor_agent)

    # Fetch and select student
    students_response = get_students(set_type=args.set_type)
    students = _extract_list(students_response, "students")
    if not students:
        print("No students found.")
        return

    student = select_item(students, "student")
    student_id = student.get("id")
    student_name = student.get("name", "<unnamed>")
    print(f"\nSelected student: {student_name}")

    # Fetch and select topic
    topics_response = get_students_topics(student_id)
    topics = _extract_list(topics_response, "topics")
    if not topics:
        print("No topics found for this student.")
        return

    topic = select_item(topics, "topic")
    topic_id = topic.get("id")
    topic_name = topic.get("name", "<unnamed>")
    grade_level = topic.get("grade_level", 8)
    subject_name = topic.get("subject_name", "Unknown")

    # Start conversation
    print("\nStarting conversation...")
    conversation_response = start_conversation(student_id, topic_id)
    conversation_id = conversation_response.get("conversation_id")

    if not conversation_id:
        print("Failed to start conversation.")
        return

    # Run adaptive tutoring
    run_adaptive_tutoring(conversation_id, topic_name, grade_level, subject_name, tutor)


if __name__ == "__main__":
    main()
