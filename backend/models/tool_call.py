from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import BaseModel


class ToolCallHistory(BaseModel):
    """工具调用历史记录模型"""
    __tablename__ = "tool_call_history"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    
    # 工具调用基本信息
    tool_call_id = Column(String, nullable=False, index=True)  # 工具调用的唯一ID
    tool_name = Column(String, nullable=False, index=True)  # 工具名称
    function_name = Column(String, nullable=False)  # 函数名称（通常与tool_name相同）
    arguments = Column(JSON, nullable=True)  # 工具调用参数
    
    # 执行状态和结果
    status = Column(String, nullable=False, default="preparing")  # preparing, executing, completed, error
    result = Column(JSON, nullable=True)  # 工具调用结果
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 时间信息
    started_at = Column(DateTime(timezone=True), nullable=True)  # 开始执行时间
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间
    
    # 关联关系
    message = relationship("ChatMessage", back_populates="tool_calls")
    conversation = relationship("Chat")
    agent = relationship("Agent") 