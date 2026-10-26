from sqlalchemy.orm import DeclarativeBase

# 为sqlalchemy注册模型类的一个基类
class Base(DeclarativeBase):
    """Base model for all models"""
    # 之前在学习时，此处增加了命名规范


