# Third-party imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import sentry_sdk

# Local application imports
from app.schemas.common import BaseResponse


def register_exception_handlers(app: FastAPI) -> None:
    # Map specific HTTP status codes to custom error codes
    error_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
    }

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,  # noqa
        exc: HTTPException,
    ) -> JSONResponse:
        # Determine the error code based on the status code
        error_code = error_map.get(exc.status_code, "error")
        # Ensure the detail is a string; if not, convert it
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        response = BaseResponse.failure(code=error_code, message=detail)
        return JSONResponse(status_code=exc.status_code, content=response.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,  # noqa
        exc: RequestValidationError,
    ) -> JSONResponse:
        # Format validation errors into a more readable message
        error_details = []
        for error in exc.errors():
            message = error.get("msg", "")

            # Clean up common prefixes in error messages
            # Remove "body: Value error, " prefix
            body_prefix = "body: Value error, "
            val_error_prefix = "Value error, "
            if message.startswith(body_prefix):
                message = message[len(body_prefix) :]
            # Remove just "Value error, " prefix
            elif message.startswith(val_error_prefix):
                message = message[len(val_error_prefix) :]

            error_details.append(message)

        # Join all error messages or use a default if empty
        max_errors = 5
        shown = error_details[:max_errors]

        if len(error_details) > max_errors:
            shown.append("…and more errors")
        detail = "; ".join(shown) if shown else "Invalid request data"

        response = BaseResponse.failure(
            code="bad_request",
            message=detail,
        )
        return JSONResponse(status_code=400, content=response.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,  # noqa
        exc: Exception,
    ) -> JSONResponse:
        # Capture the exception in Sentry for monitoring
        sentry_sdk.capture_exception(exc)
        response = BaseResponse.failure(
            code="internal_server_error",
            message="An unexpected error occurred. Please try again later.",
        )
        return JSONResponse(status_code=500, content=response.model_dump())
