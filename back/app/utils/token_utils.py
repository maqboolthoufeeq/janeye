# Standard library imports
from base64 import urlsafe_b64encode
import hashlib

# Third-party imports
from cryptography.fernet import Fernet

# Local application imports
from app.settings import settings


def encrypt_token(token: str) -> str:
    """
    Encrypt a given token using the provided encryption key.

    :param token: The token to be encrypted.
    :return: Encrypted token as a base64-encoded string.
    """

    # Generate a proper Fernet key from the SECRET_KEY
    # Use SHA-256 to get a consistent 32-byte key
    hashed_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    # Encode the key to URL-safe base64 format
    key = urlsafe_b64encode(hashed_key)

    cipher = Fernet(key)
    encrypted_token = cipher.encrypt(token.encode("utf-8"))
    return encrypted_token.decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token using the provided encryption key.

    :param encrypted_token: The encrypted token to be decrypted.
    :return: The original token as a string.
    """

    # Generate a proper Fernet key from the SECRET_KEY (must match encrypt_token)
    hashed_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = urlsafe_b64encode(hashed_key)

    cipher = Fernet(key)
    decrypted_token = cipher.decrypt(encrypted_token.encode("utf-8"))
    return decrypted_token.decode("utf-8")
