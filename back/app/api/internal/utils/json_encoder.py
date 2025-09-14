# Standard library imports
from typing import Any

# Third-party imports
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class CustomJSONResponse(JSONResponse):
    """
    Custom JSON response that removes top-level null 'meta' and 'error' keys
    from BaseResponse objects while preserving the rest of the response.
    """

    def render(self, content: Any) -> bytes:
        # Convert to JSON-serializable dict
        json_content = jsonable_encoder(content)

        # If this is a BaseResponse-like structure, clean up null values
        if isinstance(json_content, dict) and "ok" in json_content:
            # Remove null meta and error fields at the top level
            if json_content.get("meta") is None:
                json_content.pop("meta", None)
            if json_content.get("error") is None:
                json_content.pop("error", None)

        return super().render(json_content)
