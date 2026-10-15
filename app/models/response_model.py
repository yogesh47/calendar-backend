from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: str
    org_id: str
    name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class HealthResponse(BaseModel):
    status: str
    database: str
