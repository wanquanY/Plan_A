from fastapi import APIRouter, Request, Depends, BackgroundTasks, Body, Path, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from backend.schemas.chat import (
    ChatRequest, ChatCompletionResponse, ChatCreate, ChatUpdate, 
    ChatResponse as ChatResponseModel, ChatListResponse, AskAgainRequest, 
    ChatMessageResponse
)
from backend.api.deps import get_db, get_current_active_user, get_current_user
from backend.models.user import User
from backend.services.chat import (
    generate_chat_response, generate_chat_stream, get_chat_history, 
    clear_memory, truncate_memory_after_message, replace_message_and_truncate
)
from backend.crud.chat import (
    get_user_chats, get_chat, create_chat, update_chat_title, 
    soft_delete_chat, get_chat_messages, get_latest_chat, soft_delete_messages_after, add_message, update_message_content
)
from backend.crud.note_session import note_session
from backend.core.response import SuccessResponse
from backend.utils.logging import api_logger
from backend.core.config import settings
from backend.utils.id_converter import IDConverter

from openai import AsyncOpenAI
from backend.services.memory import redis_client, memory_service
from backend.schemas.common import PaginationParams, PaginationResponse

router = APIRouter()


@router.post("/chat", response_model=ChatCompletionResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    聊天接口，调用AI模型生成回复
    """
    api_logger.info(f"用户请求聊天: {current_user.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    # 特殊处理：如果session_id为0，视为创建新会话
    if chat_request.session_id == 0:
        api_logger.info(f"用户请求创建新会话: {current_user.username}")
        chat_request.session_id = None
        
        # 如果提供了note_id，检查笔记是否存在
        if chat_request.note_id:
            from backend.models.note import Note
            from sqlalchemy import select
            
            # 将note_id转换为数据库内部ID进行验证
            db_note_id = await IDConverter.get_note_db_id(db, chat_request.note_id)
            if db_note_id:
                # 查询笔记是否存在
                stmt = select(Note).where(
                    Note.id == db_note_id,
                    Note.user_id == current_user.id,
                    Note.is_deleted == False
                )
                note_result = await db.execute(stmt)
                note = note_result.scalar_one_or_none()
                
                if note:
                    api_logger.info(f"将新会话关联到笔记ID: {chat_request.note_id}")
    
    # 如果请求开启流式响应，转发到流式API
    if chat_request.stream:
        return await stream_chat(request, chat_request, db, current_user)
    
    # 获取Agent信息（现在CRUD已支持public_id）
    agent_id = chat_request.agent_id
    agent_info = None
    
    if agent_id and db:
        from backend.crud.agent import agent as agent_crud
        agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
        if agent:
            # 🔧 修复：优先使用请求中指定的模型，如果没有则使用Agent的默认模型
            actual_model = chat_request.model if chat_request.model else agent.model
            agent_info = {
                "id": agent.public_id,  # 使用public_id
                "name": "AI助手",  # 使用默认显示名称
                "avatar_url": None,  # 移除avatar_url字段访问
                "model": actual_model  # 使用实际使用的模型
            }
    
    # 调用服务生成回复，并保存对话记录
    response = await generate_chat_response(
        chat_request=chat_request,
        db=db,
        user_id=current_user.id
    )
    
    # 如果是新创建的会话，并且存在笔记ID，将会话关联到笔记
    if chat_request.note_id and response.session_id:
        from backend.models.note import Note
        
        # 将note_id转换为数据库内部ID
        db_note_id = await IDConverter.get_note_db_id(db, chat_request.note_id)
        
        if db_note_id:
            # 验证笔记存在且属于当前用户
            note_stmt = select(Note).where(
                Note.id == db_note_id,
                Note.user_id == current_user.id,
                Note.is_deleted == False
            )
            note_result = await db.execute(note_stmt)
            note = note_result.scalar_one_or_none()
            
            if note:
                # 使用新的多对多关联方式（note_session已支持public_id）
                # 检查是否已有主要会话，如果没有则设为主要会话
                existing_primary = await note_session.get_primary_session_by_note(db, chat_request.note_id)
                is_primary = existing_primary is None  # 如果没有主要会话，这个就是主要会话
                
                await note_session.create_note_session_link(
                    db, 
                    note_id=chat_request.note_id,  # 现在直接使用public_id
                    session_id=response.session_id,  # 现在直接使用public_id
                    is_primary=is_primary
                )
                
                api_logger.info(f"笔记ID {chat_request.note_id} 已关联到会话ID {response.session_id}，是否为主要会话: {is_primary}")
                
                # 验证关联是否真的被创建
                verification_sessions = await note_session.get_sessions_by_note(db, chat_request.note_id)
                verification_session_ids = [s.public_id for s in verification_sessions]  # 使用public_id
                api_logger.info(f"验证笔记 {chat_request.note_id} 关联的会话列表: {verification_session_ids}")
                
                if response.session_id in verification_session_ids:
                    api_logger.info(f"✅ 笔记 {chat_request.note_id} 与会话 {response.session_id} 关联创建成功")
                else:
                    api_logger.error(f"❌ 笔记 {chat_request.note_id} 与会话 {response.session_id} 关联创建失败！")
            else:
                api_logger.warning(f"笔记ID {chat_request.note_id} 不存在或不属于用户 {current_user.public_id}")
        else:
            api_logger.error(f"无法转换笔记ID: {chat_request.note_id}")
    
    api_logger.info(f"聊天请求完成: {current_user.username}, 会话ID: {response.session_id}")
    
    # 将Pydantic模型转换为dict，确保可JSON序列化
    response_dict = {
        "message": {
            "content": response.message.content
        },
        "usage": response.usage,
        "session_id": response.session_id,
        "agent_id": agent_id,
        "agent_info": agent_info
    }
    
    return SuccessResponse(
        data=response_dict,
        msg="聊天成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/clear-memory/{session_id}")
async def clear_chat_memory(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    清空聊天会话的记忆
    """
    api_logger.info(f"清空聊天记忆: {current_user.username}, 会话ID: {session_id}")
    
    try:
        # 验证会话是否属于当前用户（get_chat现在支持public_id）
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在或无权访问"
            )
        
        # 清空记忆（memory_service现在支持public_id）
        await clear_memory(session_id)
        
        return SuccessResponse(
            data={"session_id": session_id},
            msg="记忆已清空",
            request_id=getattr(request.state, "request_id", None)
        )
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"清空记忆失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清空记忆失败"
        )


