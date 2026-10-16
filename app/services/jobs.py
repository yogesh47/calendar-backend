from dataclasses import dataclass, field
from datetime import date

from app.auth.users import HARDCODED_USERS, STUDENT
from app.services.students import STUDENT_PROFILE


# The shape mirrors the 7Seers jobs API, so plugging in the real service only
# changes this file and the rest of the calendar stays as it is.
@dataclass(frozen=True)
class CampusJob:
    job_id: str
    title: str
    company: str
    job_type: str
    application_end_date: date
    departments: tuple[str, ...]
    batch: int | None = None
    status: str = "active"


@dataclass(frozen=True)
class JobApplication:
    application_id: str
    job_id: str
    student_id: str
    application_status: str = "Applied"
    extras: dict = field(default_factory=dict)


CAMPUS_JOBS = (
    CampusJob(
        job_id="abf9d566-a7a3-4929-bb0e-fc645ff41550",
        title="Do Not Apply to this Job 4",
        company="47 billion",
        job_type="Full-Time",
        application_end_date=date(2031, 9, 26),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
        batch=2027,
    ),
    CampusJob(
        job_id="abf9d566-a7a3-4929-bb0e-fc635ff41550",
        title="Do Not Apply to this Job 2",
        company="47 billion",
        job_type="Full-Time",
        application_end_date=date(2031, 9, 26),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
        batch=2027,
    ),
    CampusJob(
        job_id="75d14200-55e9-41ff-af7c-f67412f11b56",
        title="Electrical Engineer",
        company="Quantum Dynamics Inc.",
        job_type="Internship",
        application_end_date=date(2027, 5, 19),
        departments=("Civil Engineering", "Computer Science", "Electrical Engineering", "Management", "Pharmacy"),
        batch=2027,
    ),
)

# Demo applications — in the real app these come from the Jobs service.
APPLICATIONS: list[JobApplication] = []


# Adapter that turns a 7Seers job-detail payload straight into a CampusJob.
# Once the real service is wired, only this function is used; the logic below is unchanged.
def from_payload(payload: dict) -> CampusJob:
    detail = payload.get("job_description", payload)
    company = payload.get("company_info", {}).get("name") or detail.get("company_name", "")
    closes = str(detail.get("application_end_date", ""))[:10]

    return CampusJob(
        job_id=detail["job_id"],
        title=detail.get("job_title", ""),
        company=company,
        job_type=detail.get("job_type", ""),
        application_end_date=date.fromisoformat(closes),
        departments=tuple(payload.get("department", []) or []),
        batch=detail.get("batch"),
        status=detail.get("status", "active"),
    )


# The payload carries application_status; empty or missing means they have not applied.
def applied_from_payload(payload: dict) -> bool:
    return bool(payload.get("application_status"))


def job_by_id(job_id: str) -> CampusJob | None:
    return next((job for job in CAMPUS_JOBS if job.job_id == job_id), None)


def jobs_for(department: str) -> list[CampusJob]:
    return [job for job in CAMPUS_JOBS if department in job.departments]


def is_open(job: CampusJob) -> bool:
    return job.status == "active"


# The real Jobs API sends departments in lower case, so the match ignores case.
# There the answer arrives as `job_description.is_eligible`; here it is worked out locally.
def is_eligible(job: CampusJob, course: str, batch: int, department: str) -> bool:
    del course
    wanted = {entry.strip().lower() for entry in job.departments}

    return department.strip().lower() in wanted and (job.batch is None or job.batch == batch)


def eligible_student_ids(job: CampusJob) -> list[str]:
    if not is_eligible(job, STUDENT_PROFILE["course"], STUDENT_PROFILE["batch"], STUDENT_PROFILE["department"]):
        return []

    return [user.user_id for user in HARDCODED_USERS if user.role == STUDENT]


def has_applied(job_id: str, student_id: str) -> bool:
    return any(entry.job_id == job_id and entry.student_id == student_id for entry in APPLICATIONS)


def applications_for(job_id: str) -> list[JobApplication]:
    return [entry for entry in APPLICATIONS if entry.job_id == job_id]


# These are the three counts a TPO sees on a deadline's detail (FR-CAL-08).
def deadline_counts(job: CampusJob) -> dict[str, int]:
    eligible = eligible_student_ids(job)
    applied = [entry for entry in applications_for(job.job_id) if entry.student_id in eligible]

    return {
        "eligible": len(eligible),
        "applied": len(applied),
        "not_applied": len(eligible) - len(applied),
    }


def apply_to(job_id: str, student_id: str) -> JobApplication:
    import uuid

    existing = next(
        (entry for entry in APPLICATIONS if entry.job_id == job_id and entry.student_id == student_id), None
    )
    if existing:
        return existing

    entry = JobApplication(application_id=str(uuid.uuid4()), job_id=job_id, student_id=student_id)
    APPLICATIONS.append(entry)

    return entry


def withdraw(job_id: str, student_id: str) -> None:
    APPLICATIONS[:] = [
        entry for entry in APPLICATIONS if not (entry.job_id == job_id and entry.student_id == student_id)
    ]
