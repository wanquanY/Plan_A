from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any

from backend.models.chat import Chat, ChatMessage
from backend.utils.logging import db_logger, api_logger
from backend.services.title_generator import generate_title_with_ai
from backend.models.note import Note
from backend.utils.id_converter import IDConverter


async def create_chat(db: AsyncSession, user_id: int, chat_data=None, title: Optional[str] = None, agent_id: Optional[str] = None) -> Chat:
    """创建一个新的聊天会话
    
    Args:
        db: 数据库会话
        user_id: 用户ID（数据库内部ID）
        chat_data: ChatCreate模型数据（优先使用）
        title: 标题 (如果没有提供chat_data则使用此参数)
        agent_id: 代理public_id (如果没有提供chat_data则使用此参数)
    """
    db_logger.info(f"创建新聊天会话: user_id={user_id}")
    
    # 如果提供了chat_data，使用其中的数据
    if chat_data:
        chat_title = chat_data.title or "新对话"
        chat_agent_public_id = getattr(chat_data, "agent_id", None)
    else:
        chat_title = title or "新对话"
        chat_agent_public_id = agent_id
    
    # 如果提供了agent_id（public_id），转换为数据库内部ID
    db_agent_id = None
    if chat_agent_public_id:
        db_agent_id = await IDConverter.get_agent_db_id(db, chat_agent_public_id)
    
    db_logger.info(f"创建新聊天会话: user_id={user_id}, agent_public_id={chat_agent_public_id}, db_agent_id={db_agent_id}")
    
    chat = Chat(user_id=user_id, title=chat_title, agent_id=db_agent_id)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    db_logger.info(f"聊天会话创建成功: id={chat.id}, public_id={chat.public_id}")
    return chat


