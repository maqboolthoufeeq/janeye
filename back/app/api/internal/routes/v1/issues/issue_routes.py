# Standard library imports
from datetime import datetime
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.db import get_async_session
from app.dependancies.common import get_current_user
from app.models.auth.user import User
from app.models.issues.issue import Issue, IssueCategory, IssueSeverity, IssueStatus
from app.schemas.issues.issue_schemas import IssueCreate, IssueListResponse, IssueResponse, IssueUpdate

# from app.services.storage.s3_service import S3Service  # TODO: Enable when S3 is configured

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.post("/", response_model=IssueResponse)
async def create_issue(
    issue_data: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new issue report"""
    # Validate media_urls is not empty
    if not issue_data.media_urls:
        raise HTTPException(status_code=400, detail="At least one photo or video is required")

    # Create issue
    new_issue = Issue(**issue_data.model_dump(), reporter_id=current_user.id)

    db.add(new_issue)
    await db.commit()
    await db.refresh(new_issue)

    # Add reporter name
    response = IssueResponse.model_validate(new_issue)
    response.reporter_name = f"{current_user.first_name} {current_user.last_name}".strip()

    return response


@router.post("/upload-media", response_model=dict)
async def upload_media(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload photo or video for issue"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "video/mp4", "video/mpeg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and MP4 videos are allowed",
        )

    # Validate file size (max 50MB)
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")

    # TODO: Implement S3 upload when configured
    # For now, return a mock URL
    mock_url = (
        f"http://localhost:9000/janeye-public/issues/{current_user.id}/{datetime.now().isoformat()}_{file.filename}"
    )
    return {"url": mock_url}


@router.get("/", response_model=IssueListResponse)
async def list_issues(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    state: str | None = None,
    district: str | None = None,
    local_body: str | None = None,
    category: IssueCategory | None = None,
    severity: IssueSeverity | None = None,
    status: IssueStatus | None = None,
    sort_by: str = Query("created_at", regex="^(created_at|upvotes)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_async_session),
):
    """List issues with filters"""
    # Build query
    query = select(Issue)

    # Apply filters
    filters = []
    if state:
        filters.append(Issue.state == state)
    if district:
        filters.append(Issue.district == district)
    if local_body:
        filters.append(Issue.local_body == local_body)
    if category:
        filters.append(Issue.category == category)
    if severity:
        filters.append(Issue.severity == severity)
    if status:
        filters.append(Issue.status == status)

    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    if sort_by == "upvotes":
        order_by = Issue.upvotes.desc() if order == "desc" else Issue.upvotes.asc()
    else:
        order_by = Issue.created_at.desc() if order == "desc" else Issue.created_at.asc()

    query = query.order_by(order_by)

    # Get total count
    count_query = select(func.count()).select_from(Issue)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    issues = result.scalars().all()

    # Get reporter names
    user_ids = [issue.reporter_id for issue in issues]
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = {user.id: user for user in users_result.scalars().all()}
    else:
        users = {}

    # Build response
    issue_responses = []
    for issue in issues:
        response = IssueResponse.model_validate(issue)
        user = users.get(issue.reporter_id)
        if user:
            response.reporter_name = f"{user.first_name} {user.last_name}".strip()
        issue_responses.append(response)

    return IssueListResponse(issues=issue_responses, total=total, page=page, per_page=per_page)


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """Get issue details"""
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Get reporter info
    user_result = await db.execute(select(User).where(User.id == issue.reporter_id))
    user = user_result.scalar_one_or_none()

    response = IssueResponse.model_validate(issue)
    if user:
        response.reporter_name = f"{user.first_name} {user.last_name}".strip()

    return response


@router.patch("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: UUID,
    update_data: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update issue (only reporter or admin can update)"""
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check permissions
    if issue.reporter_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You don't have permission to update this issue")

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)

    await db.commit()
    await db.refresh(issue)

    response = IssueResponse.model_validate(issue)
    response.reporter_name = f"{current_user.first_name} {current_user.last_name}".strip()

    return response


@router.delete("/{issue_id}")
async def delete_issue(
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete issue (only reporter or admin can delete)"""
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check permissions
    if issue.reporter_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this issue")

    await db.delete(issue)
    await db.commit()

    return {"message": "Issue deleted successfully"}
