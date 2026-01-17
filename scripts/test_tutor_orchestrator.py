#!/usr/bin/env python
"""Test script for tutoring orchestrator."""
import asyncio
from typing import Optional
import time
import fire

from fbdsm.orchestrator import run_quick_test


def quick_test(student_id: Optional[str] = None, topic_id: Optional[str] = None) -> int:
    """
    Quick test with a single student/topic combination.
    
    Useful for debugging and rapid iteration.
    """
    return asyncio.run(run_quick_test(student_id=student_id, topic_id=topic_id))


if __name__ == "__main__":
    fire.Fire()
