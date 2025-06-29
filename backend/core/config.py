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
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
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
    
    # 默认Agent配置
    DEFAULT_AGENT_MODEL: str = os.getenv("DEFAULT_AGENT_MODEL", "gpt-4.1-2025-04-14")
    DEFAULT_AGENT_SYSTEM_PROMPT: str = os.getenv(
        "DEFAULT_AGENT_SYSTEM_PROMPT", 
        "你是一个智能、友善、有用的AI助手。你可以帮助用户回答问题、协助写作、整理思路，并提供各种有价值的建议。请保持回答的准确性和有用性。"
    )
    DEFAULT_AGENT_MAX_MEMORY: int = int(os.getenv("DEFAULT_AGENT_MAX_MEMORY", "20"))
    DEFAULT_AGENT_MODEL_SETTINGS: str = os.getenv(
        "DEFAULT_AGENT_MODEL_SETTINGS", 
        '{"temperature": 0.7, "top_p": 0.95, "presence_penalty": 0, "frequency_penalty": 0}'
    )
    DEFAULT_AGENT_TOOLS_ENABLED: str = os.getenv(
        "DEFAULT_AGENT_TOOLS_ENABLED", 
        '{}'
    )
    DEFAULT_AGENT_TEMPERATURE: float = float(os.getenv("DEFAULT_AGENT_TEMPERATURE", "0.7"))
    DEFAULT_AGENT_TOP_P: float = float(os.getenv("DEFAULT_AGENT_TOP_P", "1.0"))
    DEFAULT_AGENT_MAX_TOKENS: int = int(os.getenv("DEFAULT_AGENT_MAX_TOKENS", "30000"))
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Redis 记忆服务配置
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "86400"))  # 24小时，单位秒
    REDIS_MAX_MEMORY_MESSAGES: int = int(os.getenv("REDIS_MAX_MEMORY_MESSAGES", "50"))  # 每个会话的最大消息数
    REDIS_MAX_USER_MEMORIES: int = int(os.getenv("REDIS_MAX_USER_MEMORIES", "100"))  # 每个用户的最大记忆会话数
    
    # ID转换缓存配置  
    ID_CACHE_TTL: int = int(os.getenv("ID_CACHE_TTL", "3600"))  # 1小时
    ID_CACHE_ENABLED: bool = os.getenv("ID_CACHE_ENABLED", "true").lower() == "true"
    
    # Tavily API配置
    TAVILY_API_KEY: Optional[str] = None
    
    # MCP配置
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
    MCP_SERVERS: Dict[str, Any] = {}
    MCP_CONNECTION_TIMEOUT: int = int(os.getenv("MCP_CONNECTION_TIMEOUT", "30"))  # 连接超时时间(秒)
    MCP_REQUEST_TIMEOUT: int = int(os.getenv("MCP_REQUEST_TIMEOUT", "60"))  # 请求超时时间(秒)
    MCP_RETRY_ATTEMPTS: int = int(os.getenv("MCP_RETRY_ATTEMPTS", "3"))  # 重试次数
    MCP_RETRY_DELAY: float = float(os.getenv("MCP_RETRY_DELAY", "1.0"))  # 重试延迟(秒)
    
    # MCP内置服务器配置
    MCP_NOTE_ENABLED: bool = os.getenv("MCP_NOTE_ENABLED", "true").lower() == "true"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_mcp_servers()
    
    def _load_mcp_servers(self):
        """从环境变量加载MCP服务器配置"""
        mcp_servers_env = os.getenv("MCP_SERVERS", "")
        if mcp_servers_env:
            try:
                import json
                self.MCP_SERVERS = json.loads(mcp_servers_env)
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认配置
                self.MCP_SERVERS = {}
        
        # 如果没有配置外部服务器，使用默认内置服务器配置
        if not self.MCP_SERVERS:
            self.MCP_SERVERS = {
                "note": {
                    "enabled": self.MCP_NOTE_ENABLED,
                    "type": "stdio", 
                    "command": "python",
                    "args": ["-m", "backend.mcp.servers.note_server"],
                    "description": "笔记阅读和编辑服务",
                    "name": "note-server"
                }
            }
    
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