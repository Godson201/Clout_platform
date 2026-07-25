from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class BrandRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=2, max_length=255)
    sector: str | None = None
    location: str | None = None
    phone_number: str | None = None


class InfluencerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=255)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\.]+$")
    location: str | None = None
    sector: str | None = None
    phone_number: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
