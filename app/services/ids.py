import uuid

from app.exceptions import InvalidInputError

BAD_ID = "That id is not valid"


# A malformed id must answer 400, never 500, so every id is parsed in one place.
def as_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError) as error:
        raise InvalidInputError(BAD_ID) from error
