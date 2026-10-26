from pydantic import BaseModel, Field

class RoleOut(BaseModel):
    code: str
    name: str
    permissions: list[str]

class RolePermissionsIn(BaseModel):
    permission_codes: list[str] = Field(max_length=100)

class UserRoleIn(BaseModel):
    role_code: str = Field(min_length=1, max_length=32)

class UserRoleOut(BaseModel):
    user_id: int
    role_code: str