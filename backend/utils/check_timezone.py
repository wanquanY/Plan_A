import asyncio
import asyncpg
from datetime import datetime
import pytz

from backend.core.config import settings
from backend.utils.logging import db_logger
from backend.utils.time_util import to_beijing_time


async def check_timezone():
    """检查数据库时区设置"""
    try:
        # 连接到数据库
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
        
        # 检查当前时区设置
        row = await conn.fetchrow("SHOW timezone;")
        db_timezone = row[0]
        print(f"数据库时区设置: {db_timezone}")
        
        # 检查当前时间
        row = await conn.fetchrow("SELECT now();")
        db_time = row[0]
        print(f"数据库当前时间: {db_time}")
        
        # 检查北京时间
        row = await conn.fetchrow("SELECT timezone('Asia/Shanghai', now());")
        beijing_time_correct = row[0]
        print(f"数据库北京时间: {beijing_time_correct}")
        
        # 另一种检查北京时间的方式
        row = await conn.fetchrow("SELECT now() AT TIME ZONE 'Asia/Shanghai';")
        beijing_time_alt = row[0]
        print(f"数据库北京时间(另一种方式): {beijing_time_alt}")
        
        # 检查时区设置
        row = await conn.fetchrow("SELECT extract(timezone from now())/3600 as tz_hour;")
        tz_hour = row[0]
        print(f"当前时区小时差: {tz_hour} (应该是0表示UTC，8表示北京时间)")
        
        # 检查Python时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        python_time = datetime.now(beijing_tz)
        print(f"Python北京时间: {python_time}")
        
        # 检查时区设置是否有效
        await conn.execute("SET timezone TO 'Asia/Shanghai';")
        row = await conn.fetchrow("SELECT now();")
        new_db_time = row[0]
        print(f"设置时区后数据库时间: {new_db_time}")
        
        # 永久设置数据库时区
        await conn.execute(f"ALTER DATABASE {settings.POSTGRES_DB} SET timezone TO 'Asia/Shanghai';")
        print(f"已将数据库 {settings.POSTGRES_DB} 的默认时区设置为 'Asia/Shanghai'")
        
        # 关闭连接
        await conn.close()
    
    except Exception as e:
        print(f"检查时区出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(check_timezone()) 