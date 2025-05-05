from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

# 模型设置的Schema，用于JSON字段
class ModelSettings(BaseModel):
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    max_tokens: Optional[int] = Field(default=2048, ge=1)


# Agent基础属性
class AgentBase(BaseModel):
    name: str = Field(..., description="Agent昵称")
    avatar_url: Optional[str] = Field(None, description="头像链接")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model: str = Field(..., description="使用的模型")
    max_memory: Optional[int] = Field(10, description="最大记忆条数")
    model_settings: Optional[ModelSettings] = Field(None, description="模型相关设置")
    is_public: Optional[bool] = Field(False, description="是否公开")


# 创建Agent时的请求
class AgentCreate(AgentBase):
    pass


# 更新Agent时的请求
class AgentUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_memory: Optional[int] = None
    model_settings: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


# 返回Agent详情
class AgentInDB(AgentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 返回Agent列表
class AgentListResponse(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None
    model: str
    is_public: bool
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True 