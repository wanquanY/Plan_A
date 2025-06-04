from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ToolCallHistoryResponse(BaseModel):
    """工具调用历史响应模式"""
    id: int
    message_id: int
    session_id: int
    agent_id: Optional[int]
    
    # 工具调用基本信息
    tool_call_id: str
    tool_name: str
    function_name: str
    arguments: Optional[Dict[str, Any]]
    
    # 执行状态和结果
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    
    # 时间信息
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 

class ToolCallHistoryCreate(BaseModel):
    session_id: int 