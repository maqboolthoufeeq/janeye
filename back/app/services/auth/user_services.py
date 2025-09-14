# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from app.db_selectors.auth import get_user_by_email, user_exists_by_email
from app.models.auth.user import User
from app.utils.password_utils import get_password_hash, verify_password


async def does_user_exist(db: AsyncSession, email: str) -> bool:
    ok = await user_exists_by_email(db, email)
    if not ok:
        return False
    return bool(ok)


async def update_user_password(db: AsyncSession, user: User, new_password: str) -> bool:
    """
    Update a user's password in the database.

    Args:
        db: The current database session.
        user: The user whose password is being changed.
        new_password: The new password to set for the user.

    Returns:
        True if the password is successfully updated, otherwise False.
    """

    # Hash the new password
    hashed_new_password = get_password_hash(new_password)

    # Update the user's password field
    user.hashed_password = hashed_new_password

    # Commit the changes to the database
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return True


async def update_user_password_by_email(db: AsyncSession, email: str, new_password: str) -> bool:
    """
    Update a user's password in the database.

    Args:
        db: The current database session.
        email: The email of the user whose password is being changed.
        new_password: The new password to set for the user.

    Returns:
        True if the password is successfully updated, otherwise False.
    """
    # Get the user by email
    user = await get_user_by_email(db, email)
    if not user:
        return False  # User not found

    # Hash the new password
    hashed_new_password = get_password_hash(new_password)

    # Update the user's password field
    user.hashed_password = hashed_new_password

    # Commit the changes to the database
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return True


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Authenticate a user by retrieving the user from the database by email and verifying the password.

    Returns the user if authentication is successful; otherwise, returns None.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
