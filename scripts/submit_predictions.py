"""
Submit predictions from test results to the API.

Reads JSON output from test_tutor_orchestrator.py and submits all predictions
to the evaluation API.
"""
from fbdsm.api import submit_mse_predictions
import fire
import json
from typing import Optional


def submit_from_file(
    input_file: str = "out.json",
    dataset: str = "mini_dev",
    dry_run: bool = False
):
    """
    Submit predictions from a JSON file to the API.

    Args:
        input_file: Path to JSON file with test results (default: 'out.json')
        dataset: Dataset name (default: 'mini_dev')
        dry_run: If True, only print what would be submitted without actually submitting
    """
    # Load results from file
    with open(input_file, "r") as f:
        data = json.load(f)

    results = data.get("results", {})
    errors = data.get("errors", {})

    if not results:
        print("No results found in input file.")
        return

    # Flatten all student-topic pairs
    all_predictions = []
    for student_id, topics in results.items():
        for topic_result in topics:
            all_predictions.append({
                "student_id": topic_result["student_id"],
                "topic_id": topic_result["topic_id"],
                "predicted_level": topic_result["score"]
            })

    print(f"Found {len(all_predictions)} predictions to submit")
    print(f"Errors: {len(errors)} students failed")

    if dry_run:
        print("\n[DRY RUN] Would submit the following predictions:")
        for pred in all_predictions[:5]:  # Show first 5
            print(f"  - Student: {pred['student_id'][:8]}..., Topic: {pred['topic_id'][:8]}..., Score: {pred['predicted_level']}")
        if len(all_predictions) > 5:
            print(f"  ... and {len(all_predictions) - 5} more")
        return

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


def submit_batch(predictions: list, dataset: str = "mini_dev"):
    """
    Submit a batch of predictions in a single API call.

    Args:
        predictions: List of dicts with 'student_id', 'topic_id', 'predicted_level'
        dataset: Dataset name (default: 'mini_dev')

    Returns:
        API response dict
    """
    return submit_mse_predictions(predictions=predictions, set_type=dataset)


if __name__ == "__main__":
    fire.Fire(submit_from_file)
