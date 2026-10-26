import secrets

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from core.config import settings
from redis.asyncio import Redis

# 构建数据库连接池
# redis库默认取出的连接就是从连接池取的，所以一般不用关闭
redis_client=Redis.from_url(settings.redis_url,encoding="utf-8",decode_responses=True)

# 根据邮箱获取key，自定义
def _key(email: str) -> str:
    # 给注册功能申请验证码时，设计一个redis的key，这个key注意不和其它功能冲突
    return f"kb:register:code:{email.strip().lower()}"
# 保存code数据到redis库
async def save_code(email:str,code:str) -> None:
    await redis_client.set(_key(email),code,ex=300)
# 从数据库删除code数据
async def delete_code(email:str) -> None:
    await redis_client.delete(_key(email))

# 验证code
async def verify_code(email:str,code:str) -> bool:
    save_codes=await redis_client.get(_key(email))
    # 判断传递过来的code和数据库中的code是否是相等的
    """双重判断：
    - save_code is not None → 验证码存在且未过期
    - secrets.compare_digest(save_code, code) → 安全地比较内容是否一致"""
    return save_codes is not None and secrets.compare_digest(save_codes,code)

# 1.生成随机数的验证码
def generate_code() ->str:
    # random.random 小于1w，0-9999  0090
    # {:.2f}
    return f"{secrets.randbelow(10_000):04d}"

# 2.准备FastMail这个对象，需要用这个对象发送验证码
def create_mail_instance() -> FastMail:
    # 校验：对必须加的配置，加上，如果没有必须的任何配置直接报错
    required = {
        "MAIL_USERNAME": settings.mail_username,
        "MAIL_PASSWORD": settings.mail_password,
        "MAIL_FROM": settings.mail_from,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"缺少 QQ 邮箱配置：{', '.join(missing)}")

    config = ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    return FastMail(config)

# 3.发送验证码
async def send_code_email(email: str, code: str) -> None:
    message = MessageSchema(
        # 主题
        subject="【知识库智能助手】注册验证码",
        # 发送到邮箱，可以同时发送给多人
        recipients=[email],
        # 邮件内容
        body=f"您的注册验证码为：{code}，请在 5 分钟内使用。",
        # 类型 plain：字符串
        subtype=MessageType.plain,
    )
    await create_mail_instance().send_message(message)