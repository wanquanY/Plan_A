"""
MCP服务器配置模型

用于存储和管理MCP服务器的配置信息。
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON, event
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel
from backend.utils.random_util import RandomUtil


class MCPServer(BaseModel):
    """MCP服务器配置模型"""
    
    __tablename__ = "mcp_servers"
    
    # 基础信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID")
    name = Column(String(100), nullable=False, index=True, comment="服务器名称")
    description = Column(Text, comment="服务器描述")
    
    # 公开性控制
    is_public = Column(Boolean, default=False, nullable=False, comment="是否公开分享")
    share_link = Column(String(255), nullable=True, comment="分享链接")
    
    # 连接配置
    transport_type = Column(String(20), nullable=False, default="stdio", comment="传输类型: stdio, sse")
    command = Column(String(500), comment="启动命令")
    args = Column(JSON, comment="命令参数数组")
    env = Column(JSON, comment="环境变量")
    cwd = Column(String(500), comment="工作目录")
    
    # SSE配置 (当transport_type为sse时使用)
    url = Column(String(500), comment="SSE服务器URL")
    headers = Column(JSON, comment="HTTP请求头")
    
    # 状态配置
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    auto_start = Column(Boolean, default=True, nullable=False, comment="是否自动启动")
    
    # 连接配置
    timeout = Column(Integer, default=30, comment="连接超时时间(秒)")
    retry_attempts = Column(Integer, default=3, comment="重试次数")
    retry_delay = Column(Integer, default=1, comment="重试延迟(秒)")
    
    # 扩展配置
    config = Column(JSON, comment="额外配置信息")
    tags = Column(JSON, comment="标签列表")
    
    # 关联关系
    user = relationship("User", back_populates="mcp_servers")
    tool_calls = relationship("ToolCallHistory", back_populates="mcp_server", cascade="all, delete-orphan")
    
    # 添加唯一约束：同一用户下的服务器名称不能重复
    __table_args__ = (
        {'comment': 'MCP服务器配置表'}
    )
    
    def __repr__(self):
        return f"<MCPServer(id={self.id}, name='{self.name}', user_id={self.user_id}, enabled={self.enabled})>"
    
    def to_config_dict(self) -> dict:
        """转换为MCP客户端配置格式"""
        config = {
            "enabled": self.enabled,
            "type": self.transport_type,
            "description": self.description,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
        }
        
        if self.transport_type == "stdio":
            config.update({
                "command": self.command,
                "args": self.args or [],
                "env": self.env or {},
                "cwd": self.cwd,
            })
        elif self.transport_type == "sse":
            config.update({
                "url": self.url,
                "headers": self.headers or {},
            })
        
        # 添加额外配置
        if self.config:
            config.update(self.config)
            
        return config
    
    @classmethod
    def from_config_dict(cls, user_id: int, name: str, config: dict) -> "MCPServer":
        """从配置字典创建实例"""
        return cls(
            user_id=user_id,
            name=name,
            description=config.get("description", ""),
            transport_type=config.get("type", "stdio"),
            command=config.get("command"),
            args=config.get("args", []),
            env=config.get("env", {}),
            cwd=config.get("cwd"),
            url=config.get("url"),
            headers=config.get("headers", {}),
            enabled=config.get("enabled", True),
            auto_start=config.get("auto_start", True),
            timeout=config.get("timeout", 30),
            retry_attempts=config.get("retry_attempts", 3),
            retry_delay=config.get("retry_delay", 1),
            is_public=config.get("is_public", False),
            config={k: v for k, v in config.items() if k not in [
                "type", "command", "args", "env", "cwd", "url", "headers",
                "enabled", "auto_start", "timeout", "retry_attempts", "retry_delay", 
                "description", "is_public"
            ]},
            tags=config.get("tags", [])
        )


# 为MCPServer模型添加事件监听器，在创建前自动生成public_id
@event.listens_for(MCPServer, 'before_insert')
def generate_mcp_server_public_id(mapper, connection, target):
    if not target.public_id:
        target.public_id = RandomUtil.generate_mcp_server_id() 