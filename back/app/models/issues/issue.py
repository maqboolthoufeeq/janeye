# Standard library imports
import enum

# Third-party imports
from sqlalchemy import JSON, Column, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin


class IssueStatus(str, enum.Enum):
    REPORTED = "reported"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class IssueSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, enum.Enum):
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


class Issue(Base, UUIDTimeStampMixin):
    __tablename__ = "issues"

    # Issue details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(IssueCategory), nullable=False)
    severity = Column(SQLEnum(IssueSeverity), default=IssueSeverity.MEDIUM)
    status = Column(SQLEnum(IssueStatus), default=IssueStatus.REPORTED)

    # Location information
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    local_body = Column(String(100), nullable=True, index=True)  # Panchayath/Corporation
    ward = Column(String(100), nullable=True)
    area = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)

    # Media
    media_urls = Column(JSON, default=list)  # Array of photo/video URLs

    # User and voting
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    upvotes = Column(Integer, default=0, index=True)

    # Government response
    response = Column(Text, nullable=True)
    response_date = Column(String(50), nullable=True)

    # Relationships - commented to avoid circular dependencies
    # reporter = relationship("User", back_populates="reported_issues")
    votes = relationship("Vote", back_populates="issue", cascade="all, delete-orphan")
