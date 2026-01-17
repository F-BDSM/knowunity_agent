"""Batch evaluation script for all students in mini_dev set."""

import os
import argparse
from typing import List, Dict, Any

import dspy
from dotenv import load_dotenv

from api import get_students, get_students_topics, start_conversation, interact, submit_mse_predictions, evaluate_tutoring
from multi_agent_tutor import (
    EvaluatorAgent,
    TutorAgent,
    QuestionerAgent,
    ComprehensiveTutoringAgent,
    TutoringSession,
    SUBJECT_MAP,
    _extract_list
)

load_dotenv()


def run_tutoring_session_silent(
    session: TutoringSession,
    questioner: QuestionerAgent,
    unified_agent: ComprehensiveTutoringAgent,
    conversation_id: str,
    topic_name: str,
    subject_type: str,
    show_conversation: bool = False,
    fast_mode: bool = False,
) -> int:
    """
    Run a tutoring session and return final score.
    
    Args:
        fast_mode: If True, use 5 turns instead of 10 and enable early stopping
    
    Returns:
        Rounded final understanding score (1-5)
    """
    max_turns = 5 if fast_mode else 10
    
    # Generate initial question using unified agent (faster than old QuestionerAgent)
    initial_result = unified_agent.process_turn(
        student_message="Starting conversation.",
        chat_history="No previous conversation.",
        topic=topic_name,
        subject_type=subject_type,
        previous_questions="No previous questions yet."
    )
    current_question = initial_result["next_question"]
    
    recent_scores = []  # Track last 3 scores for early stopping
    
    # Run up to max_turns
    for turn in range(1, max_turns + 1):
        try:
            # Get student response
            response = interact(conversation_id, current_question)
            student_response = response.get("student_response", "<no response>")
            
            # Run turn through orchestrator
            merged_output, next_question, evaluation = session.run_turn(student_response, current_question)
            
            # Track score for early stopping
            current_score = evaluation.get("understanding_score", 0) if isinstance(evaluation, dict) else 0
            recent_scores.append(current_score)
            if len(recent_scores) > 3:
                recent_scores.pop(0)
            
            # Optional: Show conversation details
            if show_conversation:
                print(f"      Turn {turn}")
                print(f"        Q: {current_question}")
                print(f"        Student: {student_response}")
                if merged_output:
                    print(f"        Tutor: {merged_output}")
                if evaluation and isinstance(evaluation, dict):
                    score = evaluation.get("understanding_score")
                    confidence = evaluation.get("confidence_level")
                    strengths = evaluation.get("strengths", [])
                    areas = evaluation.get("areas_to_improve", [])
                    if score is not None:
                        print(f"        Eval: score {score}/5 | confidence {confidence}%")
                    if strengths:
                        print(f"        Strengths: {', '.join(strengths)}")
                    if areas:
                        print(f"        Areas to improve: {', '.join(areas)}")
                if next_question:
                    print(f"        Next: {next_question}")
                print()

            # Early stopping: if last 3 scores are identical, student has converged
            if fast_mode and len(recent_scores) == 3 and len(set(recent_scores)) == 1:
                if show_conversation:
                    print(f"      → Early exit: score converged at {recent_scores[0]}")
                break
            
            # Prepare for next turn
            if turn < max_turns:
                current_question = next_question
        
        except Exception as e:
            print(f"  ⚠ Error on turn {turn}: {e}")
            break
    
    # Return rounded final score
    final_score = session.get_final_score()
    return round(final_score)


