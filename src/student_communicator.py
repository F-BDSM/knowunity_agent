"""Interactive communication with a student via the tutoring API."""

import argparse
from typing import Any, Dict

from api import get_students, get_students_topics, start_conversation, interact


def _extract_students(raw: Any) -> list:
    """Extract students list from API response (handles wrapped and direct formats)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        students = raw.get("students")
        if isinstance(students, list):
            return students
    raise ValueError("Unexpected students response shape; expected list or {'students': [...]}")


def _extract_topics(raw: Any) -> list:
    """Extract topics list from API response (handles wrapped and direct formats)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        topics = raw.get("topics")
        if isinstance(topics, list):
            return topics
    raise ValueError("Unexpected topics response shape; expected list or {'topics': [...]}")


def select_student(students: list) -> Dict[str, Any]:
    """Display students and let user select one."""
    print("\n=== Available Students ===")
    for i, student in enumerate(students, 1):
        name = student.get("name", "<unnamed>")
        student_id = student.get("id", "<no-id>")
        print(f"{i}. {name} ({student_id})")

    while True:
        try:
            choice = int(input("\nSelect student number: "))
            if 1 <= choice <= len(students):
                return students[choice - 1]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def select_topic(topics: list) -> Dict[str, Any]:
    """Display topics and let user select one."""
    print("\n=== Available Topics ===")
    for i, topic in enumerate(topics, 1):
        name = topic.get("name", "<unnamed>")
        topic_id = topic.get("id", "<no-id>")
        grade = topic.get("grade_level", "?")
        print(f"{i}. {name} (grade {grade}) ({topic_id})")

    while True:
        try:
            choice = int(input("\nSelect topic number: "))
            if 1 <= choice <= len(topics):
                return topics[choice - 1]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")


def chat_loop(conversation_id: str, student_name: str) -> None:
    """Run interactive chat with the student."""
    print(f"\n=== Chat with {student_name} ===")
    print("Type 'quit' to exit\n")

    while True:
        message = input("You: ").strip()
        if message.lower() in ("quit", "exit", "q"):
            print("Conversation ended.")
            break

        if not message:
            continue

        response = interact(conversation_id, message)
        student_response = response.get("student_response", "<no response>")
        print(f"Student: {student_response}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Directly communicate with a student.",
    )
    parser.add_argument(
        "--set-type",
        default="mini_dev",
        help="Student set type (default: mini_dev)",
    )
    args = parser.parse_args()

    # Fetch and select student
    students_response = get_students(set_type=args.set_type)
    students = _extract_students(students_response)
    if not students:
        print("No students found.")
        return

    student = select_student(students)
    student_id = student.get("id")
    student_name = student.get("name", "<unnamed>")

    print(f"\nSelected student: {student_name}")

    # Fetch and select topic
    topics_response = get_students_topics(student_id)
    topics = _extract_topics(topics_response)
    if not topics:
        print("No topics found for this student.")
        return

    topic = select_topic(topics)
    topic_id = topic.get("id")
    topic_name = topic.get("name", "<unnamed>")

    print(f"Selected topic: {topic_name}")

    # Start conversation
    print("\nStarting conversation...")
    conversation_response = start_conversation(student_id, topic_id)
    conversation_id = conversation_response.get("conversation_id")

    if not conversation_id:
        print("Failed to start conversation.")
        return

    # Interactive chat
    chat_loop(conversation_id, student_name)


if __name__ == "__main__":
    main()
