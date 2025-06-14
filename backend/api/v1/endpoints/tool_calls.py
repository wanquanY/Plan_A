from fastapi import APIRouter, Depends, HTTPException, status, Query
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
    message_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定消息的所有工具调用记录"""
    api_logger.info(f"获取消息工具调用记录: message_id={message_id}, user_id={current_user.public_id}")
    
    # 转换message_id为数据库内部ID
    from backend.utils.id_converter import IDConverter
    db_message_id = await IDConverter.get_message_db_id(db, message_id)
    if not db_message_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    tool_calls = await get_tool_calls_by_message(db, db_message_id)
    
    # 验证权限
    if tool_calls:
        # 需要通过数据库session_id获取Chat对象，然后转换为public_id进行验证
        session_public_id = await IDConverter.get_chat_public_id(db, tool_calls[0].session_id)
        if session_public_id:
            chat = await get_chat(db, session_public_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问这些工具调用记录"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
    
    # 转换所有ID为public_id
    response_data = []
    for tool_call in tool_calls:
        response_item = {
            "id": tool_call.public_id,  # 使用public_id
            "message_id": message_id,  # 直接使用传入的message_id（已经是public_id）
            "session_id": await IDConverter.get_chat_public_id(db, tool_call.session_id),
            "agent_id": await IDConverter.get_agent_public_id(db, tool_call.agent_id) if tool_call.agent_id else None,
            "tool_call_id": tool_call.tool_call_id,
            "tool_name": tool_call.tool_name,
            "function_name": tool_call.function_name,
            "arguments": tool_call.arguments,
            "status": tool_call.status,
            "result": tool_call.result,
            "error_message": tool_call.error_message,
            "started_at": tool_call.started_at,
            "completed_at": tool_call.completed_at,
            "created_at": tool_call.created_at,
            "updated_at": tool_call.updated_at
        }
        response_data.append(response_item)
    
    return response_data


@router.get("/conversation/{session_id}", response_model=List[ToolCallHistoryResponse])
async def get_conversation_tool_calls(
    session_id: str,
    limit: int = Query(50, ge=1, le=100, description="返回记录数量限制"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定会话的工具调用记录"""
    api_logger.info(f"获取会话工具调用记录: session_id={session_id}, user_id={current_user.public_id}")
    
    # 验证会话权限
    chat = await get_chat(db, session_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问此会话"
        )
    
    # 转换session_id为数据库内部ID
    from backend.utils.id_converter import IDConverter
    db_session_id = await IDConverter.get_chat_db_id(db, session_id)
    if not db_session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    tool_calls = await get_tool_calls_by_conversation(db, db_session_id, limit)
    
    # 转换所有ID为public_id
    response_data = []
    for tool_call in tool_calls:
        response_item = {
            "id": tool_call.public_id,  # 使用public_id
            "message_id": await IDConverter.get_message_public_id(db, tool_call.message_id),
            "session_id": session_id,  # 直接使用传入的session_id（已经是public_id）
            "agent_id": await IDConverter.get_agent_public_id(db, tool_call.agent_id) if tool_call.agent_id else None,
            "tool_call_id": tool_call.tool_call_id,
            "tool_name": tool_call.tool_name,
            "function_name": tool_call.function_name,
            "arguments": tool_call.arguments,
            "status": tool_call.status,
            "result": tool_call.result,
            "error_message": tool_call.error_message,
            "started_at": tool_call.started_at,
            "completed_at": tool_call.completed_at,
            "created_at": tool_call.created_at,
            "updated_at": tool_call.updated_at
        }
        response_data.append(response_item)
    
    return response_data


@router.get("/{tool_call_id}", response_model=ToolCallHistoryResponse)
async def get_tool_call_detail(
    tool_call_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取指定工具调用的详细信息"""
    api_logger.info(f"获取工具调用详情: tool_call_id={tool_call_id}, user_id={current_user.public_id}")
    
    tool_call = await get_tool_call_by_id(db, tool_call_id)
    if not tool_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具调用记录不存在"
        )
    
    # 验证权限
    from backend.utils.id_converter import IDConverter
    session_public_id = await IDConverter.get_chat_public_id(db, tool_call.session_id)
    if not session_public_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    chat = await get_chat(db, session_public_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问此工具调用记录"
        )
    
    # 转换所有ID为public_id
    response_data = {
        "id": tool_call.public_id,  # 使用public_id
        "message_id": await IDConverter.get_message_public_id(db, tool_call.message_id),
        "session_id": session_public_id,  # 已经转换过的
        "agent_id": await IDConverter.get_agent_public_id(db, tool_call.agent_id) if tool_call.agent_id else None,
        "tool_call_id": tool_call.tool_call_id,
        "tool_name": tool_call.tool_name,
        "function_name": tool_call.function_name,
        "arguments": tool_call.arguments,
        "status": tool_call.status,
        "result": tool_call.result,
        "error_message": tool_call.error_message,
        "started_at": tool_call.started_at,
        "completed_at": tool_call.completed_at,
        "created_at": tool_call.created_at,
        "updated_at": tool_call.updated_at
    }
    
    return response_data 