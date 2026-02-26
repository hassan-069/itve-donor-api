from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Achievement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    icon_url: str = Field(default="", max_length=500)
    date_earned: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DonorSignup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    phone: str
    name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.]+$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return EmailStr(str(value).lower())

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain at least one special character.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        # Accept formats like "+923001234567" or "+92 3001234567"
        normalized = re.sub(r"[\s-]", "", value)
        if not re.fullmatch(r"^\+92\d{10}$", normalized):
            raise ValueError("Phone format must be +92XXXXXXXXXX (10 digits after +92).")
        return normalized


class DonorProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    username: str
    name: str
    about: Optional[str] = ""
    followers_count: int = Field(default=0, ge=0)
    following_count: int = Field(default=0, ge=0)
    beneficiaries_count: int = Field(default=0, ge=0)
    total_amount_donated: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    donor_class: str = ""
    donor_rank: int = Field(default=0, ge=0)
    achievements: list[Achievement] = Field(default_factory=list)
    profile_image_url: Optional[str] = ""


class DonorUpdateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    about: Optional[str] = Field(None, max_length=500)
    profile_image_url: Optional[str] = Field(None, max_length=500)


class AchievementPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    achievements: list[Achievement] = Field(default_factory=list)
