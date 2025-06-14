from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, event
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel
from backend.utils.random_util import RandomUtil


class Note(BaseModel):
    """笔记模型"""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="新笔记")
    content = Column(Text, nullable=False, default="")
    last_edited_position = Column(Integer, nullable=True)  # 用户上次编辑位置
    is_public = Column(Boolean, default=False)  # 是否公开分享
    share_link = Column(String(255), nullable=True)  # 分享链接
    
    # 关联关系
    user = relationship("User", back_populates="notes")
    note_sessions = relationship("NoteSession", back_populates="note", cascade="all, delete-orphan")
    
    # 移除会触发懒加载的property方法，改为在需要时通过明确的查询获取
    # 这些方法会在业务逻辑层通过专门的查询来实现，避免在模型层产生异步问题
    
    def get_session_count(self):
        """获取关联的会话数量（同步方法，仅用于已加载的数据）"""
        if hasattr(self, '_note_sessions_loaded') and self._note_sessions_loaded:
            return len([ns for ns in self.note_sessions if not ns.is_deleted])
        return 0
    
    def has_primary_session(self):
        """检查是否有主要会话（同步方法，仅用于已加载的数据）"""
        if hasattr(self, '_note_sessions_loaded') and self._note_sessions_loaded:
            return any(ns.is_primary for ns in self.note_sessions if not ns.is_deleted)
        return False


# 为Note模型添加事件监听器，在创建前自动生成public_id
@event.listens_for(Note, 'before_insert')
def generate_note_public_id(mapper, connection, target):
    if not target.public_id:
        target.public_id = RandomUtil.generate_note_id() 