from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from backend.crud.note_session import note_session
from backend.crud.chat import get_chat_messages, get_chat
from backend.utils.id_converter import IDConverter

router = APIRouter()


@router.post("/")
async def create_note(
    request: Request,
    note_data: NoteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """创建新笔记"""
    try:
        # 创建新笔记，不再自动创建会话
        new_note = Note(
            user_id=current_user.id,
            title=note_data.title if note_data.title is not None else "",  # 如果标题为None则设为空字符串，不再使用默认标题
            content=note_data.content or "",
            is_public=note_data.is_public or False
        )
        db.add(new_note)
        await db.commit()
        await db.refresh(new_note)
        
        return SuccessResponse(
            data={
                "note_id": new_note.public_id,
                "title": new_note.title,
                "session_id": None  # 新创建的笔记没有关联会话
            },
            msg="笔记创建成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建笔记失败: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建笔记时发生错误: {str(e)}")


@router.get("/")
async def get_notes(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的笔记列表 - 性能优化版本"""
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
        
        # 🚀 性能优化：批量获取所有需要的会话ID
        all_note_ids = [note.id for note in notes]
        primary_sessions = await note_session.batch_get_primary_sessions_by_notes(db, all_note_ids)
        
        # 🚀 批量转换会话ID为public_id
        session_db_ids = [ps.id for ps in primary_sessions.values() if ps]
        session_id_map = await IDConverter.batch_get_public_ids(db, session_db_ids, Chat)
        
        # 构建响应列表
        notes_list = []
        for note in notes:
            # 获取主要会话ID（已优化为批量查询）
            primary_session = primary_sessions.get(note.id)
            session_id = session_id_map.get(primary_session.id) if primary_session else None
            
            notes_list.append({
                "id": note.public_id,
                "title": note.title,
                "session_id": session_id,
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
            msg="获取笔记列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取笔记列表时发生错误: {str(e)}")


@router.get("/{note_id}")
async def get_note(
    request: Request,
    note_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取笔记详情"""
    try:
        # 验证笔记存在性
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除", request_id=getattr(request.state, "request_id", None))
        
        # 获取笔记的主要会话
        primary_session = await note_session.get_primary_session_by_note(db, note_id)
        session_id = primary_session.public_id if primary_session else None
        
        # 如果笔记关联了会话，尝试恢复会话记忆到Redis
        if primary_session:
            try:
                # 获取会话记忆当前状态（memory_service已支持public_id）
                memory_messages = memory_service.get_messages(primary_session.public_id)
                
                # 如果Redis中没有该会话的记忆，则尝试从数据库恢复
                if not memory_messages:
                    api_logger.info(f"笔记 {note_id} 关联的会话 {primary_session.public_id} 在Redis中没有记忆，尝试恢复")
                    
                    # 获取会话历史消息（get_chat_messages已支持public_id）
                    db_messages = await get_chat_messages(db, primary_session.public_id)
                    
                    # 格式化消息并恢复到Redis
                    formatted_messages = [
                        {"role": msg.role, "content": msg.content}
                        for msg in db_messages
                        if not msg.is_deleted
                    ]
                    
                    # 恢复记忆，传递用户ID进行管理（memory_service已支持public_id）
                    restored = memory_service.restore_memory_from_db(primary_session.public_id, formatted_messages, current_user.id)
                    if restored:
                        api_logger.info(f"已自动恢复笔记 {note_id} 关联的会话 {primary_session.public_id} 记忆，共 {len(formatted_messages)} 条消息")
                    else:
                        api_logger.warning(f"笔记 {note_id} 关联的会话 {primary_session.public_id} 没有可恢复的历史消息")
            except Exception as e:
                # 恢复记忆失败不影响笔记获取
                api_logger.error(f"自动恢复笔记 {note_id} 关联的会话 {primary_session.public_id} 记忆失败: {str(e)}", exc_info=True)
        
        # 获取所有关联的会话（note_session已支持public_id）
        sessions = await note_session.get_sessions_by_note(db, note_id)
        primary_session = await note_session.get_primary_session_by_note(db, note_id)
        
        session_list = []
        for session in sessions:
            # 获取会话的消息数量和最后一条消息（get_chat_messages已支持public_id）
            messages = await get_chat_messages(db, session.public_id)
            message_count = len(messages) if messages else 0
            
            # 获取最后一条消息内容
            last_message = None
            if message_count > 0:
                # 直接使用完整的消息内容，不进行截断
                last_message = messages[-1].content if messages[-1].content else None
            
            # 安全地获取agent_id，避免懒加载问题
            agent_public_id = None
            if session.agent_id:
                agent_public_id = await IDConverter.get_agent_public_id(db, session.agent_id)
            
            session_info = {
                "id": session.public_id,
                "title": session.title,
                "is_primary": session.id == (primary_session.id if primary_session else None),
                "agent_id": agent_public_id,
                "message_count": message_count,
                "last_message": last_message,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None
            }
            session_list.append(session_info)
        
        return SuccessResponse(
            data={
                "id": note.public_id,
                "user_id": note.user.public_id if note.user else None,
                "title": note.title,
                "content": note.content,
                "session_id": session_id,
                "last_edited_position": note.last_edited_position,
                "is_public": note.is_public,
                "share_link": note.share_link,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                "sessions": session_list
            },
            msg="获取笔记详情成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取笔记详情时发生错误: {str(e)}")


@router.put("/{note_id}")
async def update_note(
    request: Request,
    note_id: str,
    note_data: NoteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新笔记"""
    try:
        # 验证笔记存在性
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除", request_id=getattr(request.state, "request_id", None))
        
        # 更新笔记字段
        if note_data.title is not None:
            note.title = note_data.title
        if note_data.content is not None:
            note.content = note_data.content
        if note_data.last_edited_position is not None:
            note.last_edited_position = note_data.last_edited_position
        if note_data.is_public is not None:
            note.is_public = note_data.is_public
        
        await db.commit()
        await db.refresh(note)
        
        return SuccessResponse(
            data={
                "id": note.public_id,
                "title": note.title,
                "content": note.content,
                "last_edited_position": note.last_edited_position,
                "is_public": note.is_public,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            },
            msg="笔记更新成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新笔记时发生错误: {str(e)}")


@router.delete("/{note_id}")
async def delete_note(
    request: Request,
    note_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """删除笔记"""
    try:
        # 验证笔记存在性
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除", request_id=getattr(request.state, "request_id", None))
        
        # 软删除笔记
        note.is_deleted = True
        await db.commit()
        
        return SuccessResponse(
            data={"deleted_note_id": note.public_id},
            msg="笔记删除成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除笔记时发生错误: {str(e)}")


@router.post("/{note_id}/edit")
async def edit_note_by_agent(
    request: Request,
    note_id: str,
    edit_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Agent编辑笔记内容的专用端点"""
    try:
        # 将public_id转换为数据库ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记存在且属于当前用户
        stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除", request_id=getattr(request.state, "request_id", None))
        
        # 获取编辑参数
        edit_type = edit_data.get("edit_type", "replace")
        content = edit_data.get("content")
        title = edit_data.get("title")
        start_line = edit_data.get("start_line")
        end_line = edit_data.get("end_line")
        insert_position = edit_data.get("insert_position")
        search_text = edit_data.get("search_text")
        replace_text = edit_data.get("replace_text")
        
        # 记录编辑前的状态
        original_content = note.content or ""
        original_title = note.title or ""
        
        # 执行编辑操作
        new_content = original_content
        new_title = title if title is not None else original_title
        
        if edit_type == "replace":
            # 完全替换内容
            if content is not None:
                new_content = content
                
        elif edit_type == "append":
            # 追加内容
            if content is not None:
                new_content = original_content + "\n" + content if original_content else content
                
        elif edit_type == "prepend":
            # 前置内容
            if content is not None:
                new_content = content + "\n" + original_content if original_content else content
                
        elif edit_type == "insert":
            # 在指定位置插入内容
            if content is not None and insert_position:
                lines = original_content.split('\n')
                
                if insert_position == "start":
                    new_content = content + "\n" + original_content if original_content else content
                elif insert_position == "end":
                    new_content = original_content + "\n" + content if original_content else content
                elif insert_position.startswith("after_line:"):
                    try:
                        line_num = int(insert_position.split(":")[1])
                        if 0 <= line_num <= len(lines):
                            lines.insert(line_num, content)
                            new_content = '\n'.join(lines)
                        else:
                            return ErrorResponse(msg=f"行号 {line_num} 超出范围", request_id=getattr(request.state, "request_id", None))
                    except ValueError:
                        return ErrorResponse(msg="无效的行号格式", request_id=getattr(request.state, "request_id", None))
                elif insert_position.startswith("before_line:"):
                    try:
                        line_num = int(insert_position.split(":")[1])
                        if 1 <= line_num <= len(lines) + 1:
                            lines.insert(line_num - 1, content)
                            new_content = '\n'.join(lines)
                        else:
                            return ErrorResponse(msg=f"行号 {line_num} 超出范围", request_id=getattr(request.state, "request_id", None))
                    except ValueError:
                        return ErrorResponse(msg="无效的行号格式", request_id=getattr(request.state, "request_id", None))
                else:
                    return ErrorResponse(msg="无效的插入位置格式", request_id=getattr(request.state, "request_id", None))
                    
        elif edit_type == "replace_lines":
            # 替换指定行范围
            if content is not None and start_line is not None:
                lines = original_content.split('\n')
                end_line_actual = end_line if end_line is not None else start_line
                
                if 1 <= start_line <= len(lines) and 1 <= end_line_actual <= len(lines):
                    # 替换指定行范围
                    new_lines = content.split('\n')
                    lines[start_line-1:end_line_actual] = new_lines
                    new_content = '\n'.join(lines)
                else:
                    return ErrorResponse(msg=f"行号范围 {start_line}-{end_line_actual} 超出范围", request_id=getattr(request.state, "request_id", None))
                    
        elif edit_type == "replace_text":
            # 替换指定文本
            if search_text is not None and replace_text is not None:
                if search_text in original_content:
                    new_content = original_content.replace(search_text, replace_text)
                else:
                    return ErrorResponse(msg=f"未找到要替换的文本: {search_text}", request_id=getattr(request.state, "request_id", None))
            else:
                return ErrorResponse(msg="replace_text 类型需要提供 search_text 和 replace_text 参数", request_id=getattr(request.state, "request_id", None))
        else:
            return ErrorResponse(msg=f"不支持的编辑类型: {edit_type}", request_id=getattr(request.state, "request_id", None))
        
        # 更新笔记
        note.content = new_content
        note.title = new_title
        
        await db.commit()
        await db.refresh(note)
        
        # 计算变化统计
        original_lines = original_content.split('\n')
        new_lines = new_content.split('\n')
        
        return SuccessResponse(
            data={
                "note_id": note.public_id,
                "title": note.title,
                "edit_type": edit_type,
                "changes": {
                    "original_length": len(original_content),
                    "new_length": len(new_content),
                    "original_lines": len(original_lines),
                    "new_lines": len(new_lines),
                    "title_changed": original_title != new_title
                },
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                "content": new_content  # 返回完整的新内容供前端更新
            },
            msg="笔记编辑成功",
            request_id=getattr(request.state, "request_id", None)
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"编辑笔记时发生错误: {str(e)}")


@router.post("/{note_id}/apply-edit")
async def apply_edit_preview(
    request: Request,
    note_id: str,
    edit_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """应用预览编辑到笔记"""
    try:
        # 将public_id转换为数据库ID
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记存在且属于当前用户
        stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或已删除", request_id=getattr(request.state, "request_id", None))
        
        # 应用编辑
        if edit_data.get("content") is not None:
            note.content = edit_data["content"]
        
        if edit_data.get("title") is not None:
            note.title = edit_data["title"]
        
        # 保存更改
        await db.commit()
        await db.refresh(note)
        
        api_logger.info(f"用户 {current_user.public_id} 应用预览编辑到笔记 {note_id}")
        
        return SuccessResponse(
            data={
                "id": note.public_id,
                "title": note.title,
                "content": note.content,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None
            },
            msg="编辑已应用并保存",
            request_id=getattr(request.state, "request_id", None)
        )
        
    except Exception as e:
        api_logger.error(f"应用预览编辑失败: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"应用编辑时发生错误: {str(e)}")


@router.post("/{note_id}/sessions/{session_id}/link")
async def link_note_to_session(
    request: Request,
    note_id: str,
    session_id: str,
    is_primary: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """将笔记关联到会话"""
    try:
        # 验证笔记和会话都存在且属于当前用户（暂时保留ID转换用于验证）
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        db_session_id = await IDConverter.get_chat_db_id(db, session_id)
        
        if not db_note_id or not db_session_id:
            return ErrorResponse(msg="笔记或会话不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记属于当前用户
        note_stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(note_stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或无权限", request_id=getattr(request.state, "request_id", None))
        
        # 验证会话属于当前用户（get_chat已支持public_id）
        session = await get_chat(db, session_id)
        if not session or session.user_id != current_user.id:
            return ErrorResponse(msg="会话不存在或无权限", request_id=getattr(request.state, "request_id", None))
        
        # 创建关联（note_session已支持public_id）
        await note_session.create_note_session_link(
            db,
            note_id=note_id,  # 直接使用public_id
            session_id=session_id,  # 直接使用public_id
            is_primary=is_primary
        )
        
        return SuccessResponse(
            data={
                "note_id": note_id,
                "session_id": session_id,
                "is_primary": is_primary
            },
            msg="关联创建成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建关联时发生错误: {str(e)}")


@router.delete("/{note_id}/sessions/{session_id}/unlink")
async def unlink_note_from_session(
    request: Request,
    note_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """取消笔记与会话的关联"""
    try:
        # 验证权限（暂时保留ID转换用于验证）
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记属于当前用户
        note_stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(note_stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或无权限", request_id=getattr(request.state, "request_id", None))
        
        # 移除关联（note_session已支持public_id）
        success = await note_session.remove_note_session_link(
            db,
            note_id=note_id,  # 直接使用public_id
            session_id=session_id  # 直接使用public_id
        )
        
        if success:
            return SuccessResponse(
                data={
                    "note_id": note_id,
                    "session_id": session_id
                },
                msg="关联已移除",
                request_id=getattr(request.state, "request_id", None)
            )
        else:
            return ErrorResponse(msg="关联不存在或移除失败", request_id=getattr(request.state, "request_id", None))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"移除关联时发生错误: {str(e)}")


@router.put("/{note_id}/sessions/{session_id}/set-primary")
async def set_primary_session(
    request: Request,
    note_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """设置笔记的主要会话"""
    try:
        # 验证权限（暂时保留ID转换用于验证）
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记属于当前用户
        note_stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(note_stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或无权限", request_id=getattr(request.state, "request_id", None))
        
        # 设置主要会话（note_session已支持public_id）
        success = await note_session.set_primary_session(
            db,
            note_id=note_id,  # 直接使用public_id
            session_id=session_id  # 直接使用public_id
        )
        
        if success:
            return SuccessResponse(
                data={
                    "note_id": note_id,
                    "session_id": session_id,
                    "is_primary": True
                },
                msg="主要会话设置成功",
                request_id=getattr(request.state, "request_id", None)
            )
        else:
            return ErrorResponse(msg="设置主要会话失败", request_id=getattr(request.state, "request_id", None))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"设置主要会话时发生错误: {str(e)}")


@router.get("/{note_id}/sessions")
async def get_note_sessions(
    request: Request,
    note_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """获取笔记的所有关联会话"""
    try:
        # 验证权限（暂时保留ID转换用于验证）
        db_note_id = await IDConverter.get_note_db_id(db, note_id)
        if not db_note_id:
            return ErrorResponse(msg="笔记不存在", request_id=getattr(request.state, "request_id", None))
        
        # 验证笔记属于当前用户
        note_stmt = select(Note).where(
            Note.id == db_note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(note_stmt)
        note = note_result.scalar_one_or_none()
        
        if not note:
            return ErrorResponse(msg="笔记不存在或无权限", request_id=getattr(request.state, "request_id", None))
        
        # 获取关联的会话（note_session已支持public_id）
        sessions = await note_session.get_sessions_by_note(db, note_id)
        primary_session = await note_session.get_primary_session_by_note(db, note_id)
        
        session_list = []
        for session in sessions:
            # 获取会话的消息数量和最后一条消息（get_chat_messages已支持public_id）
            messages = await get_chat_messages(db, session.public_id)
            message_count = len(messages) if messages else 0
            
            # 获取最后一条消息内容
            last_message = None
            if message_count > 0:
                last_message = messages[-1].content if messages[-1].content else None
            
            # 安全地获取agent_id
            agent_public_id = None
            if session.agent_id:
                agent_public_id = await IDConverter.get_agent_public_id(db, session.agent_id)
            
            session_info = {
                "id": session.public_id,
                "title": session.title,
                "is_primary": session.id == (primary_session.id if primary_session else None),
                "agent_id": agent_public_id,
                "message_count": message_count,
                "last_message": last_message,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None
            }
            session_list.append(session_info)
        
        return SuccessResponse(
            data={
                "note_id": note_id,
                "sessions": session_list
            },
            msg="获取笔记会话列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取笔记会话列表时发生错误: {str(e)}") 