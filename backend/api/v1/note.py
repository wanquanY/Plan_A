from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from backend.db.session import get_db
from backend.api.deps import get_db as get_async_db, get_current_user
from backend.models.user import User
from backend.models.note import Note
from backend.models.chat import Chat
from backend.schemas.note import NoteCreate, NoteUpdate, NoteResponse, NoteList
from backend.core.response import SuccessResponse, ErrorResponse
from backend.services.memory import memory_service
from backend.services.chat import get_chat_messages
from backend.utils.logging import api_logger

router = APIRouter()


@router.post("/")
async def create_note(
    note_data: NoteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """创建新笔记"""
    try:
        # 创建新笔记，不再自动创建会话
        new_note = Note(
            user_id=current_user.id,
            session_id=None,  # 初始没有关联会话，只有通过@agent交互后才会创建会话
            title=note_data.title if note_data.title is not None else "",  # 如果标题为None则设为空字符串，不再使用默认标题
            content=note_data.content or "",
            is_public=note_data.is_public or False
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)
        
        return SuccessResponse(
            data={
                "note_id": new_note.id,
                "title": new_note.title,
                "session_id": new_note.session_id
            },
            msg="笔记创建成功"
        )
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建笔记失败: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建笔记时发生错误: {str(e)}")


@router.get("/")
async def get_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的笔记列表"""
    try:
        # 获取用户笔记总数
        count_stmt = select(func.count()).select_from(Note).where(
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # 获取分页的笔记列表
        stmt = select(Note).where(
            Note.user_id == current_user.id,
            Note.is_deleted == False
        ).order_by(Note.updated_at.desc()).offset(skip).limit(limit)
        
        notes_result = await db.execute(stmt)
        notes = notes_result.scalars().all()
        
        notes_list = []
        for note in notes:
            notes_list.append({
                "id": note.id,
                "title": note.title,
                "session_id": note.session_id,
                "is_public": note.is_public,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            })
        
        return SuccessResponse(
            data={
                "notes": notes_list,
                "total": total,
                "skip": skip,
                "limit": limit
            },
            msg="获取笔记列表成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取笔记列表时发生错误: {str(e)}")


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取笔记详情"""
    try:
        stmt = select(Note).where(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除")
        
        # 如果笔记关联了会话，尝试恢复会话记忆到Redis
        if note.session_id:
            try:
                # 获取会话记忆当前状态
                memory_messages = memory_service.get_messages(note.session_id)
                
                # 如果Redis中没有该会话的记忆，则尝试从数据库恢复
                if not memory_messages:
                    api_logger.info(f"笔记 {note_id} 关联的会话 {note.session_id} 在Redis中没有记忆，尝试恢复")
                    
                    # 获取会话历史消息
                    db_messages = await get_chat_messages(db, note.session_id)
                    
                    # 格式化消息并恢复到Redis
                    formatted_messages = [
                        {"role": msg.role, "content": msg.content}
                        for msg in db_messages
                        if not msg.is_deleted
                    ]
                    
                    # 恢复记忆，传递用户ID进行管理
                    restored = memory_service.restore_memory_from_db(note.session_id, formatted_messages, current_user.id)
                    if restored:
                        api_logger.info(f"已自动恢复笔记 {note_id} 关联的会话 {note.session_id} 记忆，共 {len(formatted_messages)} 条消息")
                    else:
                        api_logger.warning(f"笔记 {note_id} 关联的会话 {note.session_id} 没有可恢复的历史消息")
            except Exception as e:
                # 恢复记忆失败不影响笔记获取
                api_logger.error(f"自动恢复笔记 {note_id} 关联的会话 {note.session_id} 记忆失败: {str(e)}", exc_info=True)
        
        return SuccessResponse(
            data={
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "session_id": note.session_id,
                "is_public": note.is_public,
                "last_edited_position": note.last_edited_position,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            },
            msg="获取笔记详情成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取笔记详情时发生错误: {str(e)}")


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新笔记内容"""
    try:
        stmt = select(Note).where(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除")
        
        # 更新笔记字段
        if note_data.title is not None:
            note.title = note_data.title
        
        if note_data.content is not None:
            note.content = note_data.content
        
        if note_data.is_public is not None:
            note.is_public = note_data.is_public
        
        if note_data.last_edited_position is not None:
            note.last_edited_position = note_data.last_edited_position
        
        await db.commit()
        await db.refresh(note)
        
        return SuccessResponse(
            data={
                "id": note.id,
                "title": note.title,
                "session_id": note.session_id,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            },
            msg="笔记更新成功"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新笔记时发生错误: {str(e)}")


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """删除笔记"""
    try:
        stmt = select(Note).where(
            Note.id == note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除")
        
        # 软删除笔记
        note.soft_delete()
        await db.commit()
        
        return SuccessResponse(msg="笔记删除成功")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除笔记时发生错误: {str(e)}") 