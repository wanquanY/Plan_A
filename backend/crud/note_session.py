from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from backend.models.note_session import NoteSession
from backend.models.note import Note
from backend.models.chat import Chat
from backend.crud.base import CRUDBase


class CRUDNoteSession(CRUDBase[NoteSession, dict, dict]):
    
    async def create_note_session_link(
        self, 
        db: AsyncSession, 
        note_id: int, 
        session_id: int, 
        is_primary: bool = False
    ) -> NoteSession:
        """创建笔记-会话关联"""
        # 检查是否已经存在关联
        existing = await self.get_by_note_and_session(db, note_id, session_id)
        if existing:
            return existing
        
        # 如果设置为主要会话，先取消其他主要会话
        if is_primary:
            await self.unset_primary_sessions(db, note_id)
        
        note_session = NoteSession(
            note_id=note_id,
            session_id=session_id,
            is_primary=is_primary
        )
        db.add(note_session)
        await db.commit()
        await db.refresh(note_session)
        return note_session
    
    async def get_by_note_and_session(
        self, 
        db: AsyncSession, 
        note_id: int, 
        session_id: int
    ) -> Optional[NoteSession]:
        """根据笔记ID和会话ID获取关联"""
        stmt = select(NoteSession).where(
            and_(
                NoteSession.note_id == note_id,
                NoteSession.session_id == session_id,
                NoteSession.is_deleted == False
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_sessions_by_note(
        self, 
        db: AsyncSession, 
        note_id: int
    ) -> List[Chat]:
        """获取笔记的所有关联会话"""
        stmt = select(Chat).join(NoteSession).where(
            and_(
                NoteSession.note_id == note_id,
                NoteSession.is_deleted == False,
                Chat.is_deleted == False
            )
        ).order_by(NoteSession.is_primary.desc(), NoteSession.created_at.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_primary_session_by_note(
        self, 
        db: AsyncSession, 
        note_id: int
    ) -> Optional[Chat]:
        """获取笔记的主要会话"""
        stmt = select(Chat).join(NoteSession).where(
            and_(
                NoteSession.note_id == note_id,
                NoteSession.is_primary == True,
                NoteSession.is_deleted == False,
                Chat.is_deleted == False
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_notes_by_session(
        self, 
        db: AsyncSession, 
        session_id: int
    ) -> List[Note]:
        """获取会话的所有关联笔记"""
        stmt = select(Note).join(NoteSession).where(
            and_(
                NoteSession.session_id == session_id,
                NoteSession.is_deleted == False,
                Note.is_deleted == False
            )
        ).order_by(NoteSession.is_primary.desc(), NoteSession.created_at.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def unset_primary_sessions(self, db: AsyncSession, note_id: int) -> None:
        """取消笔记的所有主要会话标记"""
        stmt = select(NoteSession).where(
            and_(
                NoteSession.note_id == note_id,
                NoteSession.is_primary == True,
                NoteSession.is_deleted == False
            )
        )
        result = await db.execute(stmt)
        note_sessions = result.scalars().all()
        
        for ns in note_sessions:
            ns.is_primary = False
        
        await db.commit()
    
    async def set_primary_session(
        self, 
        db: AsyncSession, 
        note_id: int, 
        session_id: int
    ) -> bool:
        """设置笔记的主要会话"""
        # 先取消其他主要会话
        await self.unset_primary_sessions(db, note_id)
        
        # 设置新的主要会话
        note_session = await self.get_by_note_and_session(db, note_id, session_id)
        if note_session:
            note_session.is_primary = True
            await db.commit()
            return True
        return False
    
    async def remove_note_session_link(
        self, 
        db: AsyncSession, 
        note_id: int, 
        session_id: int
    ) -> bool:
        """删除笔记-会话关联（软删除）"""
        note_session = await self.get_by_note_and_session(db, note_id, session_id)
        if note_session:
            note_session.is_deleted = True
            await db.commit()
            return True
        return False


note_session = CRUDNoteSession(NoteSession) 