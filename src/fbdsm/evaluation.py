"""
Async evaluation framework for testing different tutoring strategies.

Usage:
    import asyncio
    from fbdsm.evaluation import Evaluator
    
    async def main():
        evaluator = Evaluator(dataset="mini_dev")
        results = await evaluator.run_evaluation()
        evaluator.print_report()
    
    asyncio.run(main())
"""
import asyncio
import json
import pathlib
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from tqdm.asyncio import tqdm

from .api import get_students, submit_mse_predictions, evaluate_tutoring, create_session
from .orchestrator import TutoringOrchestrator


@dataclass
class SessionResult:
    """Result from a single tutoring session."""
    student_id: str
    topic_id: str
    predicted_level: int
    duration_seconds: float
    num_turns: int = 10


@dataclass
class EvaluationResult:
    """Results from a full evaluation run."""
    dataset: str
    timestamp: str
    session_results: List[SessionResult]
    mse_score: Optional[float] = None
    tutoring_score: Optional[Dict[str, Any]] = None
    total_duration_seconds: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "timestamp": self.timestamp,
            "mse_score": self.mse_score,
            "tutoring_score": self.tutoring_score,
            "total_duration_seconds": self.total_duration_seconds,
            "num_sessions": len(self.session_results),
            "sessions": [
                {
                    "student_id": r.student_id,
                    "topic_id": r.topic_id,
                    "predicted_level": r.predicted_level,
                    "duration_seconds": r.duration_seconds,
                }
                for r in self.session_results
            ],
        }
    
    def save(self, filepath: str):
        """Save results to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class Evaluator:
    """
    Async evaluation framework for testing tutoring strategies.
    
    Args:
        dataset: Dataset to evaluate on ("mini_dev", "dev", or "test")
        max_turns: Maximum turns per tutoring session
        max_concurrent: Maximum concurrent student evaluations
    """
    
    def __init__(
        self,
        dataset: str = "mini_dev",
        max_turns: int = 3,
        max_concurrent: int = 3,
        early_stopping_plateau: int = 3,
    ):
        self.dataset = dataset
        self.max_turns = max_turns
        self.max_concurrent = max_concurrent
        self.early_stopping_plateau = early_stopping_plateau
        self._last_result: Optional[EvaluationResult] = None

    async def _run_single_student(
        self,
        session,
        student_id: str,
        semaphore: asyncio.Semaphore,
    ) -> List[SessionResult]:
        """Run tutoring sessions for a single student across all their topics."""
        async with semaphore:
            results = []
            orchestrator = TutoringOrchestrator(student_id,
            max_turns=self.max_turns, 
            early_stopping_plateau=self.early_stopping_plateau
            )
            topics = await orchestrator.get_all_topics(session)
            
            for topic in topics:
                start_time = time.time()
                predicted_level = await orchestrator.run_session(session, topic.id)
                duration = time.time() - start_time
                
                results.append(SessionResult(
                    student_id=student_id,
                    topic_id=topic.id,
                    predicted_level=predicted_level,
                    duration_seconds=duration,
                    num_turns=self.max_turns,
                ))
            
            return results

    async def run_evaluation(self, submit: bool = True) -> EvaluationResult:
        """
        Run full evaluation on the dataset.
        
        Args:
            submit: Whether to submit predictions and get MSE score
            
        Returns:
            EvaluationResult with all session results and scores
        """
        start_time = time.time()
        
        async with create_session() as session:
            # Get all students in the dataset
            students = await get_students(session, set_type=self.dataset)
            print(f"Running evaluation on {len(students)} students...")
            
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            # Run sessions for all students concurrently
            tasks = [
                self._run_single_student(session, s.id, semaphore)
                for s in students
            ]
            
            all_results: List[SessionResult] = []
            for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Evaluating students"):
                try:
                    session_results = await coro
                    all_results.extend(session_results)
                except Exception as e:
                    print(f"Error evaluating student: {e}")
            
            total_duration = time.time() - start_time
            
            # Create evaluation result
            result = EvaluationResult(
                dataset=self.dataset,
                timestamp=datetime.now().isoformat(),
                session_results=all_results,
                total_duration_seconds=total_duration,
            )

            try:
                pathlib.Path("eval_results").mkdir(exist_ok=True)
                result.save(f"eval_results/{self.dataset}_{datetime.now()}.json".replace(":", "_"))
            except Exception as e:
                print(f"Error saving result: {e}")
            
            # Submit predictions if requested
            if submit and all_results:
                predictions = {
                    (r.student_id, r.topic_id): r.predicted_level
                    for r in all_results
                }
                
                try:
                    mse_response = await submit_mse_predictions(session, predictions, set_type=self.dataset)
                    result.mse_score = mse_response.mse_score
                    print(f"MSE Score: {result.mse_score}")
                except Exception as e:
                    print(f"Error submitting MSE predictions: {e}")
                
                try:
                    tutoring_response = await evaluate_tutoring(session, set_type=self.dataset)
                    result.tutoring_score = tutoring_response
                    print(f"Tutoring Score: {tutoring_response}")
                except Exception as e:
                    print(f"Error getting tutoring score: {e}")
        
        self._last_result = result
        return result

    def print_report(self, result: Optional[EvaluationResult] = None):
        """Print a summary report of the evaluation."""
        result = result or self._last_result
        if not result:
            print("No evaluation results available. Run run_evaluation() first.")
            return
        
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        print(f"Dataset: {result.dataset}")
        print(f"Timestamp: {result.timestamp}")
        print(f"Total Sessions: {len(result.session_results)}")
        print(f"Total Duration: {result.total_duration_seconds:.1f}s")
        print("-" * 60)
        
        if result.mse_score is not None:
            print(f"MSE Score: {result.mse_score:.4f}")
        
        if result.tutoring_score:
            print(f"Tutoring Score: {result.tutoring_score}")
        
        # Level distribution
        level_counts = {}
        for r in result.session_results:
            level_counts[r.predicted_level] = level_counts.get(r.predicted_level, 0) + 1
        
        print("-" * 60)
        print("Predicted Level Distribution:")
        for level in sorted(level_counts.keys()):
            count = level_counts[level]
            pct = count / len(result.session_results) * 100
            bar = "█" * int(pct / 2)
            print(f"  Level {level}: {count:3d} ({pct:5.1f}%) {bar}")
        
        print("=" * 60)
