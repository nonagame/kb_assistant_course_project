from pydantic import BaseModel, Field, EmailStr, model_validator, ValidationError


#定义一个类，指定用户传递那些信息
# 注册
class RegisterIn(BaseModel):
    username:str=Field(min_length=2,max_length=10)
    # 对密码格式进行校验
    email:EmailStr
    password:str
    confirm_password:str
    code:str
    full_name:str

    # 校验密码和确认密码一致
    @model_validator(mode='after')
    def password_match(self):
        if self.password!=self.confirm_password:
            raise ValidationError('Passwords do not match')
        return self

# 定义用户应该在注册后关注那些信息：
class CurrentUser(BaseModel):
    id:int
    username:str
    email:EmailStr
    full_name:str
    role:str
    permissions:set[str] # 权限

# 定义JWT登录认证
class LoginIn(BaseModel):
    account:str
    password:str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # 可选，规范做法

# 用来接收刷新token的参数
class RefreshIn(BaseModel):
    refresh_token:str=Field(min_length=20)

# 定义"数据的形状"
class ProfileUpdateIn(BaseModel):
    username: str | None = Field(None)
    email: str | None = Field(None)
    full_name: str | None = Field(None)

class updatePasswordIn(BaseModel):
    current_password: str
    new_password: str