@router.get("/sessions")
async def list_chat_sessions(
    request: Request,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取用户的聊天会话列表
    """
    api_logger.info(f"获取聊天会话列表: {current_user.username}, 页码: {page}")
    
    try:
        skip = (page - 1) * page_size
        chats, total = await get_user_chats(db, current_user.id, skip=skip, limit=page_size)
        
        # 转换为响应格式（直接使用public_id）
        chat_list = []
        for chat in chats:
            # 获取消息数量
            messages = await get_chat_messages(db, chat.public_id)  # 直接使用public_id
            message_count = len(messages)
            
            # 获取最后一条消息
            last_message = None
            if messages:
                last_message = messages[-1].content[:50] + "..." if len(messages[-1].content) > 50 else messages[-1].content
            
            # 转换Agent ID为public_id（仍需要转换，因为数据库存储的是内部ID）
            agent_public_id = None
            if chat.agent_id:
                agent_public_id = await IDConverter.get_agent_public_id(db, chat.agent_id)
            
            chat_public_id = chat.public_id
            
            chat_list.append({
                "id": chat_public_id,
                "title": chat.title,
                "agent_id": agent_public_id,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "message_count": message_count,
                "last_message": last_message
            })
        
        # 转换总页数
        total_pages = (total + page_size - 1) // page_size
        
        return SuccessResponse(
            data={
                "chats": chat_list,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages
                }
            },
            msg="获取聊天会话列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"获取聊天会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取聊天会话列表失败"
        )


@router.get("/sessions/{session_id}", response_model=ChatResponseModel)
async def get_chat_session(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取指定的聊天会话详情
    """
    api_logger.info(f"获取聊天会话详情: {current_user.username}, 会话ID: {session_id}")
    
    try:
        # 获取会话（get_chat现在支持public_id）
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="聊天会话不存在或无权访问"
            )
        
        # 获取会话消息（get_chat_messages现在支持public_id）
        messages = await get_chat_messages(db, session_id)
        
        # 转换消息为响应格式
        message_list = []
        for msg in messages:
            # 转换消息和Agent ID为public_id
            msg_public_id = await IDConverter.get_message_public_id(db, msg.id)
            agent_public_id = None
            if msg.agent_id:
                agent_public_id = await IDConverter.get_agent_public_id(db, msg.agent_id)
            
            message_list.append({
                "id": msg_public_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "updated_at": msg.updated_at.isoformat() if msg.updated_at else None,
                "tokens": msg.tokens,
                "prompt_tokens": msg.prompt_tokens,
                "total_tokens": msg.total_tokens,
                "agent_id": agent_public_id
            })
        
        # 转换会话信息为响应格式
        chat_public_id = chat.public_id
        user_public_id = await IDConverter.get_user_public_id(db, chat.user_id)
        agent_public_id = None
        if chat.agent_id:
            agent_public_id = await IDConverter.get_agent_public_id(db, chat.agent_id)
        
        return SuccessResponse(
            data={
                "id": chat_public_id,
                "user_id": user_public_id,
                "agent_id": agent_public_id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "messages": message_list,
                "is_active": chat.is_active
            },
            msg="获取聊天会话成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"获取聊天会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取聊天会话失败"
        )


@router.get("/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history_endpoint(
    session_id: str,  # 已修复为str类型
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取聊天历史记录"""
    api_logger.info(f"获取聊天历史: session_id={session_id}, user_id={current_user.public_id}")
    
    # 验证会话存在且属于当前用户（get_chat现在支持public_id）
    chat = await get_chat(db, session_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="聊天会话不存在或无权访问"
        )
    
    # 获取聊天消息（get_chat_messages现在支持public_id）
    messages = await get_chat_messages(db, session_id)
    
    # 为每个消息加载工具调用信息
    from backend.crud.tool_call import get_tool_calls_by_message
    
    result = []
    for msg in messages:
        # 获取消息的工具调用记录
        tool_calls = await get_tool_calls_by_message(db, msg.id)
        
        # 转换消息ID为public_id
        msg_public_id = await IDConverter.get_message_public_id(db, msg.id)
        agent_public_id = await IDConverter.get_agent_public_id(db, msg.agent_id) if msg.agent_id else None
        
        # 转换为响应格式
        message_data = {
            "id": msg_public_id,  # 使用public_id
            "role": msg.role,
            "content": msg.content,
            "tokens": msg.tokens,
            "prompt_tokens": msg.prompt_tokens,
            "total_tokens": msg.total_tokens,
            "agent_id": agent_public_id,  # 使用public_id
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
            "tool_calls": [
                {
                    "id": tc.public_id,  # 工具调用也使用public_id
                    "tool_call_id": tc.tool_call_id,
                    "tool_name": tc.tool_name,
                    "function_name": tc.function_name,
                    "arguments": tc.arguments,
                    "status": tc.status,
                    "result": tc.result,
                    "error_message": tc.error_message,
                    "started_at": tc.started_at,
                    "completed_at": tc.completed_at
                } for tc in tool_calls
            ]
        }
        result.append(message_data)
    
    return result


@router.post("/stop-and-save")
async def stop_and_save_response(
    request: Request,
    stop_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    停止Agent响应并保存当前已生成的内容
    """
    request_id = str(uuid.uuid4())
    api_logger.info(f"收到停止并保存响应请求: {stop_request}, request_id={request_id}")
    
    try:
        session_id = stop_request.get("session_id")
        current_content = stop_request.get("current_content", "")
        user_content = stop_request.get("user_content", "")
        agent_id = stop_request.get("agent_id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少会话ID"
            )
        
        # 验证会话是否属于当前用户
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权访问"
            )
        
        # 如果有内容需要保存，保存Agent消息
        if current_content.strip():
            from backend.crud.chat import add_message
            
            # 计算token数量（简单估算）
            tokens = len(current_content) // 4
            prompt_tokens = len(user_content) // 4 if user_content else 0
            total_tokens = tokens + prompt_tokens
            
            # 如果提供了用户内容，且会话中还没有用户消息，先保存用户消息
            if user_content.strip():
                # 检查会话中最新的消息是否是用户消息
                existing_messages = await get_chat_messages(db, session_id)
                if not existing_messages or existing_messages[-1].role != "user":
                    # 保存用户消息
                    user_message = await add_message(
                        db=db,
                        session_id=session_id,
                        role="user",
                        content=user_content,
                        tokens=prompt_tokens,
                        prompt_tokens=0,
                        total_tokens=prompt_tokens,
                        agent_id=agent_id
                    )
                    
                    # 添加到记忆服务
                    from backend.services.memory import memory_service
                    memory_service.add_user_message(session_id, user_content, current_user.id)
                    
                    api_logger.info(f"已保存停止时的用户消息: session_id={session_id}, message_id={user_message.public_id}")
            
            # 保存Agent的部分响应
            ai_message = await add_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=current_content,
                tokens=tokens,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                agent_id=agent_id
            )
            
            # 添加到记忆服务
            from backend.services.memory import memory_service
            memory_service.add_assistant_message(session_id, current_content, current_user.id)
            
            api_logger.info(f"已保存停止时的Agent响应: session_id={session_id}, message_id={ai_message.public_id}, content_length={len(current_content)}")
        elif user_content.strip():
            # 如果只有用户内容没有Agent响应，也要保存用户消息
            from backend.crud.chat import add_message
            
            prompt_tokens = len(user_content) // 4
            
            # 检查会话中最新的消息是否是用户消息
            existing_messages = await get_chat_messages(db, session_id)
            if not existing_messages or existing_messages[-1].role != "user":
                # 保存用户消息
                user_message = await add_message(
                    db=db,
                    session_id=session_id,
                    role="user",
                    content=user_content,
                    tokens=prompt_tokens,
                    prompt_tokens=0,
                    total_tokens=prompt_tokens,
                    agent_id=agent_id
                )
                
                # 添加到记忆服务
                from backend.services.memory import memory_service
                memory_service.add_user_message(session_id, user_content, current_user.id)
                
                api_logger.info(f"已保存停止时的用户消息: session_id={session_id}, message_id={user_message.public_id}")
        
        return {
            "code": 200,
            "msg": "成功保存停止时的响应内容",
            "data": {
                "session_id": session_id,
                "content_saved": len(current_content) > 0,
                "content_length": len(current_content),
                "user_content_saved": len(user_content.strip()) > 0
            },
            "errors": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"停止并保存响应失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止并保存响应失败: {str(e)}"
        )


