# Third-party imports
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.core.db import get_async_session
from app.models.issues.issue import Issue, IssueStatus
from app.schemas.issues.location_schemas import LocationStats, StateInfo

router = APIRouter(prefix="/locations", tags=["Locations"])


# Indian states and their districts (sample data - expand as needed)
INDIA_LOCATIONS = {
    "Kerala": [
        "Thiruvananthapuram",
        "Kollam",
        "Pathanamthitta",
        "Alappuzha",
        "Kottayam",
        "Idukki",
        "Ernakulam",
        "Thrissur",
        "Palakkad",
        "Malappuram",
        "Kozhikode",
        "Wayanad",
        "Kannur",
        "Kasaragod",
    ],
    "Tamil Nadu": [
        "Chennai",
        "Coimbatore",
        "Madurai",
        "Tiruchirappalli",
        "Salem",
        "Tirunelveli",
        "Tiruppur",
        "Vellore",
        "Erode",
        "Thoothukkudi",
    ],
    "Maharashtra": [
        "Mumbai",
        "Pune",
        "Nagpur",
        "Nashik",
        "Thane",
        "Aurangabad",
        "Solapur",
        "Amravati",
        "Kolhapur",
        "Sangli",
    ],
    "Karnataka": [
        "Bengaluru",
        "Mysuru",
        "Hubballi-Dharwad",
        "Mangaluru",
        "Belagavi",
        "Kalaburagi",
        "Davanagere",
        "Ballari",
        "Vijayapura",
        "Shivamogga",
    ],
    "Andhra Pradesh": [
        "Visakhapatnam",
        "Vijayawada",
        "Guntur",
        "Nellore",
        "Kurnool",
        "Tirupati",
        "Kakinada",
        "Rajahmundry",
        "Kadapa",
        "Anantapur",
    ],
    "Telangana": [
        "Hyderabad",
        "Warangal",
        "Nizamabad",
        "Khammam",
        "Karimnagar",
        "Mahbubnagar",
        "Rangareddy",
        "Medak",
        "Nalgonda",
        "Adilabad",
    ],
    "Gujarat": [
        "Ahmedabad",
        "Surat",
        "Vadodara",
        "Rajkot",
        "Bhavnagar",
        "Jamnagar",
        "Gandhinagar",
        "Junagadh",
        "Anand",
        "Nadiad",
    ],
    "Rajasthan": [
        "Jaipur",
        "Jodhpur",
        "Udaipur",
        "Kota",
        "Ajmer",
        "Bikaner",
        "Alwar",
        "Bharatpur",
        "Sikar",
        "Pali",
    ],
    "Uttar Pradesh": [
        "Lucknow",
        "Kanpur",
        "Ghaziabad",
        "Agra",
        "Varanasi",
        "Meerut",
        "Allahabad",
        "Bareilly",
        "Aligarh",
        "Moradabad",
    ],
    "West Bengal": [
        "Kolkata",
        "Howrah",
        "Durgapur",
        "Asansol",
        "Siliguri",
        "Bardhaman",
        "Malda",
        "Baharampur",
        "Habra",
        "Kharagpur",
    ],
}


@router.get("/states", response_model=list[StateInfo])
async def get_states():
    """Get list of all states with their districts"""
    return [StateInfo(name=state, districts=districts) for state, districts in INDIA_LOCATIONS.items()]


@router.get("/districts")
async def get_districts(state: str):
    """Get districts for a specific state"""
    districts = INDIA_LOCATIONS.get(state, [])
    return {"state": state, "districts": districts}


@router.get("/local-bodies")
async def get_local_bodies(state: str, district: str, db: AsyncSession = Depends(get_async_session)):
    """Get local bodies (panchayaths/corporations) for a district"""
    # Get unique local bodies from issues
    result = await db.execute(
        select(distinct(Issue.local_body)).where(
            and_(
                Issue.state == state,
                Issue.district == district,
                Issue.local_body.isnot(None),
            )
        )
    )
    local_bodies = [row[0] for row in result.all() if row[0]]

    return {"state": state, "district": district, "local_bodies": local_bodies}


@router.get("/stats", response_model=LocationStats)
async def get_location_stats(
    state: str,
    district: str | None = None,
    local_body: str | None = None,
    db: AsyncSession = Depends(get_async_session),
):
    """Get statistics for a specific location"""
    # Build filter conditions
    filters = [Issue.state == state]
    if district:
        filters.append(Issue.district == district)
    if local_body:
        filters.append(Issue.local_body == local_body)

    # Get issue counts
    total_result = await db.execute(select(func.count(Issue.id)).where(and_(*filters)))
    total_issues = total_result.scalar() or 0

    resolved_result = await db.execute(
        select(func.count(Issue.id)).where(and_(*filters, Issue.status == IssueStatus.RESOLVED))
    )
    resolved_issues = resolved_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(Issue.id)).where(
            and_(
                *filters,
                Issue.status.in_(
                    [
                        IssueStatus.REPORTED,
                        IssueStatus.ACKNOWLEDGED,
                        IssueStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
    )
    pending_issues = pending_result.scalar() or 0

    critical_result = await db.execute(select(func.count(Issue.id)).where(and_(*filters, Issue.severity == "critical")))
    critical_issues = critical_result.scalar() or 0

    # Get top categories
    category_result = await db.execute(
        select(Issue.category, func.count(Issue.id).label("count"))
        .where(and_(*filters))
        .group_by(Issue.category)
        .order_by(func.count(Issue.id).desc())
        .limit(5)
    )
    top_categories = [{"category": row[0], "count": row[1]} for row in category_result.all()]

    resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0

    return LocationStats(
        state=state,
        district=district,
        local_body=local_body,
        total_issues=total_issues,
        resolved_issues=resolved_issues,
        pending_issues=pending_issues,
        critical_issues=critical_issues,
        resolution_rate=round(resolution_rate, 2),
        top_categories=top_categories,
    )


@router.get("/trending-locations")
async def get_trending_locations(limit: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_async_session)):
    """Get locations with most issues reported"""
    result = await db.execute(
        select(
            Issue.state,
            Issue.district,
            func.count(Issue.id).label("issue_count"),
            func.sum(Issue.upvotes).label("total_upvotes"),
        )
        .group_by(Issue.state, Issue.district)
        .order_by(func.count(Issue.id).desc())
        .limit(limit)
    )

    locations = [
        {
            "state": row[0],
            "district": row[1],
            "issue_count": row[2],
            "total_upvotes": row[3] or 0,
        }
        for row in result.all()
    ]

    return locations
