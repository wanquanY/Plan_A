from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, Field, PostgresDsn
from typing import List, Optional, Dict, Any, Union
import os
from dotenv import load_dotenv
from secrets import token_hex

# 加载.env文件
load_dotenv()


class Settings(BaseSettings):
    # API配置
    API_V1_STR: str = "/api/v1"
    
    # 服务配置
    PROJECT_NAME: str = "FreeWrite API"
    PROJECT_DESCRIPTION: str = "一个支持AI写作的笔记应用"
    PROJECT_VERSION: str = "0.1.0"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # 数据库配置
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "192.168.124.19")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "freewrite")
    
    # 数据库URI
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # JWT配置
    SECRET_KEY: str = Field(default_factory=lambda: token_hex(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))  # 默认30天
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CONSOLE_LOG_LEVEL: str = os.getenv("CONSOLE_LOG_LEVEL", "debug")
    FILE_LOG_LEVEL: str = os.getenv("FILE_LOG_LEVEL", "info")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "size")  # "size" 或 "time"
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760").split('#')[0].strip())  # 默认10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "30"))  # 默认保留30个备份
    
    # SQLAlchemy日志配置
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-2025-04-14")
    
    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "86400"))  # 默认记忆保存1天
    REDIS_MAX_MEMORY_MESSAGES: int = int(os.getenv("REDIS_MAX_MEMORY_MESSAGES", "100"))  # 默认每个会话最多保存100条消息
    REDIS_MAX_USER_MEMORIES: int = int(os.getenv("REDIS_MAX_USER_MEMORIES", "5"))  # 默认每个用户最多保留5个会话的记忆
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Tavily API配置
    TAVILY_API_KEY: Optional[str] = None
    
    @property
    def DATABASE_URI(self) -> Optional[PostgresDsn]:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"/{self.POSTGRES_DB}"
        )
    
    model_config = {
        "extra": "ignore",  # 允许额外的字段
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings() 