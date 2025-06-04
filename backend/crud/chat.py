from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any

from backend.models.chat import Chat, ChatMessage
from backend.utils.logging import db_logger, api_logger
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


async def get_chat(db: AsyncSession, session_id: int) -> Optional[Chat]:
    """
    获取指定ID的聊天会话
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        
    Returns:
        Chat对象或None
    """
    try:
        result = await db.execute(
            select(Chat).where(Chat.id == session_id, Chat.is_active == True)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        api_logger.error(f"获取聊天会话失败: {e}")
        return None


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


async def update_chat_title(db: AsyncSession, session_id: int, title: str) -> Optional[Chat]:
    """
    更新聊天会话标题
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        title: 新标题
        
    Returns:
        更新后的Chat对象或None
    """
    try:
        chat = await get_chat(db, session_id)
        if chat:
            chat.title = title
            await db.commit()
            await db.refresh(chat)
            return chat
        return None
    except Exception as e:
        api_logger.error(f"更新聊天会话标题失败: {e}")
        await db.rollback()
        return None


async def update_chat_agent(db: AsyncSession, session_id: int, agent_id: int) -> Optional[Chat]:
    """
    更新聊天会话关联的Agent
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        agent_id: Agent ID
        
    Returns:
        更新后的Chat对象或None
    """
    try:
        chat = await get_chat(db, session_id)
        if chat:
            chat.agent_id = agent_id
            await db.commit()
            await db.refresh(chat)
            return chat
        return None
    except Exception as e:
        api_logger.error(f"更新聊天会话Agent失败: {e}")
        await db.rollback()
        return None


async def add_message(
    db: AsyncSession, 
    session_id: int,
    role: str, 
    content: str,
    tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    agent_id: Optional[int] = None,
) -> Optional[ChatMessage]:
    """
    添加聊天消息到数据库
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        role: 消息角色（user, assistant, system）
        content: 消息内容
        tokens: 消息token数量
        prompt_tokens: 提示词token数量
        total_tokens: 总token数量
        agent_id: Agent ID
        
    Returns:
        创建的ChatMessage对象或None
    """
    try:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tokens=tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            agent_id=agent_id
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    except Exception as e:
        api_logger.error(f"添加消息失败: {e}")
        await db.rollback()
        return None


async def get_chat_messages(db: AsyncSession, session_id: int) -> List[ChatMessage]:
    """
    获取指定聊天会话的所有消息
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        
    Returns:
        ChatMessage对象列表
    """
    try:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()
    except Exception as e:
        api_logger.error(f"获取聊天消息失败: {e}")
        return []


async def soft_delete_chat(db: AsyncSession, session_id: int) -> bool:
    """
    软删除聊天会话
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        
    Returns:
        是否删除成功
    """
    try:
        chat = await get_chat(db, session_id)
        if chat:
            chat.is_active = False
            await db.commit()
            return True
        return False
    except Exception as e:
        api_logger.error(f"软删除聊天会话失败: {e}")
        await db.rollback()
        return False
    

async def soft_delete_messages_after(db: AsyncSession, session_id: int, message_id: int) -> int:
    """
    软删除指定消息ID之后的所有消息
    
    Args:
        db: 数据库会话
        session_id: 会话ID
        message_id: 起始消息ID（该消息之后的消息将被删除）
        
    Returns:
        删除的消息数量
    """
    try:
        # 获取指定消息的创建时间
        target_message_result = await db.execute(
            select(ChatMessage.created_at)
            .where(ChatMessage.id == message_id, ChatMessage.session_id == session_id)
        )
        target_message_time = target_message_result.scalar_one_or_none()
        
        if not target_message_time:
            api_logger.warning(f"未找到指定的消息: message_id={message_id}, session_id={session_id}")
            return 0
        
        # 删除该时间之后创建的消息
        result = await db.execute(
            delete(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.created_at > target_message_time
            )
        )
        
        await db.commit()
        return result.rowcount
    except Exception as e:
        api_logger.error(f"软删除消息失败: {e}")
        await db.rollback()
        return 0


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


async def update_message_content(db: AsyncSession, message_id: int, new_content: str) -> bool:
    """
    更新指定消息的内容
    
    Args:
        db: 数据库会话
        message_id: 消息ID
        new_content: 新的消息内容
        
    Returns:
        是否更新成功
    """
    try:
        # 使用update语句直接更新消息内容
        result = await db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == message_id)
            .values(content=new_content)
        )
        
        if result.rowcount > 0:
            await db.commit()
            api_logger.info(f"消息内容更新成功: message_id={message_id}, new_content_length={len(new_content)}")
            return True
        else:
            api_logger.warning(f"未找到要更新的消息: message_id={message_id}")
            return False
            
    except Exception as e:
        api_logger.error(f"更新消息内容失败: message_id={message_id}, error={e}")
        await db.rollback()
        return False 