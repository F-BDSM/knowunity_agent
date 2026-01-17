"""
Complete test workflow: Score all student-topic pairs and submit predictions.

This script combines the testing and submission steps into one workflow.
"""
from fbdsm.orchestrator import TutoringOrchestrator
from fbdsm.api import get_students, submit_mse_predictions
from concurrent.futures import ThreadPoolExecutor, as_completed
import fire
import json
import os
from datetime import datetime
from typing import Optional


def run_student(student_id: str):
    """Worker function that processes a single student."""
    try:
        orchestrator = TutoringOrchestrator(student_id)
        return {"student_id": student_id, "result": orchestrator.run_sessions(), "error": None}
    except Exception as e:
        return {"student_id": student_id, "result": None, "error": str(e)}


def main(
    dataset: str = "mini_dev",
    max_workers: int = None,
    output: str = None,
    submit: bool = True,
    save_results: bool = True
):
    """
    Run tutoring sessions for all students and optionally submit predictions.

    Args:
        dataset: Dataset name to fetch students from (default: 'mini_dev')
        max_workers: Number of parallel workers (default: CPU count)
        output: Output JSON file path (default: 'results_{dataset}_{timestamp}.json')
        submit: Whether to submit predictions to API (default: True)
        save_results: Whether to save results to JSON file (default: True)
    """
    if max_workers is None:
        # Use fewer workers since each student session spawns internal threads
        # and makes multiple API calls
        max_workers = min(os.cpu_count() or 2, 4)

    # Generate default output filename with timestamp
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"results_{dataset}_{timestamp}.json"

    print(f"{'='*60}")
    print(f"Starting test workflow")
    print(f"  Dataset: {dataset}")
    print(f"  Max workers: {max_workers}")
    print(f"  Output file: {output}")
    print(f"  Submit predictions: {submit}")
    print(f"{'='*60}\n")

    # Fetch students
    print(f"Fetching students from dataset '{dataset}'...")
    students = get_students(dataset)
    print(f"Found {len(students)} students\n")

    # Run tutoring sessions in parallel
    print(f"Running tutoring sessions for {len(students)} students...")
    outputs = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_student = {
            executor.submit(run_student, student.id): student.id
            for student in students
        }

        # Process results as they complete
        completed = 0
        for future in as_completed(future_to_student):
            student_id = future_to_student[future]
            completed += 1
            try:
                result = future.result()
                if result["error"]:
                    errors[result["student_id"]] = result["error"]
                    print(f"[{completed}/{len(students)}] X Student {result['student_id'][:8]}...: {result['error']}")
                else:
                    outputs[result["student_id"]] = result["result"]
                    num_topics = len(result["result"])
                    print(f"[{completed}/{len(students)}] OK Student {result['student_id'][:8]}... completed ({num_topics} topics)")
            except Exception as e:
                errors[student_id] = str(e)
                print(f"[{completed}/{len(students)}] X Student {student_id[:8]}...: {e}")

    # Save results
    final_output = {"results": outputs, "errors": errors}

    if save_results:
        with open(output, "w") as f:
            json.dump(final_output, f, indent=2)
        print(f"\n[OK] Results saved to: {output}")

    # Calculate statistics
    total_predictions = sum(len(topics) for topics in outputs.values())
    print(f"\n{'='*60}")
    print(f"Scoring complete:")
    print(f"  OK Students succeeded: {len(outputs)}/{len(students)}")
    print(f"  X  Students failed: {len(errors)}/{len(students)}")
    print(f"  Total predictions: {total_predictions}")
    print(f"{'='*60}\n")

    # Submit predictions if requested
    if submit and outputs:
        print(f"Submitting {total_predictions} predictions to API...")

        # Flatten all predictions
        all_predictions = []
        for student_id, topics in outputs.items():
            for topic_result in topics:
                all_predictions.append({
                    "student_id": topic_result["student_id"],
                    "topic_id": topic_result["topic_id"],
                    "predicted_level": topic_result["score"]
                })

        # Submit all predictions in a single batch request
        try:
            response = submit_mse_predictions(
                predictions=all_predictions,
                set_type=dataset
            )
            print(f"\n{'='*60}")
            print(f"Submission complete:")
            print(f"  OK Submitted {len(all_predictions)} predictions")
            print(f"  Response: {response}")
            print(f"{'='*60}")
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"Submission failed: {e}")
            print(f"{'='*60}")
    elif not submit:
        print(f"\nSkipping submission (--submit=False)")
        print(f"To submit later, run:")
        print(f"  python scripts/submit_predictions.py --input_file={output} --dataset={dataset}")


if __name__ == "__main__":
    fire.Fire(main)
