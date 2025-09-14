# Third-party imports
from pydantic import BaseModel

# Local application imports
from app.models.base import Base


def update_model_fields(model_instance: Base, update_data: BaseModel, partial_update: bool = True) -> None:
    """
    Updates model fields based on the provided update_data.

    - If `partial_update=True` (PATCH), updates only non-null fields.
    - If `partial_update=False` (PUT), updates all fields, setting unspecified ones to None.
    """
    update_dict = update_data.model_dump()
    if partial_update:
        # PATCH: Update only provided (non-null) fields
        fields_to_update = {k: v for k, v in update_dict.items() if v is not None and hasattr(model_instance, k)}
    else:
        # PUT: Update all fields, even if they are set to None
        fields_to_update = {k: v for k, v in update_dict.items() if hasattr(model_instance, k)}

    for field, value in fields_to_update.items():
        setattr(model_instance, field, value)
