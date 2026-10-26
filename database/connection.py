# 创建 ORM 基类和 Session
from collections.abc import Generator
from sqlalchemy import URL,create_engine,text
from sqlalchemy.orm import Session,sessionmaker
from core.config import settings

# 1. 数据库的配置
DATABASE_URL = URL.create(
    # 驱动
    drivername="mysql+pymysql",
    # 同户名、密码
    username=settings.db_user,
    password=settings.db_password,
    # 指定某台电脑的某个端
    host=settings.db_host,
    port=settings.db_port,
    # 哪一个库
    database=settings.db_name,
    # 其他参数 字符集
    query={"charset": "utf8mb4"},
)

# 2.数据库引擎 Engine：整个项目共用一个
engine=create_engine(
    DATABASE_URL,
    # 数据库的连接，一次性开启几个，数据库连接池的大小
    pool_size=10,
    max_overflow=10,
    #获取前测试连接有效性
    pool_pre_ping=True,
    # 多长时间不用，回收连接池中的连接
    pool_recycle=1800,
    # 如果多长时间没有连接到数据库，停止
    connect_args={"connect_timeout": 10},
)
# 3. Session 工厂：整个项目共用一个
sessionmaker  = sessionmaker(
    # 从哪个连接池获取数据
    bind=engine,
    # 连接类型
    class_=Session,
    # 是否自动刷新
    autoflush=False,
    # 是否提交事务
    expire_on_commit=False,
)
# 4. 每个请求创建一个 Session
# 调用这个函数能够从连接池获取一个数据库的连接
def get_session():
    # 获取一个连接
    session=sessionmaker()
    try:
        yield session
    finally:
        session.close()

# def get_db() -> Generator[Session, None, None]:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# 5. 数据库健康检查
def ping_database() -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
