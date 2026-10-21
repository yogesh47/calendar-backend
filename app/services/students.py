from sqlalchemy.orm import Session

from app.auth.users import students_of

STUDENT_PROFILE = {
    "course": "BTech",
    "batch": 2027,
    "department": "Computer Science",
}


def group_size(course: str, batch: int, department: str) -> int:
    seed = sum(ord(letter) for letter in f"{course}{batch}{department}")

    return 12 + (seed % 48)


def count_audience(courses: list[str], batches: list[int], departments: list[str]) -> int:
    return sum(
        group_size(course, batch, department)
        for course in courses
        for batch in batches
        for department in departments
    )


def matching_student_ids(
    db: Session, org_id: str, courses: list[str], batches: list[int], departments: list[str]
) -> list[str]:
    if (
        STUDENT_PROFILE["course"] in courses
        and STUDENT_PROFILE["batch"] in batches
        and STUDENT_PROFILE["department"] in departments
    ):
        return [user.user_id for user in students_of(db, org_id)]

    return []
