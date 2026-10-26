from os.path import defpath

from fastapi import APIRouter, Depends
from pydantic import EmailStr
from sqlalchemy.orm import Session

from database.connection import get_session
from modules.user.model import User

router = APIRouter(prefix="/auth",tags=["用户认证"])
from modules.user.verification import send_code_email,generate_code
from modules.user.service import request_verification_code, login_user


@router.get("/sendcode")
async def send_code(email:EmailStr,db:Session=Depends(get_session)):
    # await send_code_email(email,generate_code())
    return await request_verification_code(email,db)

from modules.user.schemas import RegisterIn,CurrentUser,LoginIn,TokenOut,RefreshIn
from modules.user.service import register_user
# 插入用户传递的数据
@router.post("/register",response_model=CurrentUser)
async def register(userinfo:RegisterIn,db:Session=Depends(get_session)):
    # 调用serviece的代码存入数据
    # 在router中设置返回值,response_model
    return await register_user(db,userinfo)


@router.post("/login",response_model=TokenOut)
async def login(data:LoginIn,db:Session=Depends(get_session)):
    # 调用service实现登录
    return login_user(db,data)

from modules.user.schemas import RefreshIn
from modules.user.service import refresh_tokens
@router.post("/refresh",response_model=TokenOut)
async def refresh(data:RefreshIn,db:Session=Depends(get_session)):
    return  refresh_tokens(db,data)

# 获取当前用户信息
from modules.user.dependencies import get_current_user
@router.get("/me",response_model=CurrentUser)
def me(user:CurrentUser=Depends(get_current_user)):
    return user

# 更新个人信息
from modules.user.service import updateprofile
from modules.user.schemas import ProfileUpdateIn
@router.put(path="/me", response_model=CurrentUser)
def updateme(data: ProfileUpdateIn,
             user: CurrentUser = Depends(get_current_user), # 根据token解析的id
             db: Session = Depends(get_session)):
    return updateprofile(data, user, db)

# 修改密码
from modules.user.service import updatePasswordById
from modules.user.schemas import updatePasswordIn
@router.put("/me/password")
def updatePassword(data: updatePasswordIn,
                   current_user: CurrentUser = Depends(get_current_user),
                   db: Session = Depends(get_session)):
    return updatePasswordById(data, current_user, db)