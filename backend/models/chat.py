from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

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


class ChatMessage(BaseModel):
    """聊天消息模型"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)  # 消息关联的Agent ID
    role = Column(String, nullable=False)  # 角色：user, assistant, system
    content = Column(Text, nullable=False)  # 消息内容
    tokens = Column(Integer, nullable=True)  # 完成token使用量(completion_tokens)
    prompt_tokens = Column(Integer, nullable=True)  # 提示token使用量
    total_tokens = Column(Integer, nullable=True)  # 总token使用量
    
    # 关联关系
    chat = relationship("Chat", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")  # 消息关联的Agent 