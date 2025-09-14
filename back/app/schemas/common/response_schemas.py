# Standard library imports
from typing import Any, Generic, TypeVar

# Third-party imports
from pydantic import BaseModel

# Define a union type for error details: string, list of strings, or a dict.
DetailsType = str | list[str] | dict[str, Any]
DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total_items: int

    class Config:
        exclude_none = True


class ErrorDetails(BaseModel):
    code: str
    message: str
    details: DetailsType | None = None

    class Config:
        exclude_none = True


class BaseResponse(BaseModel, Generic[DataT]):
    ok: bool
    data: DataT | None = None
    meta: PaginationMeta | None = None
    error: ErrorDetails | None = None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        # Get the default dump
        data = super().model_dump(**kwargs)

        # Remove data and meta fields if they are None
        if data.get("data") is None:
            data.pop("data", None)
        if data.get("meta") is None:
            data.pop("meta", None)

        return data

    @classmethod
    def success(cls, data: DataT, meta: PaginationMeta | None = None) -> "BaseResponse[DataT]":
        return cls(ok=True, data=data, meta=meta)

    @classmethod
    def failure(cls, code: str, message: str, details: DetailsType | None = None) -> "BaseResponse[None]":
        return BaseResponse[None](ok=False, error=ErrorDetails(code=code, message=message, details=details))
