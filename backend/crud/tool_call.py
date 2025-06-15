from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from backend.models.tool_call import ToolCallHistory
from backend.utils.logging import db_logger


async def create_tool_call(
    db: AsyncSession,
    message_id: int,
    session_id: int,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    arguments: Dict[str, Any],
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: str = "preparing",
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> ToolCallHistory:
    """创建工具调用记录"""
    db_logger.debug(f"创建工具调用记录: tool_call_id={tool_call_id}, tool_name={tool_name}, status={status}")
    
    tool_call = ToolCallHistory(
        user_id=user_id,
        message_id=message_id,
        session_id=session_id,
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
    session_id: int,
    limit: int = 100
) -> List[ToolCallHistory]:
    """根据会话ID获取工具调用记录"""
    result = await db.execute(
        select(ToolCallHistory).where(
            ToolCallHistory.session_id == session_id
        ).order_by(ToolCallHistory.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def get_tool_call_by_id(
    db: AsyncSession,
    tool_call_id: str
) -> Optional[ToolCallHistory]:
    """根据工具调用ID获取记录 - 支持public_id和tool_call_id"""
    # 判断是否为public_id（格式：tool-xxxxx）
    if tool_call_id.startswith('tool-'):
        # 使用public_id查询
        stmt = select(ToolCallHistory).where(ToolCallHistory.public_id == tool_call_id)
    else:
        # 使用tool_call_id查询（兼容旧格式）
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
    session_id: int
) -> int:
    """删除指定会话的所有工具调用记录"""
    stmt = delete(ToolCallHistory).where(ToolCallHistory.session_id == session_id)
    result = await db.execute(stmt)
    await db.commit()
    
    deleted_count = result.rowcount
    db_logger.debug(f"已删除会话 {session_id} 的 {deleted_count} 条工具调用记录")
    return deleted_count


async def get_or_create_tool_call(
    db: AsyncSession,
    message_id: int,
    session_id: int,
    tool_call_id: str,
    tool_name: str,
    function_name: str,
    arguments: Dict[str, Any],
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
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
        session_id=session_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        function_name=function_name,
        arguments=arguments,
        agent_id=agent_id,
        user_id=user_id,
        status=status,
        result=result,
        error_message=error_message
    )


async def create_tool_call_history(
    db: AsyncSession,
    session_id: int,
    message_id: int,
    function_name: str,
    function_arguments: str,
    function_result: str,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> ToolCallHistory:
    """创建工具调用历史记录"""
    # 创建记录
    db_tool_call = ToolCallHistory(
        message_id=message_id,
        session_id=session_id,
        function_name=function_name,
        function_arguments=function_arguments,
        function_result=function_result,
        agent_id=agent_id,
        user_id=user_id
    )
    
    db.add(db_tool_call)
    await db.commit()
    await db.refresh(db_tool_call)
    
    db_logger.debug(f"工具调用历史记录已创建: id={db_tool_call.id}")
    return db_tool_call


async def create_tool_call_with_result(
    db: AsyncSession,
    session_id: int,
    message_id: int,
    function_name: str,
    function_arguments: Dict[str, Any],
    function_result: Any,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> ToolCallHistory:
    """创建包含结果的工具调用记录"""
    
    # 序列化参数和结果
    serialized_args = json.dumps(function_arguments, ensure_ascii=False)
    serialized_result = json.dumps(function_result, ensure_ascii=False, default=str)
    
    # 创建记录
    db_tool_call = ToolCallHistory(
        message_id=message_id,
        session_id=session_id,
        function_name=function_name,
        function_arguments=serialized_args,
        function_result=serialized_result,
        agent_id=agent_id,
        user_id=user_id
    )
    
    db.add(db_tool_call)
    await db.commit()
    await db.refresh(db_tool_call)
    
    db_logger.debug(f"包含结果的工具调用记录已创建: id={db_tool_call.id}")
    return db_tool_call 