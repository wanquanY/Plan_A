import asyncio
import logging
import asyncpg
from backend.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_database():
    """创建数据库，如果不存在的话"""
    try:
        # 连接到默认的postgres数据库
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database='postgres'  # 连接到默认数据库
        )
        
        # 检查目标数据库是否存在
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.POSTGRES_DB
        )
        
        if not row:
            # 如果数据库不存在，创建它
            await conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            logger.info(f'数据库 "{settings.POSTGRES_DB}" 已创建')
        else:
            logger.info(f'数据库 "{settings.POSTGRES_DB}" 已存在')
        
        # 关闭连接
        await conn.close()
        
        # 连接到新创建的数据库，设置时区
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
        
        # 设置时区为北京时间
        await conn.execute("SET TIME ZONE '+8:00';")
        await conn.execute("ALTER DATABASE \"{}\" SET timezone TO '+8:00';".format(settings.POSTGRES_DB))
        
        logger.info(f'数据库 "{settings.POSTGRES_DB}" 时区已设置为北京时间')
        await conn.close()
        
    except Exception as e:
        logger.error(f"创建数据库出错: {e}")
        raise

if __name__ == "__main__":
    """独立运行此脚本创建数据库"""
    asyncio.run(create_database())
    logger.info("数据库创建完成") 