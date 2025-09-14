# Standard library imports
from datetime import datetime

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field


class DeviceInfo(BaseModel):
    device_name: str | None = None
    device_type: str | None = None
    browser: str | None = None
    os_name: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "device_name": "iPhone 12",
                "device_type": "mobile",
                "browser": "Safari",
                "os_name": "iOS 14.2",
            }
        },
    )


class LocationInfo(BaseModel):
    country: str | None = None
    city: str | None = None
    location_display: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "city": "Milan",
                "country": "Italy",
                "location_display": "Milan, Italy",
            }
        },
    )


class SessionResponse(BaseModel):
    """
    Response schema for session information.
    """

    id: str
    device_info: DeviceInfo | None = None
    ip_address: str | None = None
    location_info: LocationInfo | None = None
    last_login: datetime
    is_current: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "sess_123abc456def",
                "device_info": {
                    "device_name": "iPhone 12",
                    "device_type": "mobile",
                    "browser": "Safari",
                    "os_name": "iOS 14.2",
                },
                "ip_address": "192.168.1.1",
                "location_info": {
                    "country": "Italy",
                    "city": "Milan",
                    "location_display": "Milan, Italy",
                },
                "last_login": "2023-06-01T12:00:00Z",
                "is_current": True,
            }
        },
    )


class TerminateSessionRequest(BaseModel):
    """
    Request schema for terminating a specific session.
    """

    session_id: str = Field(..., description="ID of the session to terminate")
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"session_id": "sess_123abc456def"}},
    )


class UpdateDeviceTokenRequest(BaseModel):
    """
    Request schema for updating a device token.
    """

    device_token: str = Field(..., description="Device token for push notifications")
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"device_token": "token_123abc456def"}},
    )


class UpdateVoipTokenRequest(BaseModel):
    """
    Request schema for updating a VoIP token for iOS devices.
    """

    device_token: str = Field(..., description="VoIP token for iOS push notifications")
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"device_token": "voip_token_123abc456def"}},
    )
