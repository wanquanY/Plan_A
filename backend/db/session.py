from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator
from sqlalchemy import event, text

from backend.core.config import settings
from backend.utils.logging import db_logger

# 创建异步引擎
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=True,
    future=True,
)

# 创建异步会话工厂
async_session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# 创建Base类，所有模型将继承此类
Base = declarative_base()


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