async def get_chat(db: AsyncSession, session_id: str) -> Optional[Chat]:
    """
    根据public_id获取指定的聊天会话
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        
    Returns:
        Chat对象或None
    """
    try:
        # 转换public_id为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        if not db_session_id:
            return None
            
        result = await db.execute(
            select(Chat).where(Chat.id == db_session_id, Chat.is_active == True)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        api_logger.error(f"获取聊天会话失败: {e}")
        return None


async def get_user_chats(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> tuple[List[Chat], int]:
    """获取用户的所有聊天会话，不自动加载messages以避免异步加载问题
    
    Args:
        db: 数据库会话
        user_id: 用户ID（数据库内部ID）
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


async def update_chat_title(db: AsyncSession, session_id: str, title: str) -> Optional[Chat]:
    """
    更新聊天会话标题
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
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


async def update_chat_agent(db: AsyncSession, session_id: str, agent_id: str) -> Optional[Chat]:
    """
    更新聊天会话关联的Agent
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        agent_id: Agent public_id
        
    Returns:
        更新后的Chat对象或None
    """
    try:
        chat = await get_chat(db, session_id)
        if chat:
            # 转换agent_id为数据库内部ID
            db_agent_id = await IDConverter.get_agent_db_id(db, agent_id)
            if db_agent_id:
                chat.agent_id = db_agent_id
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
    session_id: str,  # 改为public_id
    role: str, 
    content: str,
    tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    agent_id: Optional[str] = None,  # 改为public_id
) -> Optional[ChatMessage]:
    """
    添加聊天消息到数据库
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        role: 消息角色（user, assistant, system）
        content: 消息内容
        tokens: 消息token数量
        prompt_tokens: 提示词token数量
        total_tokens: 总token数量
        agent_id: Agent public_id
        
    Returns:
        创建的ChatMessage对象或None
    """
    try:
        # 转换session_id为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        if not db_session_id:
            api_logger.error(f"无法找到会话: {session_id}")
            return None
        
        # 转换agent_id为数据库内部ID（如果提供）
        db_agent_id = None
        if agent_id:
            db_agent_id = await IDConverter.get_agent_db_id(db, agent_id)
        
        message = ChatMessage(
            session_id=db_session_id,
            role=role,
            content=content,
            tokens=tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            agent_id=db_agent_id
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    except Exception as e:
        api_logger.error(f"添加消息失败: {e}")
        await db.rollback()
        return None


async def get_chat_messages(db: AsyncSession, session_id: str) -> List[ChatMessage]:
    """
    获取聊天会话的所有消息
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        
    Returns:
        消息列表
    """
    try:
        # 转换session_id为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        if not db_session_id:
            return []
        
        query = select(ChatMessage).where(
            and_(
                ChatMessage.session_id == db_session_id,
                ChatMessage.is_deleted == False
            )
        ).order_by(ChatMessage.created_at.asc())
        
        result = await db.execute(query)
        messages = result.scalars().all()
        return list(messages)
    except Exception as e:
        api_logger.error(f"获取聊天消息失败: {e}")
        return []


async def soft_delete_chat(db: AsyncSession, session_id: str) -> bool:
    """
    软删除聊天会话
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        
    Returns:
        删除是否成功
    """
    try:
        # 转换session_id为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        if not db_session_id:
            return False
            
        # 更新聊天会话为已删除状态
        stmt = update(Chat).where(Chat.id == db_session_id).values(is_deleted=True)
        await db.execute(stmt)
        
        # 同时软删除所有相关消息
        msg_stmt = update(ChatMessage).where(ChatMessage.session_id == db_session_id).values(is_deleted=True)
        await db.execute(msg_stmt)
        
        await db.commit()
        return True
    except Exception as e:
        api_logger.error(f"软删除聊天会话失败: {e}")
        await db.rollback()
        return False


async def soft_delete_messages_after(db: AsyncSession, session_id: str, message_id: str) -> int:
    """
    软删除指定消息之后的所有消息
    
    Args:
        db: 数据库会话
        session_id: 会话public_id
        message_id: 消息public_id
        
    Returns:
        删除的消息数量
    """
    try:
        # 转换ID为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        db_message_id = await IDConverter.get_message_db_id(db, message_id)
        
        if not db_session_id or not db_message_id:
            return 0
        
        # 获取指定消息的创建时间
        message_query = select(ChatMessage.created_at).where(ChatMessage.id == db_message_id)
        message_result = await db.execute(message_query)
        message_time = message_result.scalar_one_or_none()
        
        if not message_time:
            return 0
        
        # 软删除该时间之后的所有消息
        stmt = update(ChatMessage).where(
            and_(
                ChatMessage.session_id == db_session_id,
                ChatMessage.created_at > message_time,
                ChatMessage.is_deleted == False
            )
        ).values(is_deleted=True)
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    except Exception as e:
        api_logger.error(f"软删除消息失败: {e}")
        await db.rollback()
        return 0


async def get_latest_chat(db: AsyncSession, user_id: int) -> Optional[Chat]:
    """
    获取用户最新的聊天会话
    
    Args:
        db: 数据库会话
        user_id: 用户ID（数据库内部ID）
        
    Returns:
        最新的Chat对象或None
    """
    try:
        query = select(Chat).where(
            and_(Chat.user_id == user_id, Chat.is_deleted == False)
        ).order_by(Chat.updated_at.desc()).limit(1)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except Exception as e:
        api_logger.error(f"获取最新聊天会话失败: {e}")
        return None


async def update_message_content(db: AsyncSession, message_id: str, new_content: str) -> bool:
    """
    更新消息内容
    
    Args:
        db: 数据库会话
        message_id: 消息public_id
        new_content: 新内容
        
    Returns:
        更新是否成功
    """
    try:
        # 转换message_id为数据库内部ID
        db_message_id = await IDConverter.get_message_db_id(db, message_id)
        if not db_message_id:
            return False
            
        stmt = update(ChatMessage).where(ChatMessage.id == db_message_id).values(content=new_content)
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount > 0
    except Exception as e:
        api_logger.error(f"更新消息内容失败: {e}")
        await db.rollback()
        return False 