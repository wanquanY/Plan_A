from sqlalchemy import Column, Integer, String, Boolean, DateTime, event
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.models.base import BaseModel
from backend.utils.random_util import RandomUtil


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)  # 添加用户头像字段，非必填
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # 管理员权限
    
    # 关联关系
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")


# 为User模型添加事件监听器，在创建前自动生成public_id
@event.listens_for(User, 'before_insert')
def generate_user_public_id(mapper, connection, target):
    if not target.public_id:
        target.public_id = RandomUtil.generate_user_id() 