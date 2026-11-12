
from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EquipmentBase(BaseModel):
    identifier: str = Field(min_length=1, max_length=100)
    installation_date: date | None = None
    name: str = Field(min_length=1, max_length=150)
    equipment_type: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=200)

    manufacturer: str | None = Field(default=None, max_length=150)
    model: str | None = Field(default=None, max_length=150)
    serial_number: str | None = Field(default=None, max_length=150)
    description: str | None = None

    @field_validator("identifier", mode="before")
    @classmethod
    def validate_identifier(cls, value):
        if not isinstance(value, str):
            raise ValueError("Identifier must be a string.")
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,99}", value):
            raise ValueError("Use letters, numbers, hyphens or underscores for the identifier.")
        return value

    @field_validator(
        "name",
        "equipment_type",
        "location",
        mode="before",
    )
    @classmethod
    def validate_required_fields(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("This field cannot be empty.")

        return value.strip()

    @field_validator(
        "manufacturer",
        "model",
        "serial_number",
        "description",
        mode="before",
    )
    @classmethod
    def clean_optional_fields(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            return value.strip() or None

        raise ValueError("This field must be a string.")


class EquipmentCreate(EquipmentBase):
    """Schema for registering new equipment."""
    identifier: str | None = Field(default=None, min_length=1, max_length=100)


class EquipmentUpdate(BaseModel):
    """Schema for updating existing equipment."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    equipment_type: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, min_length=1, max_length=200)

    manufacturer: str | None = Field(default=None, max_length=150)
    model: str | None = Field(default=None, max_length=150)
    serial_number: str | None = Field(default=None, max_length=150)
    description: str | None = None
    identifier: str | None = Field(default=None, min_length=1, max_length=100)
    installation_date: date | None = None

    @field_validator("identifier", mode="before")
    @classmethod
    def validate_identifier(cls, value):
        return EquipmentBase.validate_identifier(value)

    @field_validator(
        "name",
        "equipment_type",
        "location",
    )
    @classmethod
    def validate_required_fields(cls, value):
        if value is not None:
            if not value.strip():
                raise ValueError("This field cannot be empty.")
            return value.strip()

        return value

    @field_validator(
        "manufacturer",
        "model",
        "serial_number",
        "description",
    )
    @classmethod
    def clean_optional_fields(cls, value):
        if value is not None:
            return value.strip() or None

        return value


class EquipmentResponse(EquipmentBase):
    """Schema for returning equipment information."""

    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
