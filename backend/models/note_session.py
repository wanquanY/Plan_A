from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.models.base import BaseModel
from backend.utils.random_util import RandomUtil


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


# 为NoteSession模型添加事件监听器，在创建前自动生成public_id
@event.listens_for(NoteSession, 'before_insert')
def generate_note_session_public_id(mapper, connection, target):
    if not target.public_id:
        target.public_id = RandomUtil.generate_session_relation_id() 