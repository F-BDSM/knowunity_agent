from fbdsm.orchestrator import TutoringOrchestrator
from fbdsm.api import get_students, get_students_topics
from concurrent.futures import ProcessPoolExecutor, as_completed
import fire
import json
import os


def run_student(student_id: str):
    """Worker function that processes a single student."""
    try:
        orchestrator = TutoringOrchestrator(student_id)
        return {"student_id": student_id, "result": orchestrator.run_sessions(), "error": None}
    except Exception as e:
        return {"student_id": student_id, "result": None, "error": str(e)}


def main(dataset: str = "mini_dev", max_workers: int = None, output: str = "out.json"):
    """
    Run tutoring sessions for all students in parallel.
    
    Args:
        dataset: Dataset name to fetch students from (default: 'mini_dev')
        max_workers: Number of parallel workers (default: CPU count)
        output: Output JSON file path (default: 'out.json')
    """
    if max_workers is None:
        max_workers = os.cpu_count() or 2
    
    students = get_students(dataset)
    outputs = {}
    errors = {}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and track futures to student IDs
        future_to_student = {
            executor.submit(run_student, student.id): student.id 
            for student in students
        }
        
        # Process results as they complete
        for future in as_completed(future_to_student):
            student_id = future_to_student[future]
            try:
                result = future.result()
                if result["error"]:
                    errors[result["student_id"]] = result["error"]
                    print(f"[ERROR] Student {result['student_id']}: {result['error']}")
                else:
                    outputs[result["student_id"]] = result["result"]
                    print(f"[OK] Student {result['student_id']} completed")
            except Exception as e:
                errors[student_id] = str(e)
                print(f"[FATAL] Student {student_id}: {e}")
    
    # Save results
    final_output = {"results": outputs, "errors": errors}
    with open(output, "w") as f:
        json.dump(final_output, f, indent=2)
    
    print(f"\nCompleted: {len(outputs)} succeeded, {len(errors)} failed")
    print(f"Results saved to: {output}")


if __name__ == "__main__":
    fire.Fire(main)
