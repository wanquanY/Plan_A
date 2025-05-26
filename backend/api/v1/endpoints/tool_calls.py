from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.db.session import get_async_session
from backend.crud.tool_call import (
    get_tool_calls_by_message,
    get_tool_calls_by_conversation,
    get_tool_call_by_id
)
from backend.schemas.tool_call import ToolCallHistoryResponse
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.crud.chat import get_chat
from backend.utils.logging import api_logger

router = APIRouter()


@router.get("/message/{message_id}", response_model=List[ToolCallHistoryResponse])
async def get_message_tool_calls(
    message_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定消息的所有工具调用记录"""
    api_logger.info(f"获取消息工具调用记录: message_id={message_id}, user_id={current_user.id}")
    
    tool_calls = await get_tool_calls_by_message(db, message_id)
    
    # 验证权限：检查消息是否属于当前用户
    if tool_calls:
        # 通过第一个工具调用获取会话信息来验证权限
        chat = await get_chat(db, tool_calls[0].conversation_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此消息的工具调用记录"
            )
    
    return tool_calls


@router.get("/conversation/{conversation_id}", response_model=List[ToolCallHistoryResponse])
async def get_conversation_tool_calls(
    conversation_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定会话的所有工具调用记录"""
    api_logger.info(f"获取会话工具调用记录: conversation_id={conversation_id}, user_id={current_user.id}")
    
    # 验证权限：检查会话是否属于当前用户
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话的工具调用记录"
        )
    
    tool_calls = await get_tool_calls_by_conversation(db, conversation_id, limit)
    return tool_calls


@router.get("/{tool_call_id}", response_model=ToolCallHistoryResponse)
async def get_tool_call_detail(
    tool_call_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定工具调用的详细信息"""
    api_logger.info(f"获取工具调用详情: tool_call_id={tool_call_id}, user_id={current_user.id}")
    
    tool_call = await get_tool_call_by_id(db, tool_call_id)
    if not tool_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具调用记录不存在"
        )
    
    # 验证权限：检查会话是否属于当前用户
    chat = await get_chat(db, tool_call.conversation_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此工具调用记录"
        )
    
    return tool_call 