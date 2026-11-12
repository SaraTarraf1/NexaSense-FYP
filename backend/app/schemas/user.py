
import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class UserRegister(BaseModel):
    """
    Data received from the registration form.
    """

    full_name: str = Field(
        min_length=1,
        max_length=150,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    accept_terms: bool

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Full name is required")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(r"\d", value):
            raise ValueError(
                "Password must contain at least one number"
            )

        return value

    @field_validator("accept_terms")
    @classmethod
    def validate_terms(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "You must accept the terms and conditions"
            )

        return value


class UserResponse(BaseModel):
    """
    Data returned after successful registration.

    Passwords and password hashes are never returned.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
