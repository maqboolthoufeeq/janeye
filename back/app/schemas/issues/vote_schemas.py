# Standard library imports
from datetime import datetime
from uuid import UUID

# Third-party imports
from pydantic import BaseModel, ConfigDict


class VoteCreate(BaseModel):
    issue_id: UUID


class VoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    voter_id: UUID
    issue_id: UUID
    vote_month: str
    created_at: datetime


class UserVoteStats(BaseModel):
    current_month: str
    votes_used: int
    votes_remaining: int
    max_votes: int = 20
