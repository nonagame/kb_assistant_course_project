# service存放业务代码的文件
from datetime import datetime

from fastapi import HTTPException

from modules.user.verification import generate_code, save_code, send_code_email, delete_code
from sqlalchemy.orm import Session
# 发送邮件，并存储到redis
from modules.user.verification import send_code_email
from modules.user.repository import get_user_by_email
async def request_verification_code(email:str,db:Session):
    """如果这个邮箱已经注册过，我们是没必要继续发邮件，直接提醒用户，该邮箱已经注册
    这个业务需求，翻译成技术。就是拿邮箱去数据库中查询，如果有，说明注册过
    告诉用户，该邮箱已经注册，如果没有，继续走下一个流程"""
    if get_user_by_email(db,email):
        raise HTTPException(status_code=503,detail="该邮箱已注册")
    try:
        code=generate_code()
        # 1.发送邮件
        await send_code_email(email,code)
        # 2.存入redis
        await save_code(email,code)
    except Exception as e:
        # 报错统一用raise
        raise HTTPException(status_code=500, detail=f"验证码发送失败: {str(e)}")
    return {"message":f"验证码发送成功，请及时去邮箱{email}查看"}

from modules.user.schemas import RegisterIn, CurrentUser, TokenOut
from modules.user.model import User
from modules.user.repository import create_user
from modules.user.verification import verify_code
from core.security import hash_password, verify_password, decode_refresh_token
from modules.user.repository import get_perssion
# 在service中开发一个函数，这个函数用户组装返回值数据
def to_current_user(db:Session,user:User):
    return CurrentUser(
        id=int(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role_code,
        permissions=get_perssion(db,int(user.id)),
    )

async def register_user(db:Session,userinfo:RegisterIn):
    # 1.校验
    # 1.1邮箱校验:如果该邮箱已经注册，告诉用户换一个邮箱
    # 拿邮箱去数据库中查，看看有没有，如果有就是已经注册过
    if get_user_by_email(db,userinfo.email):
        raise HTTPException(status_code=409,detail="该邮箱已注册，请更换")
    # 1.2验证码校验
    # 技术: redis中验证码有没有
    if not await verify_code(userinfo.email,userinfo.code):
        raise HTTPException(status_code=400,detail="验证码错误，请核对后重试")
    # 2.调用repository
    try:
        user=User(
            username=userinfo.username,
            email=userinfo.email,
            password_hash=hash_password(userinfo.password),
            role_code="public",
            is_active=True,
            created_at=datetime.now(),
            full_name=userinfo.full_name,
        )
        create_user(db,user)
        await delete_code(userinfo.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return to_current_user(db,user)

from core.security import create_token_pair

def _token_out(row) ->TokenOut:
    access_token,refresh_token=create_token_pair(
        int(row.id),
        str(row.role_code),
    )
    return TokenOut(access_token=access_token,refresh_token=refresh_token)

from modules.user.schemas import LoginIn
def login_user(db:Session,data:LoginIn):
    user:User=get_user_by_email(db,data.account)
    # ifuser isNone 如果你不是我的会员,或者你的密码不对
    if user is None or not verify_password(data.password,str(user.password_hash)):
        raise HTTPException(status_code=401,detail="账号或密码错误")
    # 如果用户没激活
    if not user.is_active:
        raise HTTPException(status_code=403,detail="用户已停用")
    return _token_out(user)

from modules.user.schemas import RefreshIn
from modules.user.repository import get_user_by_id
def refresh_tokens(db:Session,data:RefreshIn):
    user_id,token_role=decode_refresh_token(data.refresh_token)
    user:User=get_user_by_id(db,user_id)
    if user is None or not user.is_active or user.role_code!=token_role:
        raise HTTPException(status_code=401,detail="用户不存在，已停用或角色已变更")
    return _token_out(user)


# 调用repository,函数update_user_profile
from modules.user.schemas import ProfileUpdateIn,CurrentUser
from modules.user.repository import update_user_profile

# updateprofile —— 更新个人资料
def updateprofile(data: ProfileUpdateIn,
                  user: CurrentUser,
                  db: Session):
    myuser = update_user_profile(data, user, db)
    return to_current_user(db, myuser)

# updatePasswordById —— 修改密码
from modules.user.repository import update_password_hash
from modules.user.schemas import updatePasswordIn
def updatePasswordById(data: updatePasswordIn,
                       user: CurrentUser,
                       db: Session):
    # 1. 校验
    # 1.1 密码是否正确
    # 重新查数据库获取最新用户
    user = get_user_by_id(db, user.id)
    # 验证旧密码
    if not verify_password(data.current_password, str(user.password_hash)):
        raise HTTPException(status_code=400, detail="当前密码错误")
    # 防止新旧密码相同
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码和旧密码不能一样")

    # 2. 更新
    # 哈希新密码并更新
    if not update_password_hash(db, user.id, hash_password(data.new_password)):
        raise HTTPException(status_code=400, detail="新密码更新失败")

    return {"message": "您的密码修改成功"}