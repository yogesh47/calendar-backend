from app.db.models import columns
from app.db.session import Base


class CalendarEventAudience(Base):
    __tablename__ = "calendar_event_audience"

    audience_id = columns.primary_key()
    event_id = columns.event_id(unique=True)
    opportunity_type = columns.text(20, nullable=False)
    courses = columns.text_list()
    batches = columns.number_list()
    departments = columns.text_list()
