"""
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
import requests
import os
from dotenv import load_dotenv


load_dotenv()


BASE_URL = "https://knowunity-agent-olympics-2026-api.vercel.app"
API_KEY = os.getenv("API_KEY")
SET_TYPE = "mini_dev"


def get_students(set_type: str = SET_TYPE):
    url = f"{BASE_URL}/students"
    params = {
        "set_type": set_type
    }
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    return data


def get_students_topics(student_id: str):
    url = f"{BASE_URL}/students/{student_id}/topics"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    return data


def get_subjects():
    url = f"{BASE_URL}/subjects"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    return data


def get_topics(subject_id: str):
    url = f"{BASE_URL}/topics"
    params = {
        "subject_id": subject_id
    }
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data


def start_conversation(student_id: str, topic_id: str):
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
    data = response.json()
    return data


def interact(conversation_id: str, tutor_message: str):
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
    data = response.json()
    return data


def submit_mse_predictions(predictions_dict: dict, set_type: str = SET_TYPE):
    """
    predictions_dict: dict of {(student_id, topic_id): predicted_level}
    """
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
            for (student_id, topic_id), predicted_level in predictions_dict.items()
        ],
        "set_type": set_type,
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data


def evaluate_tutoring(set_type: str = SET_TYPE):
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
