#!/usr/bin/env python
"""CLI for running async evaluations and quick tests."""
import asyncio
import fire
from fbdsm.evaluation import Evaluator
from fbdsm.orchestrator import run_quick_test


def evaluate(
    dataset: str = "mini_dev",
    max_turns: int = 3,
    max_concurrent: int = 3,
    submit: bool = True,
    output: str = None,
):
    """
    Run full evaluation on a dataset.
    
    Args:
        dataset: Dataset to evaluate ("mini_dev", "dev", or "test")
        max_turns: Maximum turns per session
        max_concurrent: Number of concurrent student evaluations
        submit: Whether to submit predictions for scoring
        output: Optional path to save results JSON
    """
    async def _run():
        evaluator = Evaluator(
            dataset=dataset,
            max_turns=max_turns,
            max_concurrent=max_concurrent,
        )
        
        result = await evaluator.run_evaluation(submit=submit)
        evaluator.print_report()
        
        if output:
            result.save(output)
            print(f"\nResults saved to: {output}")
        
        return result.mse_score
    
    return asyncio.run(_run())


def test(student_id: str = None, topic_id: str = None):
    """
    Quick test with a single student/topic.
    
    Args:
        student_id: Optional specific student ID
        topic_id: Optional specific topic ID
    """
    return asyncio.run(run_quick_test(student_id=student_id, topic_id=topic_id))


if __name__ == "__main__":
    fire.Fire()
