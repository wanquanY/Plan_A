from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class NoteBase(BaseModel):
    """基础笔记模型"""
    title: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = False
    

class NoteCreate(NoteBase):
    """创建笔记请求模型"""
    pass


class NoteUpdate(NoteBase):
    """更新笔记请求模型"""
    last_edited_position: Optional[int] = None


class NoteResponse(NoteBase):
    """笔记响应模型"""
    id: str
    user_id: str
    session_id: Optional[str] = None
    last_edited_position: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteList(BaseModel):
    """笔记列表项模型"""
    id: str
    title: str
    session_id: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 