from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from backend.models.note import Note
from backend.models.chat import Chat
from backend.models.note_session import NoteSession
from backend.utils.logging import db_logger
from backend.utils.id_converter import IDConverter


class NoteCRUD:
    async def create_note_session_link(
        self, 
        db: AsyncSession, 
        note_id: str,  # 改为使用public_id
        session_id: str,  # 改为使用public_id
        is_primary: bool = False
    ) -> NoteSession:
        """创建笔记和会话的关联"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        
        if not db_note_id or not db_session_id:
            raise ValueError(f"无效的ID: note_id={note_id}, session_id={session_id}")
        
        # 如果设置为主要会话，先将其他会话设为非主要
        if is_primary:
            await self.unset_primary_sessions(db, note_id)
        
        note_session = NoteSession(
            note_id=db_note_id,
            session_id=db_session_id,
            is_primary=is_primary
        )
        db.add(note_session)
        await db.commit()
        await db.refresh(note_session)
        
        db_logger.info(f"创建笔记会话关联: note_id={note_id}, session_id={session_id}, is_primary={is_primary}")
        return note_session
    
    async def get_sessions_by_note(self, db: AsyncSession, note_id: str) -> List[Chat]:
        """根据笔记public_id获取所有关联的会话"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return []
        
        # 查询关联的会话
        query = select(Chat).join(NoteSession).where(
            and_(
                NoteSession.note_id == db_note_id,
                NoteSession.is_deleted == False,
                Chat.is_deleted == False
            )
        ).options(selectinload(Chat.messages))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_notes_by_session(self, db: AsyncSession, session_id: str) -> List[Note]:
        """根据会话public_id获取所有关联的笔记"""
        # 转换public_id为数据库内部ID
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        if not db_session_id:
            return []
        
        # 查询关联的笔记
        query = select(Note).join(NoteSession).where(
            and_(
                NoteSession.session_id == db_session_id,
                NoteSession.is_deleted == False,
                Note.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_primary_session_by_note(self, db: AsyncSession, note_id: str) -> Optional[Chat]:
        """获取笔记的主要会话"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return None
        
        query = select(Chat).join(NoteSession).where(
            and_(
                NoteSession.note_id == db_note_id,
                NoteSession.is_primary == True,
                NoteSession.is_deleted == False,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def unset_primary_sessions(self, db: AsyncSession, note_id: str) -> None:
        """取消笔记的所有主要会话标记"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return
        
        stmt = update(NoteSession).where(
            and_(
                NoteSession.note_id == db_note_id,
                NoteSession.is_deleted == False
            )
        ).values(is_primary=False)
        
        await db.execute(stmt)
    
    async def remove_note_session_link(
        self, 
        db: AsyncSession,
        note_id: str,  # 改为使用public_id
        session_id: str  # 改为使用public_id
    ) -> bool:
        """移除笔记和会话的关联"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        
        if not db_note_id or not db_session_id:
            return False
        
        stmt = update(NoteSession).where(
            and_(
                NoteSession.note_id == db_note_id,
                NoteSession.session_id == db_session_id,
                NoteSession.is_deleted == False
            )
        ).values(is_deleted=True)
        
        result = await db.execute(stmt)
        await db.commit()
        
        db_logger.info(f"删除笔记会话关联: note_id={note_id}, session_id={session_id}")
        return result.rowcount > 0
    
    async def set_primary_session(
        self, 
        db: AsyncSession, 
        note_id: str,  # 改为使用public_id
        session_id: str  # 改为使用public_id
    ) -> bool:
        """设置笔记的主要会话"""
        # 转换public_id为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        
        if not db_note_id or not db_session_id:
            return False
        
        # 先取消其他主要会话
        await self.unset_primary_sessions(db, note_id)
        
        # 设置指定会话为主要会话
        stmt = update(NoteSession).where(
            and_(
                NoteSession.note_id == db_note_id,
                NoteSession.session_id == db_session_id,
                NoteSession.is_deleted == False
            )
        ).values(is_primary=True)
        
        result = await db.execute(stmt)
        await db.commit()
        
        db_logger.info(f"设置主要会话: note_id={note_id}, session_id={session_id}")
        return result.rowcount > 0

    async def batch_get_primary_sessions_by_notes(self, db: AsyncSession, note_db_ids: List[int]) -> dict:
        """批量获取多个笔记的主要会话"""
        if not note_db_ids:
            return {}
        
        # 一次性查询所有笔记的主要会话
        query = select(Chat, NoteSession.note_id).join(NoteSession).where(
            and_(
                NoteSession.note_id.in_(note_db_ids),
                NoteSession.is_primary == True,
                NoteSession.is_deleted == False,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # 构建映射：note_id -> Chat对象
        primary_sessions = {}
        for chat, note_id in rows:
            primary_sessions[note_id] = chat
        
        return primary_sessions


# 创建全局实例
note_session = NoteCRUD() 