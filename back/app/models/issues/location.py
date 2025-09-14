# Third-party imports
from sqlalchemy import Column, Integer, String, UniqueConstraint

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin


class Location(Base, UUIDTimeStampMixin):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("state", "district", "local_body", "ward", name="unique_location"),)

    # Hierarchy
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    local_body = Column(String(100), nullable=True, index=True)  # Panchayath/Corporation
    local_body_type = Column(String(50), nullable=True)  # panchayath, corporation, municipality
    ward = Column(String(100), nullable=True)

    # Statistics (will be updated via triggers or scheduled jobs)
    total_issues = Column(Integer, default=0)
    resolved_issues = Column(Integer, default=0)
    pending_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
