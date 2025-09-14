# Standard library imports
from datetime import datetime
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, ConfigDict


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    state: str
    district: str
    local_body: str | None
    local_body_type: str | None
    ward: str | None
    total_issues: int
    resolved_issues: int
    pending_issues: int
    critical_issues: int
    created_at: datetime
    updated_at: datetime


class LocationStats(BaseModel):
    state: str
    district: str | None
    local_body: str | None
    total_issues: int
    resolved_issues: int
    pending_issues: int
    critical_issues: int
    resolution_rate: float
    top_categories: list[dict]


class StateInfo(BaseModel):
    name: str
    districts: list[str]


class DistrictInfo(BaseModel):
    state: str
    name: str
    local_bodies: list[str]
