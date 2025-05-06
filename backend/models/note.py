from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel


class Note(BaseModel):
    """笔记模型"""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False, default="新笔记")
    content = Column(Text, nullable=False, default="")
    last_edited_position = Column(Integer, nullable=True)  # 用户上次编辑位置
    is_public = Column(Boolean, default=False)  # 是否公开分享
    share_link = Column(String(255), nullable=True)  # 分享链接
    
    # 关联关系
    user = relationship("User", back_populates="notes")
    session = relationship("Chat", back_populates="notes", uselist=False) 