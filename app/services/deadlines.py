from app.auth.users import TPO, HardcodedUser
from app.models.calendar_model import EventOut, LinkedJobIn
from app.services.jobs import (
    CAMPUS_JOBS,
    CampusJob,
    deadline_counts,
    has_applied,
    is_eligible,
    is_open,
)
from app.services.students import STUDENT_PROFILE


# BRD FR-CAL-08: a student sees a deadline only while the job is active, they are eligible
# and they have not applied yet. A TPO sees every active job's deadline.
def visible_jobs(viewer: HardcodedUser) -> list[CampusJob]:
    live = [job for job in CAMPUS_JOBS if is_open(job)]

    if viewer.role == TPO:
        return live

    return [
        job
        for job in live
        if is_eligible(job, STUDENT_PROFILE["course"], STUDENT_PROFILE["batch"], STUDENT_PROFILE["department"])
        and not has_applied(job.job_id, viewer.user_id)
    ]


# The deadline reads like any other calendar item, so one list serves web and mobile.
def deadline_out(job: CampusJob, viewer: HardcodedUser) -> EventOut:
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
        deadline_counts=deadline_counts(job) if viewer.role == TPO else None,
    )


def deadline_items(viewer: HardcodedUser) -> list[EventOut]:
    return [deadline_out(job, viewer) for job in visible_jobs(viewer)]
