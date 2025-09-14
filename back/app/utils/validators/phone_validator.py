# Third-party imports
import phonenumbers


def validate_phone_number(value: str | None) -> str | None:
    """
    Validate (and optionally normalize) a phone number using the `phonenumbers` library.
    Specifically handles Indian phone numbers.
    """
    if value is None:
        return value  # Allow None values (optional fields)

    try:
        # Clean the input
        cleaned = str(value).strip()

        # If it's just 10 digits, assume it's Indian
        if cleaned.isdigit() and len(cleaned) == 10:
            cleaned = f"+91{cleaned}"
        # If it starts with 91 and is 12 digits
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = f"+{cleaned}"
        # If it doesn't start with +, add it
        elif not cleaned.startswith("+") and cleaned.isdigit():
            cleaned = f"+91{cleaned}"

        # Parse the phone number for India
        parsed = phonenumbers.parse(cleaned, "IN")
        if not phonenumbers.is_valid_number(parsed):
            return None

        # Normalize to E.164 format for consistent storage (e.g., +919876543210)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None
