import uuid

COMPANY_NAMES = (
    "47 billion",
    "Quantum Dynamics Inc.",
    "Zecoho Technologies Private Limited",
    "Tripocio Carnival Pvt Ltd",
    "Hirednex",
)

COMPANY_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-0000000000c0")


def company_id_of(name: str | None) -> uuid.UUID | None:
    if not name:
        return None

    return uuid.uuid5(COMPANY_NAMESPACE, name)


def company_name_of(company_id) -> str | None:
    if not company_id:
        return None

    return next((name for name in COMPANY_NAMES if company_id_of(name) == company_id), None)
