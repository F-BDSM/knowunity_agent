"""
Async API functions for Knowunity tutoring platform.

List of Functions:
- get_students()
- get_students_topics(student_id)
- get_subjects()
- get_topics(subject_id)
- start_conversation(student_id, topic_id)
- interact(conversation_id, tutor_message)
- submit_mse_predictions(predictions_dict)
- evaluate_tutoring()
"""
import aiohttp
from typing import List, Optional

from .config import settings
from .models import StudentInfo, TopicInfo, InteractionStartResult, InteractionResult, Topic


BASE_URL = settings.KNOWUNITY_API_URL
API_KEY = settings.KNOWUNITY_API_KEY


def _get_headers(with_api_key: bool = False) -> dict:
    """Get common headers for API requests."""
    headers = {"accept": "application/json"}
    if with_api_key:
        headers["content-type"] = "application/json"
        headers["X-Api-Key"] = API_KEY
    return headers


async def get_students(
    session: aiohttp.ClientSession,
    set_type: str = "mini_dev"
) -> List[StudentInfo]:
    """Get list of students in the dataset."""
    url = f"{BASE_URL}/students"
    params = {"set_type": set_type}
    
    async with session.get(url, params=params, headers=_get_headers()) as response:
        response.raise_for_status()
        data = await response.json()
        return [StudentInfo(**student) for student in data['students']]


async def get_students_topics(
    session: aiohttp.ClientSession,
    student_id: str
) -> List[TopicInfo]:
    """Get topics assigned to a student."""
    url = f"{BASE_URL}/students/{student_id}/topics"
    
    async with session.get(url, headers=_get_headers()) as response:
        response.raise_for_status()
        data = await response.json()
        return [TopicInfo(**topic) for topic in data['topics']]


async def get_subjects(session: aiohttp.ClientSession):
    """Get all subjects."""
    url = f"{BASE_URL}/subjects"
    
    async with session.get(url, headers=_get_headers()) as response:
        response.raise_for_status()
        return await response.json()


async def get_topics(
    session: aiohttp.ClientSession,
    subject_id: str
) -> List[TopicInfo]:
    """Get topics for a subject."""
    url = f"{BASE_URL}/topics"
    params = {"subject_id": subject_id}
    
    async with session.get(url, params=params, headers=_get_headers()) as response:
        response.raise_for_status()
        data = await response.json()
        return [TopicInfo(**topic) for topic in data]


async def start_conversation(
    session: aiohttp.ClientSession,
    student_id: str,
    topic_id: str
) -> InteractionStartResult:
    """Start a new tutoring conversation."""
    url = f"{BASE_URL}/interact/start"
    payload = {
        "student_id": student_id,
        "topic_id": topic_id,
    }
    
    async with session.post(url, json=payload, headers=_get_headers(with_api_key=True)) as response:
        response.raise_for_status()
        data = await response.json()
        return InteractionStartResult(**data)


async def interact(
    session: aiohttp.ClientSession,
    conversation_id: str,
    tutor_message: str
) -> InteractionResult:
    """Send a message in an ongoing conversation."""
    url = f"{BASE_URL}/interact"
    payload = {
        "conversation_id": conversation_id,
        "tutor_message": tutor_message,
    }
    
    async with session.post(url, json=payload, headers=_get_headers(with_api_key=True)) as response:
        response.raise_for_status()
        data = await response.json()
        return InteractionResult(tutor_message=tutor_message, **data)


async def submit_mse_predictions(
    session: aiohttp.ClientSession,
    predictions_dict: dict,
    set_type: str = "mini_dev"
):
    """
    Submit level predictions for MSE evaluation.
    
    Args:
        predictions_dict: dict of {(student_id, topic_id): predicted_level}
    """
    url = f"{BASE_URL}/evaluate/mse"
    payload = {
        "predictions": [
            {
                "student_id": student_id,
                "topic_id": topic_id,
                "predicted_level": predicted_level,
            }
            for (student_id, topic_id), predicted_level in predictions_dict.items()
        ],
        "set_type": set_type,
    }
    
    async with session.post(url, json=payload, headers=_get_headers(with_api_key=True)) as response:
        response.raise_for_status()
        return await response.json()


async def evaluate_tutoring(
    session: aiohttp.ClientSession,
    set_type: str = "mini_dev"
):
    """Evaluate tutoring quality."""
    url = f"{BASE_URL}/evaluate/tutoring"
    payload = {"set_type": set_type}
    
    async with session.post(url, json=payload, headers=_get_headers(with_api_key=True)) as response:
        response.raise_for_status()
        return await response.json()


def create_session() -> aiohttp.ClientSession:
    """Create a new aiohttp session with connection pooling."""
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=10)
    return aiohttp.ClientSession(timeout=timeout, connector=connector)
