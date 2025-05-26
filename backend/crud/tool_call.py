from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.models.tool_call import ToolCallHistory
from backend.utils.logging import db_logger


async def create_tool_call(
    db: AsyncSession,
    message_id: int,
    conversation_id: int,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    arguments: Dict[str, Any],
    agent_id: Optional[int] = None,
    status: str = "preparing",
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> ToolCallHistory:
    """创建工具调用记录"""
    db_logger.debug(f"创建工具调用记录: tool_call_id={tool_call_id}, tool_name={tool_name}, status={status}")
    
    tool_call = ToolCallHistory(
        message_id=message_id,
        conversation_id=conversation_id,
        agent_id=agent_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        function_name=function_name,
        arguments=arguments,
        status=status,
        started_at=datetime.now(),
        result=result,
        error_message=error_message
    )
    
    # 如果状态是完成或错误，设置完成时间
    if status in ["completed", "error"]:
        tool_call.completed_at = datetime.now()
    
    db.add(tool_call)
    await db.commit()
    await db.refresh(tool_call)
    
    db_logger.debug(f"工具调用记录已创建: id={tool_call.id}")
    return tool_call


async def update_tool_call_status(
    db: AsyncSession,
    tool_call_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Optional[ToolCallHistory]:
    """更新工具调用状态"""
    db_logger.debug(f"更新工具调用状态: tool_call_id={tool_call_id}, status={status}")
    
    stmt = select(ToolCallHistory).where(ToolCallHistory.tool_call_id == tool_call_id)
    query_result = await db.execute(stmt)
    tool_call = query_result.scalar_one_or_none()
    
    if tool_call:
        tool_call.status = status
        if result is not None:
            tool_call.result = result
        if error_message is not None:
            tool_call.error_message = error_message
        if status in ["completed", "error"]:
            tool_call.completed_at = datetime.now()
        
        await db.commit()
        await db.refresh(tool_call)
        db_logger.debug(f"工具调用状态已更新: id={tool_call.id}")
        return tool_call
    
    db_logger.warning(f"工具调用不存在: tool_call_id={tool_call_id}")
    return None


async def get_tool_calls_by_message(
    db: AsyncSession,
    message_id: int
) -> List[ToolCallHistory]:
    """获取消息的所有工具调用记录"""
    stmt = select(ToolCallHistory).where(
        ToolCallHistory.message_id == message_id
    ).order_by(ToolCallHistory.started_at)
    
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def get_tool_calls_by_conversation(
    db: AsyncSession,
    conversation_id: int,
    limit: Optional[int] = None
) -> List[ToolCallHistory]:
    """获取会话的所有工具调用记录"""
    stmt = select(ToolCallHistory).where(
        ToolCallHistory.conversation_id == conversation_id
    ).order_by(ToolCallHistory.started_at.desc())
    
    if limit:
        stmt = stmt.limit(limit)
    
    query_result = await db.execute(stmt)
    return query_result.scalars().all()


async def get_tool_call_by_id(
    db: AsyncSession,
    tool_call_id: str
) -> Optional[ToolCallHistory]:
    """根据工具调用ID获取记录"""
    stmt = select(ToolCallHistory).where(ToolCallHistory.tool_call_id == tool_call_id)
    query_result = await db.execute(stmt)
    return query_result.scalar_one_or_none()


async def delete_tool_calls_by_message(
    db: AsyncSession,
    message_id: int
) -> int:
    """删除消息的所有工具调用记录"""
    stmt = delete(ToolCallHistory).where(ToolCallHistory.message_id == message_id)
    query_result = await db.execute(stmt)
    await db.commit()
    
    deleted_count = query_result.rowcount
    db_logger.debug(f"已删除消息 {message_id} 的 {deleted_count} 条工具调用记录")
    return deleted_count


async def delete_tool_calls_by_conversation(
    db: AsyncSession,
    conversation_id: int
) -> int:
    """删除会话的所有工具调用记录"""
    stmt = delete(ToolCallHistory).where(ToolCallHistory.conversation_id == conversation_id)
    query_result = await db.execute(stmt)
    await db.commit()
    
    deleted_count = query_result.rowcount
    db_logger.debug(f"已删除会话 {conversation_id} 的 {deleted_count} 条工具调用记录")
    return deleted_count


async def get_or_create_tool_call(
    db: AsyncSession,
    message_id: int,
    conversation_id: int,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    arguments: Dict[str, Any],
    agent_id: Optional[int] = None,
    status: str = "preparing",
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> ToolCallHistory:
    """获取或创建工具调用记录，避免重复创建"""
    db_logger.debug(f"获取或创建工具调用记录: tool_call_id={tool_call_id}, tool_name={tool_name}")
    
    # 首先检查是否已存在
    existing_tool_call = await get_tool_call_by_id(db, tool_call_id)
    if existing_tool_call:
        db_logger.debug(f"工具调用记录已存在: id={existing_tool_call.id}")
        return existing_tool_call
    
    # 如果不存在，创建新记录
    return await create_tool_call(
        db=db,
        message_id=message_id,
        conversation_id=conversation_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        function_name=function_name,
        arguments=arguments,
        agent_id=agent_id,
        status=status,
        result=result,
        error_message=error_message
    ) 