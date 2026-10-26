# 访问数据库的文件

from sqlalchemy.orm import Session
from modules.user.model import User, role_permissions, Permission
from sqlalchemy import select
# 通过邮箱查询用户是否存在
def get_user_by_email(db:Session,email:str):
    # select * from user where user.email = email
    # scalar返回单个对象或 None
    return db.scalar(select(User).where(User.email==email))
# 通过user_id查询用户是否存在
def get_user_by_id(db:Session,user_id:int):
    # select * from user where user.id=id
    return db.scalar(select(User).where(User.id == user_id))

# 定义向user表插入一条数据的函数
def create_user(db:Session,user:User):
    db.add(user)
    db.commit()
    db.refresh(user)

# 获取该用户的权限code,permission的获取
def get_perssion(db:Session,id:int):
    #  在联合查询时 Table 对象需要加一个.c
    codes=db.scalars(select(Permission.code).join(role_permissions,
        Permission.code==role_permissions.c.permission_code).
        join(User,User.role_code==role_permissions.c.role_code).
        where(User.id==id,User.is_active.is_(True))
        ).all()
    return set(codes)

# 更新数据库
from modules.user.schemas import ProfileUpdateIn,CurrentUser
def update_user_profile(data: ProfileUpdateIn,
                        user: CurrentUser,
                        db: Session):
    # 需要找到与数据库对应的 model，来更新
    # ① 从数据库加载 User 对象到内存
    myuser = db.get(User, user.id)  # 根据主键查 ORM 对象

    if data.username != None:
        # ② 修改内存中的属性（SQLAlchemy 自动标记为"脏"）
        myuser.username = data.username  # 修改内存中的对象属性
    if data.email != None:
        myuser.email = data.email
    if data.full_name != None:
        myuser.full_name = data.full_name
    # 把数据库的对象进行更改

    # ③ 自动生成 UPDATE SQL 并发送到数据库
    db.flush()  # 发送 SQL 到数据库（但不提交事务）
    # ④ 提交事务
    db.commit()  # 提交事务，真正写入数据库
    return myuser

# 密码哈希
def update_password_hash(db: Session,user_id:int,password:str):
    user=db.get(User,user_id)
    user.password_hash=password
    db.flush()
    db.commit()
    return True