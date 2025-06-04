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


# 工具配置的Schema
class ToolConfig(BaseModel):
    enabled: bool = Field(default=False, description="是否启用此工具")
    name: str = Field(..., description="工具名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    config: Optional[Dict[str, Any]] = Field(None, description="工具特定配置")


# Agent基础属性
class AgentBase(BaseModel):
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model: str = Field(..., description="使用的模型")
    max_memory: Optional[int] = Field(10, description="最大记忆条数")
    model_settings: Optional[ModelSettings] = Field(None, description="模型相关设置")
    tools_enabled: Optional[Dict[str, ToolConfig]] = Field(None, description="启用的工具配置")


# 创建Agent时的请求
class AgentCreate(AgentBase):
    pass


# 更新Agent时的请求
class AgentUpdate(BaseModel):
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_memory: Optional[int] = None
    model_settings: Optional[Dict[str, Any]] = None
    tools_enabled: Optional[Dict[str, Any]] = None


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
    model: str
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True 