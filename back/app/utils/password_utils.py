# Third-party imports
import bcrypt


def get_password_hash(password: str) -> str:
    """
    Generate a hashed password.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its hashed version.
    """
    password_byte_enc = plain_password.encode("utf-8")
    # Convert hashed_password to bytes if it's a string
    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password_bytes)
