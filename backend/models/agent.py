from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, JSON, ARRAY, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel


class Agent(BaseModel):
    """Agent模型，用于定义聊天助手"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    system_prompt = Column(Text, nullable=True)  # 系统提示词
    model = Column(String, nullable=False)  # 模型名称
    max_memory = Column(Integer, default=10)  # 最大记忆条数
    model_settings = Column(JSON, nullable=True)  # 模型相关的设置，如temperature等
    tools_enabled = Column(JSON, nullable=True)  # 可用的工具配置，包含工具名称和相关参数
    
    # 添加唯一约束：每个用户只能有一个未删除的agent
    __table_args__ = (
        UniqueConstraint('user_id', 'is_deleted', name='uq_user_agent_not_deleted'),
    )
    
    # 关联关系
    user = relationship("User", back_populates="agents")
    chats = relationship("Chat", back_populates="agent", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="agent")  # Agent发送的消息 