@router.get("/test_api")
async def test_openai_api(
    request: Request,
):
    """
    测试OpenAI API连接
    """
    result = {"success": False, "message": "", "content": ""}
    
    try:
        # 获取配置
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL
        
        # 确保base_url以/v1结尾
        if base_url and not base_url.endswith('/v1'):
            base_url = base_url.rstrip() + '/v1'
            api_logger.info(f"修正后的BASE URL: {base_url}")
        
        api_logger.info(f"测试OpenAI API连接 - BASE URL: {base_url}")
        
        # 初始化客户端
        async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        api_logger.info(f"客户端初始化完成, 实际URL: {async_client.base_url}")
        
        # 发送测试请求
        response = await async_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_tokens=50,
            temperature=0.7,
            stream=False
        )
        
        # 记录响应信息
        content = response.choices[0].message.content
        result["success"] = True
        result["message"] = "API连接测试成功"
        result["content"] = content
        result["response_type"] = str(type(response))
        
        api_logger.info(f"[测试API响应] OpenAI API测试成功，返回内容长度: {len(content)}")
        
    except Exception as e:
        error_msg = f"OpenAI API测试失败: {str(e)}"
        api_logger.error(error_msg, exc_info=True)
        result["message"] = error_msg
    
    return SuccessResponse(
        data=result,
        msg="API测试完成",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/stream")
async def stream_chat(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    流式聊天接口，逐步返回AI生成的内容
    """
    api_logger.info(f"用户请求流式聊天: {current_user.username}, 请求ID: {getattr(request.state, 'request_id', '')}")
    
    # 🔍 添加详细的请求参数日志
    api_logger.info(f"🔍 流式聊天请求参数详情:")
    api_logger.info(f"   - content: {chat_request.content[:50]}..." if len(chat_request.content) > 50 else f"   - content: {chat_request.content}")
    api_logger.info(f"   - session_id: {chat_request.session_id} (类型: {type(chat_request.session_id)})")
    api_logger.info(f"   - note_id: {chat_request.note_id} (类型: {type(chat_request.note_id)})")
    api_logger.info(f"   - agent_id: {chat_request.agent_id}")
    api_logger.info(f"   - model: {chat_request.model}")
    api_logger.info(f"   - stream: {chat_request.stream}")
    
    # 特殊处理：如果session_id为0，视为创建新会话
    create_new_session = False
    note_id = None
    if chat_request.session_id == 0:
        api_logger.info(f"用户请求创建新流式会话: {current_user.username}")
        chat_request.session_id = None
        create_new_session = True
        
        # 如果提供了note_id，记录下来
        if chat_request.note_id:
            from backend.models.note import Note
            from sqlalchemy import select
            
            # 将note_id转换为数据库内部ID进行验证
            db_note_id = await IDConverter.get_note_db_id(db, chat_request.note_id)
            if db_note_id:
                # 查询笔记是否存在
                stmt = select(Note).where(
                    Note.id == db_note_id,
                    Note.user_id == current_user.id,
                    Note.is_deleted == False
                )
                note_result = await db.execute(stmt)
                note = note_result.scalar_one_or_none()
                
                if note:
                    note_id = chat_request.note_id
                    api_logger.info(f"流式会话将关联到笔记ID: {note_id}")
    
    # 强制设置为流式
    chat_request.stream = True
    
    # 获取Agent信息
    agent_id = chat_request.agent_id
    agent_info = None
    
    if agent_id and db:
        from backend.crud.agent import agent as agent_crud
        agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
        if agent:
            # 🔧 修复：优先使用请求中指定的模型，如果没有则使用Agent的默认模型
            actual_model = chat_request.model if chat_request.model else agent.model
            agent_info = {
                "id": agent.public_id,
                "name": "AI助手",  # 使用默认显示名称
                "avatar_url": None,  # 移除avatar_url字段访问
                "model": actual_model  # 使用实际使用的模型
            }
    
    # 创建流式响应
    async def event_generator():
        try:
            # 跟踪生成的完整内容
            full_content = ""
            session_id = None  # 将在流中获取
            request_id = getattr(request.state, "request_id", None)
            first_chunk = True  # 标记是否是第一个数据块
            
            # 如果是创建新会话，先预创建会话以获取ID
            if create_new_session:
                from backend.crud.chat import create_chat
                from backend.schemas.chat import ChatCreate
                
                # 预创建会话
                chat_data = ChatCreate(title="新对话")
                new_chat = await create_chat(db, current_user.id, chat_data=chat_data, agent_id=agent_id)
                session_id = new_chat.public_id  # 使用public_id
                
                # 更新请求中的会话ID
                chat_request.session_id = session_id
                
                api_logger.info(f"预创建新会话: session_id={session_id}")
                
                # 如果有笔记ID，立即关联到会话
                if note_id:
                    api_logger.info(f"🔍 开始处理笔记关联: note_id={note_id}, session_id={session_id}")
                    
                    from backend.models.note import Note
                    from sqlalchemy import select
                    
                    # 将note_id转换为数据库内部ID
                    db_note_id = await IDConverter.get_note_db_id(db, note_id)
                    if db_note_id:
                        note_stmt = select(Note).where(
                            Note.id == db_note_id,
                            Note.user_id == current_user.id,
                            Note.is_deleted == False
                        )
                        note_result = await db.execute(note_stmt)
                        note = note_result.scalar_one_or_none()
                        
                        api_logger.info(f"🔍 笔记查询结果: {'找到笔记' if note else '笔记不存在'}")
                        
                        if note:
                            api_logger.info(f"🔍 笔记详情: id={note.id}, title={note.title}, user_id={note.user_id}")
                            
                            # 使用新的多对多关联方式
                            # 检查是否已有主要会话，如果没有则设为主要会话
                            existing_primary = await note_session.get_primary_session_by_note(db, note_id)
                            is_primary = existing_primary is None  # 如果没有主要会话，这个就是主要会话
                            
                            api_logger.info(f"🔍 现有主要会话: {existing_primary}, 新会话是否为主要: {is_primary}")
                            
                            await note_session.create_note_session_link(
                                db, 
                                note_id=note_id, 
                                session_id=session_id,
                                is_primary=is_primary
                            )
                            
                            api_logger.info(f"🔍 笔记ID {note_id} 已关联到预创建会话ID {session_id}，是否为主要会话: {is_primary}")
                            
                            # 验证关联是否真的被创建
                            verification_sessions = await note_session.get_sessions_by_note(db, note_id)
                            verification_session_ids = [s.public_id for s in verification_sessions]
                            api_logger.info(f"🔍 验证笔记 {note_id} 关联的会话列表: {verification_session_ids}")
                            
                            if session_id in verification_session_ids:
                                api_logger.info(f"✅ 笔记 {note_id} 与会话 {session_id} 关联创建成功")
                            else:
                                api_logger.error(f"❌ 笔记 {note_id} 与会话 {session_id} 关联创建失败！")
                        else:
                            api_logger.warning(f"🔍 笔记ID {note_id} 不存在或不属于用户 {current_user.id}")
                    else:
                        api_logger.error(f"无法转换笔记ID: {note_id}")
                else:
                    api_logger.info("没有提供笔记ID，跳过笔记关联")
            
            async for chunk_data in generate_chat_stream(
                chat_request=chat_request,
                db=db,
                user_id=current_user.id
            ):
                # 处理不同格式的响应数据
                content = ""
                reasoning_content = ""
                tool_status = None
                
                if isinstance(chunk_data, tuple):
                    if len(chunk_data) == 4:
                        # 四元组：(content, session_id, reasoning_content, tool_status)
                        content, stream_session_id, reasoning_content, tool_status = chunk_data
                        if stream_session_id and session_id is None:
                            session_id = stream_session_id
                    elif len(chunk_data) == 3:
                        # 三元组：(content, reasoning_content, tool_status) 或 (content, session_id, reasoning_content/tool_status)
                        first, second, third = chunk_data
                        if isinstance(second, int):
                            # 格式：(content, session_id, reasoning_content/tool_status)
                            content = first
                            stream_session_id = second
                            if stream_session_id and session_id is None:
                                session_id = stream_session_id
                            
                            # 判断第三个参数类型
                            if isinstance(third, dict):
                                tool_status = third
                            else:
                                reasoning_content = third or ""
                        else:
                            # 格式：(content, reasoning_content, tool_status)
                            content = first
                            reasoning_content = second or ""
                            if isinstance(third, dict):
                                tool_status = third
                    elif len(chunk_data) == 2:
                        # 二元组：(content, session_id) 或 (content, reasoning_content)
                        first, second = chunk_data
                        content = first
                        if isinstance(second, int):
                            stream_session_id = second
                            if stream_session_id and session_id is None:
                                session_id = stream_session_id
                        else:
                            reasoning_content = second or ""
                else:
                    # 单个内容
                    content = chunk_data
                
                # 确保reasoning_content是字符串
                if reasoning_content and not isinstance(reasoning_content, str):
                    reasoning_content = str(reasoning_content)
                
                # 累积内容
                if content:
                    full_content += content
                
                # 如果有工具状态信息，发送工具状态事件
                if tool_status:
                    tool_response_data = {
                        "code": 200,
                        "msg": "成功",
                        "data": {
                            "message": {
                                "content": ""
                            },
                            "full_content": full_content,
                            "session_id": session_id or 0,
                            "done": False,
                            "tool_status": tool_status,
                            "agent_info": agent_info
                        },
                        "errors": None,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "request_id": request_id
                    }
                    
                    yield f"data: {json.dumps(tool_response_data, ensure_ascii=False)}\n\n"
                
                # 如果有内容，发送内容事件
                if content or reasoning_content:
                    # 构造响应数据
                    response_data = {
                        "code": 200,
                        "msg": "成功",
                        "data": {
                            "message": {
                                "content": content,
                                "reasoning_content": reasoning_content  # 添加思考内容字段
                            },
                            "full_content": full_content,
                            "session_id": session_id or 0,
                            "done": False,
                            "agent_info": agent_info
                        },
                        "errors": None,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "request_id": request_id
                    }
                    
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
            
            # 发送最终响应，标记完成
            final_response_data = {
                "code": 200,
                "msg": "成功",
                "data": {
                    "message": {
                        "content": ""
                    },
                    "full_content": full_content,
                    "session_id": session_id or 0,
                    "done": True,
                    "agent_info": agent_info
                },
                "errors": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "request_id": request_id
            }
            
            yield f"data: {json.dumps(final_response_data, ensure_ascii=False)}\n\n"
            
            api_logger.info(f"流式聊天完成: session_id={session_id}, content_length={len(full_content)}")
            
        except Exception as e:
            api_logger.error(f"流式响应生成失败: {str(e)}", exc_info=True)
            
            # 发送错误响应
            error_response_data = {
                "code": 500,
                "msg": f"流式响应失败: {str(e)}",
                "data": {
                    "message": {
                        "content": f"抱歉，AI助手出错了: {str(e)}"
                    },
                    "full_content": f"抱歉，AI助手出错了: {str(e)}",
                    "session_id": session_id or 0,
                    "done": True,
                    "agent_info": agent_info
                },
                "errors": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "request_id": request_id
            }
            
            yield f"data: {json.dumps(error_response_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.post("/sessions", response_model=ChatResponseModel)
async def create_chat_session(
    request: Request,
    chat_data: ChatCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    创建新的聊天会话
    """
    try:
        new_chat = await create_chat(db, user_id=current_user.id, chat_data=chat_data)
        
        # 如果提供了笔记ID，将会话与笔记关联
        if chat_data.note_id:
            from backend.models.note import Note
            from sqlalchemy import select
            
            # 将note_id转换为数据库内部ID进行验证
            db_note_id = await IDConverter.get_note_db_id(db, chat_data.note_id)
            if db_note_id:
                # 查询笔记是否存在
                stmt = select(Note).where(
                    Note.id == db_note_id,
                    Note.user_id == current_user.id,
                    Note.is_deleted == False
                )
                note_result = await db.execute(stmt)
                note = note_result.scalar_one_or_none()
                
                if note:
                    # 使用新的多对多关联方式
                    # 检查是否已有主要会话，如果没有则设为主要会话
                    existing_primary = await note_session.get_primary_session_by_note(db, chat_data.note_id)
                    is_primary = existing_primary is None  # 如果没有主要会话，这个就是主要会话
                    
                    await note_session.create_note_session_link(
                        db, 
                        note_id=chat_data.note_id, 
                        session_id=new_chat.public_id,  # 使用public_id
                        is_primary=is_primary
                    )
                    
                    api_logger.info(f"笔记ID {chat_data.note_id} 已关联到会话ID {new_chat.public_id}，是否为主要会话: {is_primary}")
                    
                    # 验证关联是否真的被创建
                    verification_sessions = await note_session.get_sessions_by_note(db, chat_data.note_id)
                    verification_session_ids = [s.public_id for s in verification_sessions]
                    api_logger.info(f"验证笔记 {chat_data.note_id} 关联的会话列表: {verification_session_ids}")
                    
                    if new_chat.public_id in verification_session_ids:
                        api_logger.info(f"✅ 笔记 {chat_data.note_id} 与会话 {new_chat.public_id} 关联创建成功")
                    else:
                        api_logger.error(f"❌ 笔记 {chat_data.note_id} 与会话 {new_chat.public_id} 关联创建失败！")
                else:
                    api_logger.warning(f"笔记ID {chat_data.note_id} 不存在或不属于用户 {current_user.id}")
        
        return SuccessResponse(
            data={
                "id": new_chat.public_id,  # 使用public_id
                "title": new_chat.title,
                "user_id": current_user.public_id,  # 使用public_id
                "created_at": new_chat.created_at.isoformat() if new_chat.created_at else None,
                "updated_at": new_chat.updated_at.isoformat() if new_chat.updated_at else None
            },
            msg="创建会话成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{session_id}", response_model=ChatResponseModel)
async def update_chat_session(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    chat_data: ChatUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新聊天会话信息
    """
    api_logger.info(f"更新聊天会话: session_id={session_id}, user={current_user.username}")
    
    # 验证会话存在且属于当前用户（get_chat已支持public_id）
    chat = await get_chat(db, session_id)
    if not chat or chat.user_id != current_user.id:
        api_logger.warning(f"聊天会话不存在或无权访问: session_id={session_id}, user={current_user.username}")
        return SuccessResponse(
            data=None,
            msg="聊天会话不存在或无权访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 更新标题（update_chat_title已支持public_id）
    updated_chat = await update_chat_title(db, session_id, chat_data.title)
    
    result = {
        "id": updated_chat.public_id,  # 使用public_id
        "user_id": current_user.public_id,  # 使用public_id
        "title": updated_chat.title,
        "created_at": updated_chat.created_at.isoformat() if updated_chat.created_at else None,
        "updated_at": updated_chat.updated_at.isoformat() if updated_chat.updated_at else None,
        "messages": []
    }
    
    return SuccessResponse(
        data=result,
        msg="更新聊天会话成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除聊天会话
    """
    api_logger.info(f"删除聊天会话: session_id={session_id}, user={current_user.username}")
    
    # 验证会话存在且属于当前用户（get_chat已支持public_id）
    chat = await get_chat(db, session_id)
    if not chat or chat.user_id != current_user.id:
        api_logger.warning(f"聊天会话不存在或无权访问: session_id={session_id}, user={current_user.username}")
        return SuccessResponse(
            data=None,
            msg="聊天会话不存在或无权访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 软删除会话（soft_delete_chat已支持public_id）
    success = await soft_delete_chat(db, session_id)
    
    return SuccessResponse(
        data={"success": success},
        msg="删除聊天会话成功" if success else "删除聊天会话失败",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/memory/health")
async def check_memory_health(
    request: Request,
):
    """
    检查Redis记忆服务的健康状态
    """
    result = {"redis_connected": False, "message": ""}
    
    try:
        # 测试Redis连接
        redis_client.ping()
        
        # 测试Redis操作
        test_key = "memory:test:health"
        redis_client.set(test_key, "测试成功", ex=60)
        test_value = redis_client.get(test_key)
        redis_client.delete(test_key)
        
        result["redis_connected"] = True
        result["message"] = f"Redis连接正常，读写测试成功: {test_value}"
        
        # 获取Redis信息
        info = redis_client.info()
        result["redis_version"] = info.get("redis_version")
        result["memory_used"] = f"{info.get('used_memory_human', '0')} / {info.get('maxmemory_human', 'unlimited')}"
        result["uptime"] = f"{info.get('uptime_in_days', 0)} 天"
        
        api_logger.info("Redis健康检查通过")
    except Exception as e:
        result["message"] = f"Redis连接错误: {str(e)}"
        api_logger.error(f"Redis健康检查失败: {str(e)}", exc_info=True)
    
    return SuccessResponse(
        data=result,
        msg="Redis健康检查完成",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/memory/{session_id}")
async def get_memory_content(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定会话在Redis中的记忆内容
    """
    api_logger.info(f"获取会话记忆内容: session_id={session_id}, user={current_user.username}")
    
    try:
        # 获取会话基本信息（验证用户权限）（get_chat已支持public_id）
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: session_id={session_id}, user={current_user.username}")
            return SuccessResponse(
                data=None,
                msg="聊天会话不存在或无权访问",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 获取会话记忆内容（memory_service已支持public_id）
        messages = memory_service.get_messages(session_id)
        
        # 计算记忆统计信息
        stats = {
            "message_count": len(messages),
            "user_messages": sum(1 for msg in messages if msg.get("role") == "user"),
            "assistant_messages": sum(1 for msg in messages if msg.get("role") == "assistant"),
            "total_tokens_estimate": sum(len(msg.get("content", "")) // 4 for msg in messages)  # 粗略估计
        }
        
        result = {
            "session_id": session_id,
            "memory_exists": len(messages) > 0,
            "messages": messages,
            "stats": stats
        }
        
        return SuccessResponse(
            data=result,
            msg="获取会话记忆内容成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"获取会话记忆内容失败: {str(e)}", exc_info=True)
        return SuccessResponse(
            data={"error": str(e)},
            msg="获取会话记忆内容失败",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/memory/stats/all")
async def get_all_memory_stats(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    获取Redis中所有记忆的统计信息（仅管理员可用）
    """
    if not current_user.is_superuser:
        return SuccessResponse(
            data=None,
            msg="权限不足，仅管理员可访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    try:
        # 获取所有记忆键
        memory_keys = redis_client.keys("memory:*")
        
        # 获取Redis信息
        info = redis_client.info()
        
        # 构建响应
        result = {
            "active_memories": len(memory_keys),
            "memory_keys": memory_keys[:20],  # 仅返回前20个键
            "redis_info": {
                "version": info.get("redis_version"),
                "memory_used": info.get("used_memory_human"),
                "memory_peak": info.get("used_memory_peak_human"),
                "uptime_days": info.get("uptime_in_days"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": sum(db.get("keys", 0) for db_id, db in info.items() if isinstance(db, dict) and "keys" in db)
            }
        }
        
        api_logger.info(f"获取Redis记忆统计信息：活跃记忆数={result['active_memories']}")
        
        return SuccessResponse(
            data=result,
            msg="获取记忆统计信息成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"获取Redis记忆统计信息失败: {str(e)}", exc_info=True)
        return SuccessResponse(
            data={"error": str(e)},
            msg="获取记忆统计信息失败",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/restore-memory/{session_id}")
async def restore_chat_memory(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    从数据库恢复指定会话的记忆上下文到Redis
    """
    api_logger.info(f"恢复会话记忆: session_id={session_id}, user={current_user.username}")
    
    try:
        # 验证会话存在且属于当前用户（get_chat已支持public_id）
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: session_id={session_id}, user={current_user.username}")
            return SuccessResponse(
                data={"success": False, "message": "聊天会话不存在或无权访问"},
                msg="恢复会话记忆失败",
                request_id=getattr(request.state, "request_id", None)
            )
        
        try:
            # 查询历史消息（get_chat_messages已支持public_id）
            db_messages = await get_chat_messages(db, session_id)
            
            # 清除现有记忆（memory_service已支持public_id）
            memory_service.clear_memory(session_id)
            
            # 格式化消息并恢复到Redis
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in db_messages
                if not msg.is_deleted
            ]
            
            # 获取用户当前的记忆会话数量
            memory_count = memory_service.count_user_memories(current_user.id)
            
            # 恢复记忆，传递用户ID进行管理（memory_service已支持public_id）
            restored = memory_service.restore_memory_from_db(session_id, formatted_messages, current_user.id)
            
            if restored:
                return SuccessResponse(
                    data={
                        "success": True, 
                        "message_count": len(formatted_messages),
                        "memory_count": memory_service.count_user_memories(current_user.id),
                        "max_memories": settings.REDIS_MAX_USER_MEMORIES,
                        "messages": formatted_messages if len(formatted_messages) <= 5 else formatted_messages[:5] + [{"note": f"还有 {len(formatted_messages) - 5} 条消息..."}]
                    },
                    msg="恢复会话记忆成功",
                    request_id=getattr(request.state, "request_id", None)
                )
            else:
                return SuccessResponse(
                    data={"success": False, "message": "没有可恢复的历史消息"},
                    msg="恢复会话记忆失败",
                    request_id=getattr(request.state, "request_id", None)
                )
        except Exception as redis_error:
            # Redis错误特殊处理，返回成功但标记Redis错误
            api_logger.error(f"Redis操作出错: {str(redis_error)}", exc_info=True)
            return SuccessResponse(
                data={
                    "success": False, 
                    "message": f"Redis操作失败: {str(redis_error)}",
                    "redis_error": True
                },
                msg="Redis操作失败",
                request_id=getattr(request.state, "request_id", None)
            )
    except Exception as e:
        # 数据库或其他错误
        api_logger.error(f"恢复会话记忆失败: {str(e)}", exc_info=True)
        return SuccessResponse(
            data={"success": False, "message": f"系统错误: {str(e)}"},
            msg="恢复会话记忆失败",
            request_id=getattr(request.state, "request_id", None)
        )


@router.get("/memory-sessions")
async def get_user_memory_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户当前在Redis中保存的记忆会话列表
    """
    api_logger.info(f"获取用户记忆会话列表: user={current_user.username}")
    
    try:
        # 获取用户的记忆会话ID列表（memory_service已支持用户ID）
        memory_ids = memory_service.get_user_memory_sessions(current_user.id)
        
        # 从数据库获取会话详情
        sessions = []
        for mem_id in memory_ids:
            try:
                # get_chat已支持public_id
                chat = await get_chat(db, mem_id)
                if chat and chat.user_id == current_user.id:
                    messages_count = len(memory_service.get_messages(mem_id))
                    sessions.append({
                        "id": chat.public_id,  # 使用public_id
                        "title": chat.title,
                        "created_at": chat.created_at.isoformat() if chat.created_at else None,
                        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                        "messages_in_memory": messages_count
                    })
            except Exception as e:
                api_logger.error(f"获取会话 {mem_id} 详情失败: {str(e)}", exc_info=True)
                # 跳过当前会话，继续处理其他会话
                continue
                
        return SuccessResponse(
            data={
                "sessions": sessions,
                "count": len(sessions),
                "max_memories": settings.REDIS_MAX_USER_MEMORIES
            },
            msg="获取用户记忆会话列表成功",
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"获取用户记忆会话列表失败: {str(e)}", exc_info=True)
        return SuccessResponse(
            data={
                "sessions": [],
                "count": 0,
                "max_memories": settings.REDIS_MAX_USER_MEMORIES,
                "error": str(e)
            },
            msg="获取用户记忆会话列表出错",
            request_id=getattr(request.state, "request_id", None)
        )


@router.post("/ask-again/{session_id}")
async def ask_again(
    request: Request,
    session_id: str = Path(..., description="聊天会话ID"),
    ask_request: AskAgainRequest = Body(..., description="重新提问请求"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    编辑并重新执行会话中的消息
    
    功能：
    1. 编辑用户输入并重新执行(is_user_message=True, rerun=True)
    2. 仅编辑用户输入不重新执行(is_user_message=True, rerun=False)
    3. 编辑AI回复(is_user_message=False)
    """
    api_logger.info(f"用户请求编辑消息: session_id={session_id}, message_index={ask_request.message_index}, " +
                   f"is_user_message={ask_request.is_user_message}, rerun={ask_request.rerun}, user={current_user.username}")
    
    try:
        # 验证会话存在且属于当前用户（get_chat已支持public_id）
        chat = await get_chat(db, session_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: session_id={session_id}, user={current_user.username}")
            return SuccessResponse(
                data=None,
                msg="聊天会话不存在或无权访问",
                request_id=getattr(request.state, "request_id", None)
            )
            
        # 获取消息列表，验证消息ID是否存在（get_chat_messages已支持public_id）
        db_messages = await get_chat_messages(db, session_id)
        db_message_ids = [msg.id for msg in db_messages]
        db_message_public_ids = [msg.public_id for msg in db_messages]
        
        # 判断message_index是整数索引还是字符串ID
        is_message_index_numeric = isinstance(ask_request.message_index, int)
        is_message_index_in_db_ids = ask_request.message_index in db_message_ids
        is_message_index_in_public_ids = ask_request.message_index in db_message_public_ids
        
        # 查找指定消息在数据库中的角色
        target_message_id = None  # 要软删除的起始消息ID
        target_message_public_id = None  # 目标消息的public_id
        target_message = None
        message_position = None
        
        if is_message_index_in_db_ids:
            # 是数据库内部ID
            message_position = db_message_ids.index(ask_request.message_index)
            target_message = db_messages[message_position]
            target_message_id = ask_request.message_index
            target_message_public_id = target_message.public_id
        elif is_message_index_in_public_ids:
            # 是public_id，需要转换为数据库ID
            message_position = db_message_public_ids.index(ask_request.message_index)
            target_message = db_messages[message_position]
            target_message_id = target_message.id
            target_message_public_id = ask_request.message_index
            api_logger.info(f"将public_id {ask_request.message_index} 转换为数据库ID {target_message_id}")
        elif is_message_index_numeric and 0 <= ask_request.message_index < len(db_messages):
            # 是有效的数字索引
            message_position = ask_request.message_index
            target_message = db_messages[message_position]
            target_message_id = target_message.id
            target_message_public_id = target_message.public_id
        
        # 如果找到了目标消息，检查角色一致性
        if target_message:
            is_user_role = target_message.role == "user"
            if is_user_role != ask_request.is_user_message:
                api_logger.warning(f"消息角色与请求不一致: 数据库角色={target_message.role}, 请求is_user_message={ask_request.is_user_message}")
                return SuccessResponse(
                    data={"success": False},
                    msg="消息角色与请求不匹配",
                    request_id=getattr(request.state, "request_id", None)
                )
        
        # 检查是否找到了有效的消息
        if target_message and message_position is not None:
            # 获取当前Redis中的记忆状态，查看消息数是否匹配（memory_service已支持public_id）
            memory_messages = memory_service.get_messages(session_id)
            
            # 检查Redis中的记忆是否存在或是否有足够的消息
            if not memory_messages or len(memory_messages) == 0:
                api_logger.warning(f"会话 {session_id} 在Redis中没有记忆，尝试恢复记忆")
                
                # 尝试将数据库消息恢复到Redis
                formatted_messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in db_messages
                    if not msg.is_deleted
                ]
                
                restored = memory_service.restore_memory_from_db(session_id, formatted_messages, current_user.id)
                if not restored:
                    return SuccessResponse(
                        data={"success": False},
                        msg="消息编辑失败，无法恢复聊天记忆",
                        request_id=getattr(request.state, "request_id", None)
                    )
                
                # 重新获取Redis中的消息
                memory_messages = memory_service.get_messages(session_id)
            
            # 如果Redis中的消息数量与数据库不一致，使用消息对应的比例位置
            if len(memory_messages) != len(db_messages):
                # 使用消息在数据库中的相对位置计算在Redis中的索引
                memory_index = int((message_position / len(db_messages)) * len(memory_messages))
                api_logger.info(f"数据库消息数 {len(db_messages)} 与Redis记忆消息数 {len(memory_messages)} 不一致，使用相对位置计算")
            else:
                # 记忆消息与数据库消息一致，直接使用相同索引
                memory_index = message_position
                
            api_logger.info(f"转换消息ID {ask_request.message_index} 为记忆索引 {memory_index}")
            
            # 获取目标消息角色
            target_role = db_messages[message_position].role
            # 记录要删除的消息数量
            messages_to_remove = 0
            
            # 根据操作类型处理不同情况
            if ask_request.is_user_message:  # 编辑用户消息
                if ask_request.rerun:  # 需要重新执行
                    # 记录要删除的消息数量
                    messages_to_remove = len(memory_messages) - memory_index if memory_index < len(memory_messages) else 0
                    
                    # 替换消息并截断（replace_message_and_truncate已支持public_id）
                    if not ask_request.content:
                        # 如果没有提供新内容，使用原消息内容
                        original_content = db_messages[message_position].content
                        result = await replace_message_and_truncate(session_id, memory_index, original_content, target_role)
                    else:
                        result = await replace_message_and_truncate(session_id, memory_index, ask_request.content, target_role)
                    
                    # 更新数据库中的消息内容（update_message_content已支持message_id）
                    if ask_request.content and memory_index < len(db_messages):
                        corresponding_message = db_messages[memory_index]
                        db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                        if db_update_success:
                            api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                        else:
                            api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
                else:  # 仅编辑不重新执行
                    # 不需要截断记忆，仅替换指定消息内容
                    new_content = ask_request.content or db_messages[message_position].content
                    result = memory_service.update_message_content(session_id, memory_index, new_content)
                    messages_to_remove = 0
                    
                    # 更新数据库中的消息内容
                    if ask_request.content and memory_index < len(db_messages):
                        corresponding_message = db_messages[memory_index]
                        db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                        if db_update_success:
                            api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                        else:
                            api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
            else:  # 编辑AI回复
                # 找到AI回复消息的位置
                if target_role != "assistant":
                    api_logger.warning(f"尝试编辑非AI回复消息: message_index={ask_request.message_index}, role={target_role}")
                    return SuccessResponse(
                        data={"success": False},
                        msg="只能编辑AI回复消息",
                        request_id=getattr(request.state, "request_id", None)
                    )
                
                # 仅编辑内容，不重新执行
                new_content = ask_request.content or db_messages[message_position].content
                result = memory_service.update_message_content(session_id, memory_index, new_content)
                messages_to_remove = 0
                
                # 更新数据库中的消息内容
                if ask_request.content and memory_index < len(db_messages):
                    corresponding_message = db_messages[memory_index]
                    db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                    if db_update_success:
                        api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                    else:
                        api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
        else:
            # 消息未找到，检查是否为有效的数字索引
            if not is_message_index_numeric:
                # 字符串ID但未找到对应消息
                api_logger.warning(f"无法找到消息: message_index={ask_request.message_index}")
                return SuccessResponse(
                    data={"success": False},
                    msg="指定的消息不存在",
                    request_id=getattr(request.state, "request_id", None)
                )
            # 如果是数字索引，继续到下面的统一处理逻辑
        
        # 此时我们有两种情况：
        # 1. target_message 不为空：找到了数据库中的消息，使用 message_position 和 memory_index
        # 2. target_message 为空但 is_message_index_numeric 为 True：使用数字索引直接操作记忆
        
        # 设置工作变量
        memory_messages = memory_service.get_messages(session_id)
        working_memory_index = None
        target_role = None
        messages_to_remove = 0
        result = False
        
        if target_message and message_position is not None:
            # 找到了数据库消息，使用之前计算的memory_index
            working_memory_index = memory_index
            target_role = target_message.role
        elif is_message_index_numeric:
            # 使用数字索引直接操作记忆
            api_logger.info(f"直接使用 {ask_request.message_index} 作为记忆索引")
            
            # 检查记忆索引是否有效
            if ask_request.message_index < 0 or ask_request.message_index >= len(memory_messages):
                return SuccessResponse(
                    data={"success": False},
                    msg="无效的记忆消息索引",
                    request_id=getattr(request.state, "request_id", None)
                )
            
            working_memory_index = ask_request.message_index
            target_role = memory_messages[ask_request.message_index]["role"]
            
            # 检查角色与请求中的is_user_message是否一致
            is_user_role = target_role == "user"
            if is_user_role != ask_request.is_user_message:
                api_logger.warning(f"消息角色与请求不一致: 记忆角色={target_role}, 请求is_user_message={ask_request.is_user_message}")
                return SuccessResponse(
                    data={"success": False},
                    msg="消息角色与请求不匹配",
                    request_id=getattr(request.state, "request_id", None)
                )
        else:
            # 这种情况不应该发生，因为前面已经处理了
            api_logger.error("未能确定工作索引")
            return SuccessResponse(
                data={"success": False},
                msg="系统错误：未能确定消息索引",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 根据操作类型处理不同情况
        if ask_request.is_user_message:  # 编辑用户消息
            if ask_request.rerun:  # 需要重新执行
                # 记录要删除的消息数量
                messages_to_remove = len(memory_messages) - working_memory_index if working_memory_index < len(memory_messages) else 0
                
                # 替换消息并截断
                if not ask_request.content:
                    # 如果没有提供新内容，使用原消息内容
                    original_content = memory_messages[working_memory_index]["content"]
                    result = await replace_message_and_truncate(session_id, working_memory_index, original_content, target_role)
                else:
                    result = await replace_message_and_truncate(session_id, working_memory_index, ask_request.content, target_role)
                
                # 更新数据库中的消息内容
                if ask_request.content and working_memory_index < len(db_messages):
                    corresponding_message = db_messages[working_memory_index]
                    db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                    if db_update_success:
                        api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                    else:
                        api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
            else:  # 仅编辑不重新执行
                # 不需要截断记忆，仅替换指定消息内容
                new_content = ask_request.content or memory_messages[working_memory_index]["content"]
                result = memory_service.update_message_content(session_id, working_memory_index, new_content)
                messages_to_remove = 0
                
                # 更新数据库中的消息内容
                if ask_request.content and working_memory_index < len(db_messages):
                    corresponding_message = db_messages[working_memory_index]
                    db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                    if db_update_success:
                        api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                    else:
                        api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
        else:  # 编辑AI回复
            # 检查是否为AI回复消息
            if target_role != "assistant":
                api_logger.warning(f"尝试编辑非AI回复消息: memory_index={working_memory_index}, role={target_role}")
                return SuccessResponse(
                    data={"success": False},
                    msg="只能编辑AI回复消息",
                    request_id=getattr(request.state, "request_id", None)
                )
            
            # 仅编辑内容，不重新执行
            new_content = ask_request.content or memory_messages[working_memory_index]["content"]
            result = memory_service.update_message_content(session_id, working_memory_index, new_content)
            messages_to_remove = 0
            
            # 更新数据库中的消息内容
            if ask_request.content and working_memory_index < len(db_messages):
                corresponding_message = db_messages[working_memory_index]
                db_update_success = await update_message_content(db, corresponding_message.public_id, ask_request.content)
                if db_update_success:
                    api_logger.info(f"已更新数据库中的消息内容: message_id={corresponding_message.public_id}")
                else:
                    api_logger.warning(f"更新数据库中的消息内容失败: message_id={corresponding_message.public_id}")
        
        if not result:
            return SuccessResponse(
                data={"success": False},
                msg="编辑消息失败",
                request_id=getattr(request.state, "request_id", None)
            )
        
        api_logger.info(f"会话 {session_id} 已编辑消息" + 
                        (f"并截断记忆，删除 {messages_to_remove} 条后续消息" if messages_to_remove > 0 else ""))
        
        # 如果找到了要操作的数据库消息ID，在需要重新执行时执行软删除操作
        db_deleted_count = 0
        if target_message_id and ask_request.is_user_message and ask_request.rerun:
            # 在删除后续消息之前，先更新原始消息的内容
            if ask_request.content:
                update_success = await update_message_content(db, target_message_public_id, ask_request.content)
                if update_success:
                    api_logger.info(f"已更新原始消息内容: message_id={target_message_public_id}")
                else:
                    api_logger.warning(f"更新原始消息内容失败: message_id={target_message_public_id}")
            
            # 软删除指定消息ID之后的所有消息（soft_delete_messages_after已支持session_id）
            db_deleted_count = await soft_delete_messages_after(db, session_id, target_message_public_id)
            api_logger.info(f"已在数据库中软删除 {db_deleted_count} 条消息，从ID {target_message_public_id} 开始")
        
        # 如果重新执行，并且提供了新内容，则立即发送新消息
        if ask_request.is_user_message and ask_request.rerun and ask_request.content:
            # 获取Agent信息
            agent_id = ask_request.agent_id
            agent_info = None
            
            if agent_id and db:
                from backend.crud.agent import agent as agent_crud
                agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
                if agent:
                    agent_info = {
                        "id": agent.public_id,  # 使用public_id
                        "name": "AI助手",
                        "avatar_url": None,
                        "model": agent.model
                    }
            
            # 准备图片数据：优先使用请求中的图片，如果没有则从原始消息中提取
            images_to_use = ask_request.images if ask_request.images else []
            
            # 如果请求中没有图片数据，尝试从原始消息中提取
            if not images_to_use and target_message:
                try:
                    # 尝试解析原始消息内容中的图片数据
                    import json
                    original_content = target_message.content
                    if original_content:
                        # 检查是否是JSON格式的复合消息
                        try:
                            parsed_content = json.loads(original_content)
                            if isinstance(parsed_content, dict) and parsed_content.get("type") == "user_message":
                                if "images" in parsed_content and parsed_content["images"]:
                                    # 将数据库中的图片格式转换为ImageData格式
                                    from backend.schemas.chat import ImageData
                                    images_to_use = [
                                        ImageData(
                                            url=img.get("url", ""),
                                            name=img.get("name"),
                                            size=img.get("size")
                                        ) for img in parsed_content["images"]
                                    ]
                                    api_logger.info(f"从原始消息中提取到 {len(images_to_use)} 张图片")
                        except (json.JSONDecodeError, ValueError):
                            # 如果不是JSON格式，说明是纯文本消息，没有图片
                            pass
                except Exception as e:
                    api_logger.warning(f"提取原始消息图片数据失败: {e}")
            
            # 如果是流式请求，使用特殊的编辑重新执行处理
            if ask_request.stream:
                # 创建修改后的聊天请求，标记为编辑重新执行
                edit_chat_request = ChatRequest(
                    content=ask_request.content,
                    images=images_to_use,  # 添加图片数据
                    stream=True,
                    session_id=session_id,
                    agent_id=ask_request.agent_id
                )
                
                # 添加特殊标记，告诉ChatStreamService跳过用户消息创建
                edit_chat_request.__dict__['_skip_user_message'] = True
                
                api_logger.info(f"编辑重新执行：使用特殊标记跳过用户消息创建，携带 {len(images_to_use)} 张图片")
                
                # 直接调用流式聊天处理
                return await stream_chat(request, edit_chat_request, db, current_user)
            
            # 非流式请求的处理
            # 创建聊天请求
            chat_request = ChatRequest(
                content=ask_request.content,
                images=images_to_use,  # 添加图片数据
                stream=False,
                session_id=session_id,
                agent_id=ask_request.agent_id
            )
            
            # 调用非流式响应生成
            response = await generate_chat_response(
                chat_request=chat_request,
                db=db,
                user_id=current_user.id
            )
            
            api_logger.info(f"编辑并重新发送消息完成: {current_user.username}, 会话ID: {response.session_id}")
            
            # 将Pydantic模型转换为dict
            response_dict = {
                "message": {
                    "content": response.message.content
                },
                "usage": response.usage,
                "session_id": response.session_id,
                "messages_removed": messages_to_remove,
                "db_messages_deleted": db_deleted_count,
                "agent_id": agent_id,
                "agent_info": agent_info
            }
            
            return SuccessResponse(
                data=response_dict,
                msg="编辑并重新发送消息成功",
                request_id=getattr(request.state, "request_id", None)
            )
        
        return SuccessResponse(
            data={
                "success": True, 
                "messages_removed": messages_to_remove, 
                "db_messages_deleted": db_deleted_count,
                "edited": True,
                "rerun": ask_request.is_user_message and ask_request.rerun
            },
            msg="消息编辑成功" + ("并准备重新执行" if ask_request.is_user_message and ask_request.rerun else ""),
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"编辑消息失败: {str(e)}", exc_info=True)
        return SuccessResponse(
            data={"error": str(e)},
            msg="编辑消息失败",
            request_id=getattr(request.state, "request_id", None)
        ) 