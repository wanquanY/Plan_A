from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any

from backend.models.chat import Chat, ChatMessage
from backend.utils.logging import db_logger
from backend.services.title_generator import generate_title_with_ai
from backend.models.note import Note


async def create_chat(db: AsyncSession, user_id: int, chat_data=None, title: Optional[str] = None, agent_id: Optional[int] = None) -> Chat:
    """创建一个新的聊天会话
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        chat_data: ChatCreate模型数据（优先使用）
        title: 标题 (如果没有提供chat_data则使用此参数)
        agent_id: 代理ID (如果没有提供chat_data则使用此参数)
    """
    db_logger.info(f"创建新聊天会话: user_id={user_id}")
    
    # 如果提供了chat_data，使用其中的数据
    if chat_data:
        chat_title = chat_data.title or "新对话"
        chat_agent_id = getattr(chat_data, "agent_id", None)
    else:
        chat_title = title or "新对话"
        chat_agent_id = agent_id
    
    db_logger.info(f"创建新聊天会话: user_id={user_id}, agent_id={chat_agent_id}")
    
    chat = Chat(user_id=user_id, title=chat_title, agent_id=chat_agent_id)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    db_logger.info(f"聊天会话创建成功: id={chat.id}")
    return chat


async def get_chat(db: AsyncSession, conversation_id: int) -> Optional[Chat]:
    """获取聊天会话详情，不自动加载messages以避免异步加载问题"""
    query = select(Chat).where(
        and_(
            Chat.id == conversation_id,
            Chat.is_deleted == False
        )
    )  # 移除selectinload，避免延迟加载
    
    result = await db.execute(query)
    chat = result.scalars().first()
    
    return chat


async def get_user_chats(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> tuple[List[Chat], int]:
    """获取用户的所有聊天会话，不自动加载messages以避免异步加载问题
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        skip: 跳过的记录数
        limit: 返回的记录数上限
        
    Returns:
        Tuple[List[Chat], int]: 返回会话列表和总记录数
    """
    # 查询总记录数
    count_query = select(func.count()).select_from(
        select(Chat).where(
            and_(
                Chat.user_id == user_id,
                Chat.is_deleted == False
            )
        ).subquery()
    )
    total_count = await db.execute(count_query)
    total = total_count.scalar()
    
    # 查询分页数据
    query = select(Chat).where(
        and_(
            Chat.user_id == user_id,
            Chat.is_deleted == False
        )
    ).order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    chats = result.scalars().all()
    
    return list(chats), total


async def update_chat_title(db: AsyncSession, conversation_id: int, title: str) -> Optional[Chat]:
    """更新聊天会话标题"""
    query = update(Chat).where(
        and_(
            Chat.id == conversation_id,
            Chat.is_deleted == False
        )
    ).values(title=title).returning(Chat)
    
    result = await db.execute(query)
    await db.commit()
    
    updated_chat = result.scalars().first()
    return updated_chat


async def update_chat_agent(db: AsyncSession, conversation_id: int, agent_id: int) -> Optional[Chat]:
    """更新聊天会话关联的Agent"""
    query = update(Chat).where(
        and_(
            Chat.id == conversation_id,
            Chat.is_deleted == False
        )
    ).values(agent_id=agent_id).returning(Chat)
    
    result = await db.execute(query)
    await db.commit()
    
    updated_chat = result.scalars().first()
    return updated_chat


async def add_message(
    db: AsyncSession, 
    conversation_id: int, 
    role: str, 
    content: str,
    tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    agent_id: Optional[int] = None,
    tool_calls_data: Optional[List[Dict[str, Any]]] = None
) -> ChatMessage:
    """添加一条聊天消息"""
    db_logger.debug(f"添加聊天消息: conversation_id={conversation_id}, role={role}, agent_id={agent_id}, has_tools={bool(tool_calls_data)}")
    
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tokens=tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
        agent_id=agent_id,
        tool_calls_data=tool_calls_data
    )
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    db_logger.debug(f"聊天消息已保存: id={message.id}")
    return message


async def get_chat_messages(db: AsyncSession, conversation_id: int) -> List[ChatMessage]:
    """获取聊天会话的所有消息"""
    query = select(ChatMessage).where(
        and_(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.is_deleted == False
        )
    ).order_by(ChatMessage.created_at.asc())
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return list(messages)


async def soft_delete_chat(db: AsyncSession, conversation_id: int) -> bool:
    """软删除聊天会话"""
    chat = await get_chat(db, conversation_id)
    if not chat:
        return False
    
    chat.soft_delete()
    await db.commit()
    
    db_logger.info(f"聊天会话已软删除: id={conversation_id}")
    return True


async def soft_delete_messages_after(db: AsyncSession, conversation_id: int, message_id: int) -> int:
    """
    软删除指定消息ID及之后的所有消息
    
    Args:
        db: 数据库会话
        conversation_id: 会话ID
        message_id: 指定消息ID，包含该消息及之后的都会被删除
        
    Returns:
        int: 被软删除的消息数量
    """
    db_logger.info(f"执行消息软删除: conversation_id={conversation_id}, 从message_id={message_id}开始")
    
    # 获取需要软删除的所有消息
    query = select(ChatMessage).where(
        and_(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.id >= message_id,
            ChatMessage.is_deleted == False
        )
    ).order_by(ChatMessage.created_at.asc())
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # 软删除每条消息
    deleted_count = 0
    for message in messages:
        message.soft_delete()
        deleted_count += 1
    
    # 提交事务
    if deleted_count > 0:
        await db.commit()
        db_logger.info(f"已软删除{deleted_count}条消息，会话ID={conversation_id}，起始消息ID={message_id}")
    
    return deleted_count


async def get_latest_chat(db: AsyncSession, user_id: int) -> Optional[Chat]:
    """获取用户最新的聊天会话"""
    query = select(Chat).where(
        and_(
            Chat.user_id == user_id,
            Chat.is_deleted == False
        )
    ).order_by(Chat.updated_at.desc()).limit(1)
    
    result = await db.execute(query)
    chat = result.scalars().first()
    
    return chat 


async def update_message_tool_calls(
    db: AsyncSession,
    message_id: int,
    tool_calls_data: List[Dict[str, Any]]
) -> Optional[ChatMessage]:
    """更新消息的工具调用数据"""
    db_logger.debug(f"更新消息工具调用数据: message_id={message_id}")
    
    stmt = select(ChatMessage).where(ChatMessage.id == message_id)
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    
    if message:
        message.tool_calls_data = tool_calls_data
        await db.commit()
        await db.refresh(message)
        db_logger.debug(f"工具调用数据已更新: message_id={message_id}")
        return message
    
    db_logger.warning(f"消息不存在: message_id={message_id}")
    return None 