# Standard library imports
from uuid import UUID


def is_valid_uuid(value: str) -> bool:
    try:
        uuid_obj = UUID(value, version=4)
    except ValueError:
        return False
    return str(uuid_obj) == value
