"""
List of Functions:
- get_students()
- get_students_topics(student_id)
- get_subjects()
- get_topics(subject_id)
- start_conversation(student_id, topic_id)
- interact(conversation_id, tutor_message)
- submit_mse_predictions(student_id, topic_id, prediction_level)
- evaluate_tutoring()
"""
import requests
import os
from typing import List,Optional

from .config import settings
from .models import StudentInfo,TopicInfo,InteractionStartResult,InteractionResult,Topic


BASE_URL = settings.KNOWUNITY_API_URL
API_KEY = settings.KNOWUNITY_API_KEY


def get_students(set_type: str = "mini_dev")->List[StudentInfo]:
    url = f"{BASE_URL}/students"
    params = {
        "set_type": set_type
    }
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()['students']
    return [StudentInfo(**student) for student in data]


def get_students_topics(student_id: str)->List[TopicInfo]:
    url = f"{BASE_URL}/students/{student_id}/topics"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    data = response.json()['topics']
    return [TopicInfo(**topic) for topic in data]


def get_subjects():
    url = f"{BASE_URL}/subjects"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers, timeout=10)
    data = response.json()

    return data


def get_topics(subject_id: str)->List[TopicInfo]:
    url = f"{BASE_URL}/topics"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers).json()
    return [TopicInfo(**topic) for topic in response]


def start_conversation(student_id: str, topic_id: str)->InteractionStartResult:
    url = f"{BASE_URL}/interact/start"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": API_KEY,
    }
    payload = {
        "student_id": student_id,
        "topic_id": topic_id,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return InteractionStartResult(**response.json())


def interact(conversation_id: str, tutor_message: str)->InteractionResult:
    url = f"{BASE_URL}/interact"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": API_KEY,
    }
    payload = {
        "conversation_id": conversation_id,
        "tutor_message": tutor_message,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return InteractionResult(tutor_message=tutor_message,**response.json())


def submit_mse_predictions(student_id: str, topic_id: str, predicted_level: int, set_type: str = "mini_dev"):
    url = f"{BASE_URL}/evaluate/mse"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": API_KEY,
    }
    payload = {
        "predictions": [
            {
                "student_id": student_id,
                "topic_id": topic_id,
                "predicted_level": predicted_level,
            }
        ],
        "set_type": set_type,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def evaluate_tutoring(set_type: str = "mini_dev"):
    url = f"{BASE_URL}/evaluate/tutoring"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": API_KEY,
    }
    payload = {
        "set_type": set_type
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data


# for local testing
# if __name__ == "__main__":
#     student_id = "1c6afe74-c388-4eb1-b82e-8326d95e29a3"
#     topic_id = "b09cd19f-e8f4-4587-96c7-11f2612f8040"
#     response = start_conversation(student_id, topic_id)
#     conversation_id = response["conversation_id"]
#     response = interact(conversation_id, "Hello, how are you?")
#     print(response["student_response"])
