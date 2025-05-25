import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# 导入配置
from backend.core.config import settings

# 导入所有模型
from backend.db.session import Base

# 确保导入所有模型，以便反射到metadata中
import backend.models.base
import backend.models.user
import backend.models.chat
import backend.models.agent
from backend.models.user import User
from backend.models.chat import Chat, ChatMessage
from backend.models.agent import Agent

# 打印所有表名，用于调试
print("已检测到以下表:")
for table in Base.metadata.tables.keys():
    print(f" - {table}")

# 从配置文件中获取配置
config = context.config

# 使用.env文件中的数据库配置
config.set_main_option(
    "sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI
)

# 加载logging配置（如果存在）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置target_metadata为Base.metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线运行迁移

    不需要实际连接到数据库。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 添加比较选项，确保检测到所有更改
        compare_type=True, 
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        # 添加比较选项，确保检测到所有更改
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """在线运行迁移

    需要连接到数据库。
    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online()) 