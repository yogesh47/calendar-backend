from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CampusJob:
    job_id: str
    title: str
    company: str
    job_type: str
    application_end_date: date
    departments: tuple[str, ...]


CAMPUS_JOBS = (
    CampusJob(
        job_id="abf9d566-a7a3-4929-bb0e-fc645ff41550",
        title="Do Not Apply to this Job 4",
        company="47 billion",
        job_type="Full-Time",
        application_end_date=date(2031, 9, 26),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
    ),
    CampusJob(
        job_id="abf9d566-a7a3-4929-bb0e-fc635ff41550",
        title="Do Not Apply to this Job 2",
        company="47 billion",
        job_type="Full-Time",
        application_end_date=date(2031, 9, 26),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
    ),
    CampusJob(
        job_id="75d14200-55e9-41ff-af7c-f67412f11b56",
        title="Electrical Engineer",
        company="Quantum Dynamics Inc.",
        job_type="Internship",
        application_end_date=date(2027, 5, 19),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
    ),
)


def job_by_id(job_id: str) -> CampusJob | None:
    return next((job for job in CAMPUS_JOBS if job.job_id == job_id), None)


def jobs_for(department: str) -> list[CampusJob]:
    return [job for job in CAMPUS_JOBS if department in job.departments]