def evaluate_all_students(provider: str = "gemini", set_type: str = "mini_dev", show_conversation: bool = False, fast_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Evaluate all student-topic pairs and return predictions.
    
    Args:
        fast_mode: Use 5 turns instead of 10, enable early stopping (~50% faster)
    
    Returns:
        List of predictions with student_id, topic_id, predicted_level
    """
    # Initialize LLM
    if provider == "gemini":
        model = "gemini/gemini-2.0-flash-exp"
        api_key = os.getenv("GEMINI_API_KEY")
    else:
        model = "openai/gpt-4o-mini"
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print(f"Error: {provider.upper()}_API_KEY not found")
        return []
    
    lm = dspy.LM(model=model, api_key=api_key)
    dspy.configure(lm=lm)
    
    # Initialize agents (UNIFIED AGENT FOR 70% SPEEDUP)
    evaluator = EvaluatorAgent(lm)
    tutor = TutorAgent(lm)
    questioner = QuestionerAgent(lm)
    unified_agent = ComprehensiveTutoringAgent(lm)  # NEW: One agent to rule them all
    
    # Get all students
    students_response = get_students(set_type=set_type)
    students = _extract_list(students_response, "students")
    
    if not students:
        print("No students found.")
        return []
    
    print(f"\n{'='*60}")
    print(f"BATCH EVALUATION - {set_type}")
    print(f"Total Students: {len(students)}")
    print(f"{'='*60}\n")
    
    predictions = []
    total_pairs = 0
    completed_pairs = 0
    
    # Process each student
    for student_idx, student in enumerate(students, 1):
        student_id = student.get("id")
        student_name = student.get("name", "<unnamed>")
        
        print(f"[{student_idx}/{len(students)}] Student: {student_name}")
        
        # Get topics for this student
        topics_response = get_students_topics(student_id)
        topics = _extract_list(topics_response, "topics")
        
        if not topics:
            print(f"  ⚠ No topics found. Skipping.\n")
            continue
        
        total_pairs += len(topics)
        print(f"  Topics: {len(topics)}")
        
        # Process each topic
        for topic_idx, topic in enumerate(topics, 1):
            topic_id = topic.get("id")
            topic_name = topic.get("name", "<unnamed>")
            subject_name = topic.get("subject_name", "Math")
            
            if show_conversation:
                print(f"  [{topic_idx}/{len(topics)}] {topic_name} ({subject_name})")
            else:
                print(f"  [{topic_idx}/{len(topics)}] {topic_name} ({subject_name})... ", end="", flush=True)
            
            try:
                # Start conversation
                conversation_response = start_conversation(student_id, topic_id)
                conversation_id = conversation_response.get("conversation_id")
                
                if not conversation_id:
                    print("✗ Failed to start conversation")
                    continue
                
                # Get subject type
                subject_info = SUBJECT_MAP.get(subject_name, {"type": "STEM"})
                subject_type = subject_info["type"]
                
                # Create session
                session = TutoringSession(
                    evaluator=evaluator,
                    tutor=tutor,
                    questioner=questioner,
                    conversation_id=conversation_id,
                    topic=topic_name,
                    subject_name=subject_name,
                    unified_agent=unified_agent  # Use unified agent for speed
                )
                
                # Run tutoring session silently
                predicted_level = run_tutoring_session_silent(
                    session=session,
                    questioner=questioner,
                    unified_agent=unified_agent,
                    conversation_id=conversation_id,
                    topic_name=topic_name,
                    subject_type=subject_type,
                    show_conversation=show_conversation,
                    fast_mode=fast_mode
                )
                
                # Store prediction
                predictions.append({
                    "student_id": student_id,
                    "topic_id": topic_id,
                    "predicted_level": predicted_level
                })
                
                completed_pairs += 1
                if show_conversation:
                    print(f"    ✓ Final Score: {predicted_level}/5")
                else:
                    print(f"✓ Score: {predicted_level}/5")
            
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print()  # Blank line between students
    
    print(f"{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"Total pairs: {total_pairs}")
    print(f"Completed: {completed_pairs}")
    print(f"Failed: {total_pairs - completed_pairs}")
    print(f"{'='*60}\n")
    
    return predictions


def submit_predictions(predictions: List[Dict[str, Any]], set_type: str = "mini_dev") -> Dict[str, Any]:
    """
    Submit predictions and get MSE score.
    
    Returns:
        Response with MSE score
    """
    import requests
    
    BASE_URL = "https://knowunity-agent-olympics-2026-api.vercel.app"
    API_KEY = os.getenv("API_KEY")
    
    if not API_KEY:
        print("Error: API_KEY not found in environment")
        return {}
    
    url = f"{BASE_URL}/evaluate/mse"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": API_KEY,
    }
    payload = {
        "predictions": predictions,
        "set_type": set_type,
    }
    
    print("Submitting predictions...")
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Batch evaluate all students and submit predictions"
    )
    parser.add_argument(
        "--provider",
        default="gemini",
        choices=["gemini", "openai"],
        help="LLM provider"
    )
    parser.add_argument(
        "--set-type",
        default="mini_dev",
        help="Student set type (mini_dev, dev, test)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run evaluation but don't submit predictions"
    )
    parser.add_argument(
        "--show-conversation",
        action="store_true",
        help="Display turn-by-turn tutor/student conversation during batch runs"
    )
    parser.add_argument(
        "--evaluate-tutoring",
        action="store_true",
        help="Evaluate tutoring quality for the given set without generating or submitting predictions"
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="Fast mode: use 5 turns instead of 10, enable early stopping (~50% faster)"
    )
    args = parser.parse_args()

    # If evaluating tutoring quality, call the API directly
    if args.evaluate_tutoring:
        try:
            result = evaluate_tutoring(set_type=args.set_type)
            print(f"\n{'='*60}")
            print(f"TUTORING QUALITY EVALUATION - {args.set_type}")
            print(f"{'='*60}")
            if isinstance(result, dict):
                avg = result.get("average_score")
                if avg is not None:
                    print(f"Average Score: {avg:.4f}")
                for k, v in result.items():
                    if k != "average_score":
                        print(f"{k}: {v}")
            else:
                print(result)
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"\n✗ Tutoring evaluation failed: {e}")
        return

    # Run prediction-based batch evaluation
    predictions = evaluate_all_students(
        provider=args.provider,
        set_type=args.set_type,
        show_conversation=args.show_conversation,
        fast_mode=args.fast_mode
    )
    
    if not predictions:
        print("No predictions generated. Exiting.")
        return
    
    print(f"Generated {len(predictions)} predictions.")
    
    if args.dry_run:
        print("\n[DRY RUN] Predictions:")
        for pred in predictions[:5]:  # Show first 5
            print(f"  Student: {pred['student_id'][:8]}... | Topic: {pred['topic_id'][:8]}... | Level: {pred['predicted_level']}")
        if len(predictions) > 5:
            print(f"  ... and {len(predictions) - 5} more")
        print("\nSkipping submission (dry-run mode)")
        return
    
    # Submit predictions
    try:
        result = submit_predictions(predictions, set_type=args.set_type)
        
        print(f"\n{'='*60}")
        print(f"SUBMISSION RESULT")
        print(f"{'='*60}")
        
        if "mse" in result:
            print(f"MSE Score: {result['mse']:.4f}")
        
        if "message" in result:
            print(f"Message: {result['message']}")
        
        # Print any additional fields
        for key, value in result.items():
            if key not in ["mse", "message"]:
                print(f"{key}: {value}")
        
        print(f"{'='*60}")
    
    except Exception as e:
        print(f"\n✗ Submission failed: {e}")


if __name__ == "__main__":
    main()
