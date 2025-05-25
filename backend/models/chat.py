from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import BaseModel


class Chat(BaseModel):
    """聊天会话模型"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)  # 关联的Agent ID
    title = Column(String, nullable=True)  # 会话标题
    is_active = Column(Boolean, default=True)  # 是否为活跃会话
    
    # 关联关系
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="session")


class ChatMessage(BaseModel):
    """聊天消息模型"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)  # 消息的token数量
    prompt_tokens = Column(Integer, nullable=True)  # 提示词token数量
    total_tokens = Column(Integer, nullable=True)  # 总token数量
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 关联的Agent ID
    
    # 工具调用相关字段 - 作为AI消息的一部分
    tool_calls_data = Column(JSON, nullable=True)  # 存储工具调用的完整信息
    # 格式: [
    #   {
    #     "id": "call_123",
    #     "name": "serper_search", 
    #     "arguments": {"query": "..."},
    #     "status": "completed",
    #     "result": {...},
    #     "error": null,
    #     "started_at": "2025-01-01T00:00:00",
    #     "completed_at": "2025-01-01T00:00:05"
    #   }
    # ]
    
    # 关联关系
    chat = relationship("Chat", back_populates="messages")
    agent = relationship("Agent") 