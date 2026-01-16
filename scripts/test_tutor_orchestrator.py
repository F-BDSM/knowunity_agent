from fbdsm.orchestrator import TutoringOrchestrator
from fbdsm.api import get_students,get_students_topics

import fire

def main():
    student_info = get_students()[0]
    topic_info = get_students_topics(student_info.id)[0]
    orchestrator = TutoringOrchestrator(student_info.id)

    out = orchestrator.run_session(topic_info.id)
    print(out)


if __name__ == "__main__":
    fire.Fire()
