# Standard library imports
import secrets


def generate_otp() -> str:
    """Generate a 6-digit OTP code as a string using secure random."""
    return "".join(str(secrets.randbelow(10)) for _ in range(6))
