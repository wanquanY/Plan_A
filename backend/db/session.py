from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator, Generator
from sqlalchemy import event, text, create_engine
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.utils.logging import db_logger

# 创建异步引擎
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
    # 添加连接池配置
    pool_size=20,                    # 连接池大小
    max_overflow=30,                 # 最大溢出连接
    pool_pre_ping=True,             # 连接前ping检测
    pool_recycle=3600,              # 连接回收时间（1小时）
    pool_timeout=30,                # 获取连接超时时间
)

# 创建同步引擎
sync_engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+asyncpg", "postgresql"),
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
    # 添加连接池配置
    pool_size=10,                    # 同步连接池较小
    max_overflow=20,                 # 最大溢出连接
    pool_pre_ping=True,             # 连接前ping检测
    pool_recycle=3600,              # 连接回收时间（1小时）
    pool_timeout=30,                # 获取连接超时时间
)

# 创建异步会话工厂
async_session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# 创建同步会话工厂
sync_session_factory = sessionmaker(
    sync_engine, expire_on_commit=False
)

# 创建Base类，所有模型将继承此类
Base = declarative_base()


async def init_db():
    # 导入所有模型，确保它们被注册到Base.metadata中
    from backend.models import User, Chat, ChatMessage, Agent, Note
    
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # 如果需要，可以取消注释以在每次启动时删除所有表
        await conn.run_sync(Base.metadata.create_all)
    db_logger.info("数据库表初始化完成")


# 获取异步数据库会话
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    db_logger.debug("创建新的数据库会话")
    async with async_session_factory() as session:
        # 设置会话时区为北京时间
        await session.execute(text("SET timezone TO 'Asia/Shanghai';"))
        # 确保timestamp输出使用时区
        await session.execute(text("SET timezone_abbreviations TO 'Default';"))
        # 设置datestyle确保日期格式正确
        await session.execute(text("SET datestyle TO 'ISO, YMD';"))
        
        try:
            yield session
            await session.commit()
            db_logger.debug("数据库会话已提交")
        except Exception as e:
            await session.rollback()
            db_logger.error(f"数据库会话回滚: {str(e)}", exc_info=True)
            raise


# 获取同步数据库会话（非异步API使用）
def get_db() -> Generator[Session, None, None]:
    db_logger.debug("创建新的同步数据库会话")
    session = sync_session_factory()
    # 设置会话时区为北京时间
    session.execute(text("SET timezone TO 'Asia/Shanghai';"))
    # 确保timestamp输出使用时区
    session.execute(text("SET timezone_abbreviations TO 'Default';"))
    # 设置datestyle确保日期格式正确
    session.execute(text("SET datestyle TO 'ISO, YMD';"))
    
    try:
        yield session
        session.commit()
        db_logger.debug("同步数据库会话已提交")
    except Exception as e:
        session.rollback()
        db_logger.error(f"同步数据库会话回滚: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()
        db_logger.debug("同步数据库会话已关闭") 