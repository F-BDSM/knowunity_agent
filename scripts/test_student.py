import fire
from fbdsm.api import get_students,get_students_topics
from fbdsm.student import Student



def main():
    student_info = get_students()[0]
    print(student_info)

    grade_level = student_info.grade_level
    name = student_info.name

    topic_info = get_students_topics(student_info.id)[0]
    print(topic_info)

    student = Student(student_id=student_info.id,
    topic_id=topic_info.id)
    
    answer = student.get_response("Hello, how are you?")
    print(answer)


if __name__ == "__main__":
    fire.Fire()
