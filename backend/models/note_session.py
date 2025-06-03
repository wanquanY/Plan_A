from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import BaseModel


class NoteSession(BaseModel):
    """笔记-会话关联模型"""
    __tablename__ = "note_sessions"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)  # 是否为笔记的主要会话
    
    # 关联关系
    note = relationship("Note", back_populates="note_sessions")
    session = relationship("Chat", back_populates="note_sessions")

    class Config:
        from_attributes = True 