# Third-party imports
from sqladmin import ModelView

# Local application imports
from app.models.auth.session import Session
from app.models.auth.user import User


class UserAdmin(ModelView):  # type: ignore[misc]
    model = User
    column_list = [
        "id",
        "is_admin",
        "email",
        "first_name",
        "last_name",
        "is_email_verified",
        "is_phone_number_verified",
        "created_at",
        "updated_at",
    ]

    column_formatters = {
        "sessions": lambda m, a: m.session.id if hasattr(m, "session") else "-",
    }


class SessionAdmin(ModelView):  # type: ignore[misc]
    model = Session
    column_list = [
        "id",
        "user",
        "access_token_jti",
        "refresh_token_jti",
        "device_type",
        "device_name",
        "city",
        "country",
        "last_login",
        "is_active",
        "created_at",
        "updated_at",
        "device_token",
    ]
