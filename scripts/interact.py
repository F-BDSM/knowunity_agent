# from project root run: uv run -m scripts.interact
from src.api import get_students, get_students_topics, start_conversation, interact, submit_mse_predictions, evaluate_tutoring


def generate_all_student_topic_pairs() -> dict:
    student_topic_pairs = dict()

    student_dict = create_student_dict()
    for student_name, student_id in student_dict.items():
        topics = get_students_topics(student_id)['topics']
        for topic in topics:
            topic_id = topic['id']
            topic_name = topic['name'].split()
            topic_name_camel_case = topic_name[0].lower() + ''.join(w.capitalize() for w in topic_name[1:])
            student_topic_key = student_name + "-" + topic_name_camel_case
            student_topic_pairs[student_topic_key] = (student_id, topic_id)

    return student_topic_pairs


def create_student_dict() -> dict:
    student_dict = dict()
    students = get_students()['students']
    for student in students:
        id = student['id']
        name = student['name'].split()[0]
        student_dict[name.split()[0]] = id
    return student_dict

if __name__ == "__main__":
    predictions_dict = {}
    for i in range(3):
        print("===== CHAT WITH STUDENTS =====")
        student_topic_pairs = generate_all_student_topic_pairs()
        print("Choose one of the following pairs:")
        for i, pair in enumerate(student_topic_pairs):
            print(f"{i+1}. {pair}")
        pair_num = int(input("\033[32mEnter the pair (1-3):\033[0m "))
        if pair_num == 1:
            pair = "Alex-linearFunctions"
        elif pair_num == 2:
            pair = "Sam-quadraticEquations"
        elif pair_num == 3:
            pair = "Maya-thermodynamicsBasics"
        else:
            print("Unknown pair")
            exit
        id = student_topic_pairs[pair]
        student_id, topic_id = id[0], id[1]
        conversation_id = start_conversation(student_id, topic_id)['conversation_id']

        print("\n===== CONVERSATION STARTS ======")
        for i in range(10):
            tutor_message = input(f"Question {i+1}: ")
            if tutor_message == "done":
                break
            student_response = interact(conversation_id, tutor_message)['student_response']
            print(f"{student_response}\n")
        print("===== CONVERSATION ENDS ======")

        print("\nEVALUATION:")
        prediction_level = int(input("Submit your prediction level: "))
        predictions_dict[(student_id, topic_id)] = prediction_level

    mse_result = submit_mse_predictions(predictions_dict)['mse_score']
    tutoring_quality = evaluate_tutoring()['score']
    print(f"MSE Result: {mse_result}")
    print(f"Tutoring Evaluation Result: {tutoring_quality}")
