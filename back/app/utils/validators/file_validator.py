def normalize_file_name(value: str) -> str | None:
    """
    validate file url
    """
    if value is None:
        return None

    return value.replace(" ", "_").lower()
