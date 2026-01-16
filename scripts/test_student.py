from fbdsm.student import Student
import fire


def test_student(message:str):

    student_id = "1c6afe74-c388-4eb1-b82e-8326d95e29a3"
    topic_id = "b09cd19f-e8f4-4587-96c7-11f2612f8040"

    student = Student(student_id,topic_id)

    result = student.answer_tutor(message)

    print(result)



if __name__ == "__main__":
    fire.Fire(test_student)



