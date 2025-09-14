# Standard library imports
from datetime import datetime
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.db import get_async_session
from app.dependancies.common import get_current_user
from app.models.auth.user import User
from app.models.issues.issue import Issue
from app.models.issues.vote import Vote
from app.schemas.issues.vote_schemas import UserVoteStats, VoteCreate, VoteResponse

router = APIRouter(prefix="/votes", tags=["Votes"])


@router.post("/", response_model=VoteResponse)
async def create_vote(
    vote_data: VoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Vote for an issue (max 20 votes per month)"""
    current_month = datetime.now().strftime("%Y-%m")

    # Check if issue exists
    issue_result = await db.execute(select(Issue).where(Issue.id == vote_data.issue_id))
    issue = issue_result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check if user already voted for this issue
    existing_vote = await db.execute(
        select(Vote).where(and_(Vote.voter_id == current_user.id, Vote.issue_id == vote_data.issue_id))
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already voted for this issue")

    # Check monthly vote limit
    monthly_votes = await db.execute(
        select(func.count(Vote.id)).where(and_(Vote.voter_id == current_user.id, Vote.vote_month == current_month))
    )
    vote_count = monthly_votes.scalar()

    if vote_count >= 20:
        raise HTTPException(
            status_code=400,
            detail="You have reached your monthly voting limit of 20 votes",
        )

    # Create vote
    new_vote = Vote(voter_id=current_user.id, issue_id=vote_data.issue_id, vote_month=current_month)

    # Update issue upvotes
    issue.upvotes += 1

    # Update user vote count
    if current_user.current_vote_month != current_month:
        current_user.current_vote_month = current_month
        current_user.monthly_vote_count = 1
    else:
        current_user.monthly_vote_count += 1

    db.add(new_vote)
    await db.commit()
    await db.refresh(new_vote)

    return VoteResponse.model_validate(new_vote)


@router.delete("/{issue_id}")
async def remove_vote(
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove vote from an issue"""
    # Find the vote
    vote_result = await db.execute(
        select(Vote).where(and_(Vote.voter_id == current_user.id, Vote.issue_id == issue_id))
    )
    vote = vote_result.scalar_one_or_none()

    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    # Get issue and update upvotes
    issue_result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = issue_result.scalar_one_or_none()

    if issue:
        issue.upvotes = max(0, issue.upvotes - 1)

    # Update user vote count
    current_month = datetime.now().strftime("%Y-%m")
    if vote.vote_month == current_month:
        current_user.monthly_vote_count = max(0, current_user.monthly_vote_count - 1)

    await db.delete(vote)
    await db.commit()

    return {"message": "Vote removed successfully"}


@router.get("/stats", response_model=UserVoteStats)
async def get_vote_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get user's voting statistics for current month"""
    current_month = datetime.now().strftime("%Y-%m")

    # Get vote count for current month
    monthly_votes = await db.execute(
        select(func.count(Vote.id)).where(and_(Vote.voter_id == current_user.id, Vote.vote_month == current_month))
    )
    vote_count = monthly_votes.scalar()

    return UserVoteStats(
        current_month=current_month,
        votes_used=vote_count,
        votes_remaining=20 - vote_count,
        max_votes=20,
    )


@router.get("/user/{user_id}")
async def get_user_votes(
    user_id: UUID,
    month: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all votes by a user (admin only or self)"""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You can only view your own votes")

    query = select(Vote).where(Vote.voter_id == user_id)

    if month:
        query = query.where(Vote.vote_month == month)

    result = await db.execute(query.order_by(Vote.created_at.desc()))
    votes = result.scalars().all()

    return [VoteResponse.model_validate(vote) for vote in votes]
