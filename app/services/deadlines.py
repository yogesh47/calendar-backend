from datetime import date

from app.auth.users import TPO, HardcodedUser
from app.models.calendar_model import EventOut, LinkedJobIn
from app.services.jobs import CAMPUS_JOBS, CampusJob
from app.services.students import STUDENT_PROFILE


# A campus job the student may still apply to shows its closing date on the calendar.
def visible_jobs(viewer: HardcodedUser) -> list[CampusJob]:
    if viewer.role == TPO:
        return list(CAMPUS_JOBS)

    return [job for job in CAMPUS_JOBS if STUDENT_PROFILE["department"] in job.departments]


# The deadline reads like any other calendar item, so one list serves web and mobile.
def deadline_out(job: CampusJob) -> EventOut:
    moment = f"{job.application_end_date.isoformat()}T00:00:00+00:00"

    return EventOut(
        event_id=f"deadline-{job.job_id}",
        event_type="deadline",
        title=f"{job.company} {job.title} — Applications close",
        company=job.company,
        event_date=job.application_end_date,
        end_date=job.application_end_date,
        start_time=None,
        end_time=None,
        mode=None,
        venue=None,
        online_platform=None,
        description=None,
        note=None,
        status="published",
        cancel_reason=None,
        cancel_note=None,
        cancelled_at=None,
        created_by="system",
        created_by_name="Auto from job",
        created_at=moment,
        updated_at=moment,
        notified_count=0,
        audience=None,
        linked_job=LinkedJobIn(kind="campus", campus_job=f"{job.company} — {job.title}", url=None, title=job.title),
        remind_before=None,
        linked_type="job_deadline",
        linked_id=job.job_id,
        is_owner=False,
    )


def deadline_items(viewer: HardcodedUser) -> list[EventOut]:
    return [deadline_out(job) for job in visible_jobs(viewer)]


def closing_on_or_after(viewer: HardcodedUser, day: date) -> list[EventOut]:
    return [item for item in deadline_items(viewer) if item.event_date >= day]
