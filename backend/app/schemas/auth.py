from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class BrandRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=2, max_length=255)
    sector: str | None = None
    province: str | None = None
    location: str | None = None
    admin_sector: str | None = None
    admin_cell: str | None = None
    admin_village: str | None = None
    address_detail: str | None = None
    phone_number: str | None = None
    security_question: str | None = Field(default=None, max_length=255)
    security_answer: str | None = Field(default=None, max_length=255)


class InfluencerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=255)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\.]+$")
    province: str | None = None
    location: str | None = None
    admin_sector: str | None = None
    admin_cell: str | None = None
    admin_village: str | None = None
    address_detail: str | None = None
    sector: str | None = None
    phone_number: str | None = None
    security_question: str | None = Field(default=None, max_length=255)
    security_answer: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetPromptResponse(BaseModel):
    security_question: str | None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    security_answer: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
