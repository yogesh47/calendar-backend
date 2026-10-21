"""
The errors this service raises on purpose.

Named classes, not bare built-ins: a `ValueError` escaping from a genuine bug
used to be answered with 400, because the only way to recognise "bad input" was
to catch `ValueError` itself. These say what they mean, so anything unnamed is
a 500 again — which is what an unexpected failure should be.

The names match 7Seers-SkillsBridge's `app/utils/errors.py` wherever the two
services mean the same thing, so this layer ports across unchanged.
"""


class CalendarError(Exception):
    """Base for everything raised deliberately."""


class NotExistError(CalendarError):
    """The thing asked for is not there. Answers 404."""


class AlreadyExistError(CalendarError):
    """It is already there, and a second one is not allowed. Answers 409."""


class AuthenticationError(CalendarError):
    """Not signed in, or the session is over. Answers 401."""


class PermissionDeniedError(CalendarError):
    """Signed in, but not allowed to do this. Answers 403."""


class InvalidInputError(CalendarError):
    """The request itself does not make sense. Answers 400."""
