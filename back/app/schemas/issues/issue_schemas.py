# Standard library imports
from datetime import datetime
from enum import Enum
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field


class IssueStatus(str, Enum):
    REPORTED = "reported"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    ROADS = "roads"
    WATER_SUPPLY = "water_supply"
    ELECTRICITY = "electricity"
    WASTE_MANAGEMENT = "waste_management"
    DRAINAGE = "drainage"
    STREET_LIGHTS = "street_lights"
    PUBLIC_SAFETY = "public_safety"
    BUILDING_SAFETY = "building_safety"
    POLLUTION = "pollution"
    TRANSPORTATION = "transportation"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    OTHER = "other"


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: IssueCategory
    severity: IssueSeverity = IssueSeverity.MEDIUM
    state: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    local_body: str | None = Field(None, max_length=100)
    ward: str | None = Field(None, max_length=100)
    area: str | None = Field(None, max_length=200)
    address: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    media_urls: list[str] = Field(default_factory=list)


class IssueUpdate(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=200)
    description: str | None = Field(None, min_length=10)
    category: IssueCategory | None = None
    severity: IssueSeverity | None = None
    status: IssueStatus | None = None
    response: str | None = None
    response_date: str | None = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    state: str
    district: str
    local_body: str | None
    ward: str | None
    area: str | None
    address: str | None
    latitude: str | None
    longitude: str | None
    media_urls: list[str]
    reporter_id: UUID
    reporter_name: str | None = None
    upvotes: int
    response: str | None
    response_date: str | None
    created_at: datetime
    updated_at: datetime


class IssueListResponse(BaseModel):
    issues: list[IssueResponse]
    total: int
    page: int
    per_page: int
