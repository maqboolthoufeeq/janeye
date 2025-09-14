# Third-party imports
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Local application imports
from app.models.base import Base
from app.models.mixins.uuid_timestamp import UUIDTimeStampMixin


class Vote(Base, UUIDTimeStampMixin):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("voter_id", "issue_id", name="unique_voter_issue"),)

    # Vote information
    voter_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    vote_month = Column(String(7), nullable=False, index=True)  # Format: YYYY-MM

    # Relationships - voter commented to avoid circular dependencies
    # voter = relationship("User", back_populates="votes")
    issue = relationship("Issue", back_populates="votes")
