from fastapi import APIRouter, Request, Depends, BackgroundTasks, Body, Path, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

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
    soft_delete_chat, get_chat_messages, get_latest_chat, soft_delete_messages_after
)
from backend.core.response import SuccessResponse
from backend.utils.logging import api_logger
from backend.core.config import settings

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
    
    # 特殊处理：如果conversation_id为0，视为创建新会话
    if chat_request.conversation_id == 0:
        api_logger.info(f"用户请求创建新会话: {current_user.username}")
        chat_request.conversation_id = None
        
        # 如果提供了note_id，检查是否需要关联到笔记
        if chat_request.note_id:
            from backend.models.note import Note
            from sqlalchemy import select
            
            # 查询笔记是否存在
            stmt = select(Note).where(
                Note.id == chat_request.note_id,
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
    
    # 获取Agent信息
    agent_id = chat_request.agent_id
    agent_info = None
    
    if agent_id and db:
        from backend.crud.agent import agent as agent_crud
        agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
        if agent:
            agent_info = {
                "id": agent.id,
                "name": agent.name,
                "avatar_url": agent.avatar_url,
                "model": agent.model
            }
    
    # 调用服务生成回复，并保存对话记录
    response = await generate_chat_response(
        chat_request=chat_request,
        db=db,
        user_id=current_user.id
    )
    
    # 如果是新创建的会话，并且存在笔记ID，将会话关联到笔记
    if chat_request.note_id and response.conversation_id:
        from backend.models.note import Note
        
        # 更新笔记，关联到新创建的会话
        note_stmt = select(Note).where(
            Note.id == chat_request.note_id,
            Note.user_id == current_user.id,
            Note.is_deleted == False
        )
        note_result = await db.execute(note_stmt)
        note = note_result.scalar_one_or_none()
        
        if note:
            note.session_id = response.conversation_id
            await db.commit()
            api_logger.info(f"笔记ID {chat_request.note_id} 已关联到会话ID {response.conversation_id}")
    
    api_logger.info(f"聊天请求完成: {current_user.username}, 会话ID: {response.conversation_id}")
    
    # 将Pydantic模型转换为dict，确保可JSON序列化
    response_dict = {
        "message": {
            "content": response.message.content
        },
        "usage": response.usage,
        "conversation_id": response.conversation_id,
        "agent_id": agent_id,
        "agent_info": agent_info
    }
    
    return SuccessResponse(
        data=response_dict,
        msg="聊天成功",
        request_id=getattr(request.state, "request_id", None)
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


@router.post("/chat/stream")
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
    
    # 特殊处理：如果conversation_id为0，视为创建新会话
    create_new_session = False
    note_id = None
    if chat_request.conversation_id == 0:
        api_logger.info(f"用户请求创建新流式会话: {current_user.username}")
        chat_request.conversation_id = None
        create_new_session = True
        
        # 如果提供了note_id，记录下来
        if chat_request.note_id:
            from backend.models.note import Note
            from sqlalchemy import select
            
            # 查询笔记是否存在
            stmt = select(Note).where(
                Note.id == chat_request.note_id,
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
            agent_info = {
                "id": agent.id,
                "name": agent.name,
                "avatar_url": agent.avatar_url,
                "model": agent.model
            }
    
    # 创建流式响应
    async def event_generator():
        try:
            # 跟踪生成的完整内容
            full_content = ""
            conversation_id = None  # 将在流中获取
            request_id = getattr(request.state, "request_id", None)
            first_chunk = True  # 标记是否是第一个数据块
            
            # 如果是创建新会话，先预创建会话以获取ID
            if create_new_session:
                from backend.crud.chat import create_chat
                from backend.schemas.chat import ChatCreate
                
                # 预创建会话
                chat_data = ChatCreate(title="新对话")
                new_chat = await create_chat(db, current_user.id, chat_data=chat_data, agent_id=agent_id)
                conversation_id = new_chat.id
                
                # 更新请求中的会话ID
                chat_request.conversation_id = conversation_id
                
                api_logger.info(f"预创建新会话: conversation_id={conversation_id}")
                
                # 如果有笔记ID，立即关联到会话
                if note_id:
                    from backend.models.note import Note
                    from sqlalchemy import select
                    
                    note_stmt = select(Note).where(
                        Note.id == note_id,
                        Note.user_id == current_user.id,
                        Note.is_deleted == False
                    )
                    note_result = await db.execute(note_stmt)
                    note = note_result.scalar_one_or_none()
                    
                    if note:
                        note.session_id = conversation_id
                        await db.commit()
                        api_logger.info(f"笔记ID {note_id} 已关联到预创建会话ID {conversation_id}")
            
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
                        # 四元组：(content, conversation_id, reasoning_content, tool_status)
                        content, stream_conversation_id, reasoning_content, tool_status = chunk_data
                        if stream_conversation_id and conversation_id is None:
                            conversation_id = stream_conversation_id
                    elif len(chunk_data) == 3:
                        # 三元组处理
                        first, second, third = chunk_data
                        if isinstance(second, int):
                            # (content, conversation_id, reasoning_content) 或 (content, conversation_id, tool_status)
                            if isinstance(third, str):
                                # (content, conversation_id, reasoning_content)
                                content, stream_conversation_id, reasoning_content = first, second, third
                            elif isinstance(third, dict) and third.get("type") in ["tool_call_executing", "tool_call_completed", "tool_call_error", "tools_completed"]:
                                # (content, conversation_id, tool_status)
                                content, stream_conversation_id, tool_status = first, second, third
                            else:
                                # 默认处理为 (content, conversation_id, tool_status)
                                content, stream_conversation_id, tool_status = first, second, third
                            
                            if stream_conversation_id and conversation_id is None:
                                conversation_id = stream_conversation_id
                        else:
                            # 如果第二个参数不是int，那很可能是错误的数据格式
                            # 记录警告并按照原来的逻辑处理
                            api_logger.warning(f"检测到异常的三元组格式: first={type(first)}, second={type(second)}, third={type(third)}")
                            # 保守处理：只取第一个作为content
                            content = first
                    elif len(chunk_data) == 2:
                        # 二元组：可能是 (content, conversation_id) 或 (content, reasoning_content)
                        first, second = chunk_data
                        if isinstance(second, int):
                            # (content, conversation_id)
                            content, stream_conversation_id = first, second
                            if stream_conversation_id and conversation_id is None:
                                conversation_id = stream_conversation_id
                        elif isinstance(second, str):
                            # (content, reasoning_content) - reasoning_content应该是字符串
                            content, reasoning_content = first, second
                        elif isinstance(second, dict) and second.get("type") in ["tool_call_executing", "tool_call_completed", "tool_call_error", "tools_completed"]:
                            # 这应该是工具状态被错误地当作reasoning_content的情况
                            # 实际上应该是 (content, tool_status)，但这种格式不应该存在
                            # 记录日志并将其当作tool_status处理
                            api_logger.warning(f"检测到可能的数据格式错误：工具状态被放在二元组的第二位: {second}")
                            content = first
                            tool_status = second
                        else:
                            # 其他情况，当作reasoning_content处理，但转换为字符串
                            content, reasoning_content = first, str(second)
                else:
                    # 单个内容
                    content = chunk_data
                
                # 累积内容
                if content:
                    full_content += content
                if reasoning_content:
                    # 可以选择是否将思考内容也累积到完整内容中
                    # 这里单独记录但不加入到最终显示内容中
                    pass
                
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
                            "conversation_id": conversation_id or 0,
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
                    # 确保reasoning_content是字符串类型
                    if reasoning_content and not isinstance(reasoning_content, str):
                        api_logger.warning(f"reasoning_content不是字符串类型: {type(reasoning_content)}, 内容: {reasoning_content}")
                        reasoning_content = ""  # 重置为空字符串
                    
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
                            "conversation_id": conversation_id or 0,
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
                    "conversation_id": conversation_id or 0,
                    "done": True,
                    "agent_info": agent_info
                },
                "errors": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "request_id": request_id
            }
            
            yield f"data: {json.dumps(final_response_data, ensure_ascii=False)}\n\n"
            
            api_logger.info(f"流式聊天完成: conversation_id={conversation_id}, content_length={len(full_content)}")
            
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
                    "conversation_id": conversation_id or 0,
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


@router.post("/clear-memory/{conversation_id}")
async def clear_chat_memory(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    current_user: User = Depends(get_current_active_user),
):
    """
    清空指定会话的记忆上下文
    """
    api_logger.info(f"清空会话记忆: conversation_id={conversation_id}, user={current_user.username}")
    
    await clear_memory(conversation_id)
    
    return SuccessResponse(
        data={"success": True},
        msg="清空会话记忆成功",
        request_id=getattr(request.state, "request_id", None)
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
    获取当前用户的所有聊天会话，支持分页
    """
    api_logger.info(f"获取用户聊天会话列表: {current_user.username}, page={page}, page_size={page_size}")
    
    # 计算跳过的记录数
    skip = (page - 1) * page_size
    
    # 从数据库获取会话列表和总数，不自动加载消息
    chats, total = await get_user_chats(db, current_user.id, skip, page_size)
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    # 转换为响应格式
    result = []
    for chat in chats:
        # 单独查询每个会话的消息数量和最后一条消息
        chat_messages = await get_chat_messages(db, chat.id)
        message_count = len(chat_messages) if chat_messages else 0
        
        # 获取最后一条消息内容
        last_message = None
        if message_count > 0:
            content = chat_messages[-1].content
            if len(content) > 30:
                last_message = content[:30] + "..."
            else:
                last_message = content
        
        result.append({
            "id": chat.id,
            "title": chat.title,
            "agent_id": chat.agent_id,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            "message_count": message_count,
            "last_message": last_message
        })
    
    # 构建分页响应
    pagination_response = {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": total_pages
    }
    
    return SuccessResponse(
        data=pagination_response,
        msg="获取聊天会话列表成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/sessions/{conversation_id}", response_model=ChatResponseModel)
async def get_chat_session(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取指定聊天会话的详情和消息
    """
    api_logger.info(f"获取聊天会话详情: conversation_id={conversation_id}, user={current_user.username}")
    
    # 获取会话基本信息
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != current_user.id:
        api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
        return SuccessResponse(
            data=None,
            msg="聊天会话不存在或无权访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 获取会话的消息列表
    chat_messages = await get_chat_messages(db, conversation_id)
    
    # 构建消息列表，包含工具调用信息
    messages = []
    for msg in chat_messages:
        # 获取Agent信息
        agent_info = None
        if msg.agent_id:
            agent_info = {
                "id": msg.agent_id,
                "name": "默认助手",  # 这里可以根据需要从数据库获取真实的agent信息
                "avatar": None
            }
        
        # 检查消息内容是否是JSON结构（包含interaction_flow）
        tool_calls_data = []
        is_json_structure = False
        
        if msg.role == "assistant" and msg.content:
            try:
                import json
                parsed_content = json.loads(msg.content)
                if (isinstance(parsed_content, dict) and 
                    parsed_content.get("type") == "agent_response" and 
                    "interaction_flow" in parsed_content):
                    is_json_structure = True
                    api_logger.debug(f"消息 {msg.id} 包含JSON结构，跳过tool_calls_data查询")
            except (json.JSONDecodeError, TypeError):
                # 不是JSON结构，继续正常处理
                pass
        
        # 只有在消息内容不是JSON结构时，才查询并添加tool_calls_data
        if not is_json_structure:
            from backend.crud.tool_call import get_tool_calls_by_message
            tool_calls = await get_tool_calls_by_message(db, msg.id)
            
            # 转换工具调用数据格式
            for tool_call in tool_calls:
                tool_calls_data.append({
                    "id": tool_call.id,
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "function_name": tool_call.function_name,
                    "arguments": tool_call.arguments,
                    "status": tool_call.status,
                    "result": tool_call.result,
                    "error_message": tool_call.error_message,
                    "started_at": tool_call.started_at.isoformat() if tool_call.started_at else None,
                    "completed_at": tool_call.completed_at.isoformat() if tool_call.completed_at else None
                })
        
        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "tokens": msg.tokens,
            "agent_id": msg.agent_id,
            "agent_info": agent_info,
            # 工具调用相关字段 - 从新的数据结构获取
            "tool_calls_data": tool_calls_data
        })
    
    result = {
        "id": chat.id,
        "user_id": chat.user_id,
        "agent_id": chat.agent_id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
        "messages": messages
    }
    
    return SuccessResponse(
        data=result,
        msg="获取聊天会话详情成功",
        request_id=getattr(request.state, "request_id", None)
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
            
            # 查询笔记是否存在
            stmt = select(Note).where(
                Note.id == chat_data.note_id,
                Note.user_id == current_user.id,
                Note.is_deleted == False
            )
            note_result = await db.execute(stmt)
            note = note_result.scalar_one_or_none()
            
            if note:
                note.session_id = new_chat.id
                await db.commit()
                api_logger.info(f"笔记ID {chat_data.note_id} 已关联到会话ID {new_chat.id}")
        
        return SuccessResponse(
            data={
                "id": new_chat.id,
                "title": new_chat.title,
                "user_id": new_chat.user_id,
                "created_at": new_chat.created_at.isoformat() if new_chat.created_at else None,
                "updated_at": new_chat.updated_at.isoformat() if new_chat.updated_at else None
            },
            request_id=getattr(request.state, "request_id", None)
        )
    except Exception as e:
        api_logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{conversation_id}", response_model=ChatResponseModel)
async def update_chat_session(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    chat_data: ChatUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新聊天会话信息
    """
    api_logger.info(f"更新聊天会话: conversation_id={conversation_id}, user={current_user.username}")
    
    # 验证会话存在且属于当前用户
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != current_user.id:
        api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
        return SuccessResponse(
            data=None,
            msg="聊天会话不存在或无权访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 更新标题
    updated_chat = await update_chat_title(db, conversation_id, chat_data.title)
    
    result = {
        "id": updated_chat.id,
        "user_id": updated_chat.user_id,
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


@router.delete("/sessions/{conversation_id}")
async def delete_chat_session(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    删除聊天会话
    """
    api_logger.info(f"删除聊天会话: conversation_id={conversation_id}, user={current_user.username}")
    
    # 验证会话存在且属于当前用户
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != current_user.id:
        api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
        return SuccessResponse(
            data=None,
            msg="聊天会话不存在或无权访问",
            request_id=getattr(request.state, "request_id", None)
        )
    
    # 软删除会话
    success = await soft_delete_chat(db, conversation_id)
    
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


@router.get("/memory/{conversation_id}")
async def get_memory_content(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定会话在Redis中的记忆内容
    """
    api_logger.info(f"获取会话记忆内容: conversation_id={conversation_id}, user={current_user.username}")
    
    try:
        # 获取会话基本信息（验证用户权限）
        chat = await get_chat(db, conversation_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
            return SuccessResponse(
                data=None,
                msg="聊天会话不存在或无权访问",
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 获取会话记忆内容
        messages = memory_service.get_messages(conversation_id)
        
        # 计算记忆统计信息
        stats = {
            "message_count": len(messages),
            "user_messages": sum(1 for msg in messages if msg.get("role") == "user"),
            "assistant_messages": sum(1 for msg in messages if msg.get("role") == "assistant"),
            "total_tokens_estimate": sum(len(msg.get("content", "")) // 4 for msg in messages)  # 粗略估计
        }
        
        result = {
            "conversation_id": conversation_id,
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


@router.post("/restore-memory/{conversation_id}")
async def restore_chat_memory(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    从数据库恢复指定会话的记忆上下文到Redis
    """
    api_logger.info(f"恢复会话记忆: conversation_id={conversation_id}, user={current_user.username}")
    
    try:
        # 验证会话存在且属于当前用户
        chat = await get_chat(db, conversation_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
            return SuccessResponse(
                data={"success": False, "message": "聊天会话不存在或无权访问"},
                msg="恢复会话记忆失败",
                request_id=getattr(request.state, "request_id", None)
            )
        
        try:
            # 查询历史消息
            db_messages = await get_chat_messages(db, conversation_id)
            
            # 清除现有记忆
            memory_service.clear_memory(conversation_id)
            
            # 格式化消息并恢复到Redis
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in db_messages
                if not msg.is_deleted
            ]
            
            # 获取用户当前的记忆会话数量
            memory_count = memory_service.count_user_memories(current_user.id)
            
            # 恢复记忆，传递用户ID进行管理
            restored = memory_service.restore_memory_from_db(conversation_id, formatted_messages, current_user.id)
            
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
        # 获取用户的记忆会话ID列表
        memory_ids = memory_service.get_user_memory_sessions(current_user.id)
        
        # 从数据库获取会话详情
        sessions = []
        for mem_id in memory_ids:
            try:
                chat = await get_chat(db, mem_id)
                if chat and chat.user_id == current_user.id:
                    messages_count = len(memory_service.get_messages(mem_id))
                    sessions.append({
                        "id": chat.id,
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


@router.post("/ask-again/{conversation_id}")
async def ask_again(
    request: Request,
    conversation_id: int = Path(..., description="聊天会话ID"),
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
    api_logger.info(f"用户请求编辑消息: conversation_id={conversation_id}, message_index={ask_request.message_index}, " +
                   f"is_user_message={ask_request.is_user_message}, rerun={ask_request.rerun}, user={current_user.username}")
    
    try:
        # 验证会话存在且属于当前用户
        chat = await get_chat(db, conversation_id)
        if not chat or chat.user_id != current_user.id:
            api_logger.warning(f"聊天会话不存在或无权访问: conversation_id={conversation_id}, user={current_user.username}")
            return SuccessResponse(
                data=None,
                msg="聊天会话不存在或无权访问",
                request_id=getattr(request.state, "request_id", None)
            )
            
        # 获取消息列表，验证消息ID是否存在
        db_messages = await get_chat_messages(db, conversation_id)
        db_message_ids = [msg.id for msg in db_messages]
        
        # 查找指定消息在数据库中的角色
        target_message_id = None  # 要软删除的起始消息ID
        
        if ask_request.message_index in db_message_ids:
            # 获取消息的ID
            message_index_in_db = db_message_ids.index(ask_request.message_index)
            if message_index_in_db < len(db_messages):
                # 获取目标消息对象
                target_message = db_messages[message_index_in_db]
                target_message_id = ask_request.message_index
                
                # 检查消息角色与请求中的is_user_message是否一致
                is_user_role = target_message.role == "user"
                if is_user_role != ask_request.is_user_message:
                    api_logger.warning(f"消息角色与请求不一致: 数据库角色={target_message.role}, 请求is_user_message={ask_request.is_user_message}")
                    return SuccessResponse(
                        data={"success": False},
                        msg="消息角色与请求不匹配",
                        request_id=getattr(request.state, "request_id", None)
                    )
        
        # 检查message_index是否是数据库中的消息ID
        if ask_request.message_index in db_message_ids:
            # 是数据库消息ID，找出它在聊天中的位置
            message_position = db_message_ids.index(ask_request.message_index)
            # 获取当前Redis中的记忆状态，查看消息数是否匹配
            memory_messages = memory_service.get_messages(conversation_id)
            
            # 检查Redis中的记忆是否存在或是否有足够的消息
            if not memory_messages or len(memory_messages) == 0:
                api_logger.warning(f"会话 {conversation_id} 在Redis中没有记忆，尝试恢复记忆")
                
                # 尝试将数据库消息恢复到Redis
                formatted_messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in db_messages
                    if not msg.is_deleted
                ]
                
                restored = memory_service.restore_memory_from_db(conversation_id, formatted_messages, current_user.id)
                if not restored:
                    return SuccessResponse(
                        data={"success": False},
                        msg="消息编辑失败，无法恢复聊天记忆",
                        request_id=getattr(request.state, "request_id", None)
                    )
                
                # 重新获取Redis中的消息
                memory_messages = memory_service.get_messages(conversation_id)
            
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
                    # 记录要删除的消息数量（编辑点之后的所有消息）
                    messages_to_remove = len(memory_messages) - memory_index if memory_index < len(memory_messages) else 0
                    
                    # 替换消息并截断该消息之后的所有记忆
                    if not ask_request.content:
                        # 如果没有提供新内容，使用原消息内容
                        original_content = db_messages[message_position].content
                        result = await replace_message_and_truncate(conversation_id, memory_index, original_content, target_role)
                    else:
                        # 使用新的内容替换
                        result = await replace_message_and_truncate(conversation_id, memory_index, ask_request.content, target_role)
                else:  # 仅编辑不重新执行
                    # 不需要截断记忆，仅替换指定消息内容
                    result = memory_service.update_message_content(
                        conversation_id, 
                        memory_index, 
                        ask_request.content or db_messages[message_position].content
                    )
            else:  # 编辑AI回复
                # 找到AI回复消息的位置
                if target_role != "assistant":
                    api_logger.warning(f"尝试编辑非AI回复消息: message_id={ask_request.message_index}, role={target_role}")
                    return SuccessResponse(
                        data={"success": False},
                        msg="只能编辑AI回复消息",
                        request_id=getattr(request.state, "request_id", None)
                    )
                
                # 仅编辑内容，不重新执行
                result = memory_service.update_message_content(
                    conversation_id, 
                    memory_index, 
                    ask_request.content or db_messages[message_position].content
                )
        else:
            # 直接作为记忆索引使用
            api_logger.info(f"直接使用 {ask_request.message_index} 作为记忆索引")
            memory_messages = memory_service.get_messages(conversation_id)
            
            # 检查记忆索引是否有效
            if ask_request.message_index < 0 or ask_request.message_index >= len(memory_messages):
                return SuccessResponse(
                    data={"success": False},
                    msg="无效的记忆消息索引",
                    request_id=getattr(request.state, "request_id", None)
                )
            
            # 获取目标消息角色
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
            
            # 根据操作类型处理不同情况
            if ask_request.is_user_message:  # 编辑用户消息
                if ask_request.rerun:  # 需要重新执行
                    # 记录要删除的消息数量
                    messages_to_remove = len(memory_messages) - ask_request.message_index if ask_request.message_index < len(memory_messages) else 0
                    
                    # 替换消息并截断
                    if not ask_request.content:
                        # 如果没有提供新内容，使用原消息内容
                        original_content = memory_messages[ask_request.message_index]["content"]
                        result = await replace_message_and_truncate(conversation_id, ask_request.message_index, original_content, target_role)
                    else:
                        result = await replace_message_and_truncate(conversation_id, ask_request.message_index, ask_request.content, target_role)
                else:  # 仅编辑不重新执行
                    # 不需要截断记忆，仅替换指定消息内容
                    new_content = ask_request.content or memory_messages[ask_request.message_index]["content"]
                    result = memory_service.update_message_content(conversation_id, ask_request.message_index, new_content)
                    messages_to_remove = 0
            else:  # 编辑AI回复
                # 检查是否为AI回复消息
                if target_role != "assistant":
                    api_logger.warning(f"尝试编辑非AI回复消息: memory_index={ask_request.message_index}, role={target_role}")
                    return SuccessResponse(
                        data={"success": False},
                        msg="只能编辑AI回复消息",
                        request_id=getattr(request.state, "request_id", None)
                    )
                
                # 仅编辑内容，不重新执行
                new_content = ask_request.content or memory_messages[ask_request.message_index]["content"]
                result = memory_service.update_message_content(conversation_id, ask_request.message_index, new_content)
                messages_to_remove = 0
        
        if not result:
            return SuccessResponse(
                data={"success": False},
                msg="编辑消息失败",
                request_id=getattr(request.state, "request_id", None)
            )
        
        api_logger.info(f"会话 {conversation_id} 已编辑消息" + 
                        (f"并截断记忆，删除 {messages_to_remove} 条后续消息" if messages_to_remove > 0 else ""))
        
        # 如果找到了要操作的数据库消息ID，在需要重新执行时执行软删除操作
        db_deleted_count = 0
        if target_message_id and ask_request.is_user_message and ask_request.rerun:
            # 软删除指定消息ID之后的所有消息
            db_deleted_count = await soft_delete_messages_after(db, conversation_id, target_message_id)
            api_logger.info(f"已在数据库中软删除 {db_deleted_count} 条消息，从ID {target_message_id} 开始")
        
        # 如果重新执行，并且提供了新内容，则立即发送新消息
        if ask_request.is_user_message and ask_request.rerun and ask_request.content:
            # 创建聊天请求
            chat_request = ChatRequest(
                content=ask_request.content,
                stream=ask_request.stream,
                conversation_id=conversation_id,
                agent_id=ask_request.agent_id
            )
            
            # 获取Agent信息
            agent_id = ask_request.agent_id
            agent_info = None
            
            if agent_id and db:
                from backend.crud.agent import agent as agent_crud
                agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=current_user.id)
                if agent:
                    agent_info = {
                        "id": agent.id,
                        "name": agent.name,
                        "avatar_url": agent.avatar_url,
                        "model": agent.model
                    }
            
            # 如果是流式请求
            if chat_request.stream:
                return await stream_chat(request, chat_request, db, current_user)
            
            # 非流式请求
            response = await generate_chat_response(
                chat_request=chat_request,
                db=db,
                user_id=current_user.id
            )
            
            api_logger.info(f"编辑并重新发送消息完成: {current_user.username}, 会话ID: {response.conversation_id}")
            
            # 将Pydantic模型转换为dict
            response_dict = {
                "message": {
                    "content": response.message.content
                },
                "usage": response.usage,
                "conversation_id": response.conversation_id,
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
        
        # 如果没有需要重新执行，则仅返回编辑结果
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


@router.get("/{conversation_id}/history", response_model=List[ChatMessageResponse])
async def get_chat_history_endpoint(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取聊天历史记录"""
    api_logger.info(f"获取聊天历史: conversation_id={conversation_id}, user_id={current_user.id}")
    
    # 验证会话存在且属于当前用户
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="聊天会话不存在或无权访问"
        )
    
    # 获取聊天消息
    messages = await get_chat_messages(db, conversation_id)
    
    # 为每个消息加载工具调用信息
    from backend.crud.tool_call import get_tool_calls_by_message
    
    result = []
    for msg in messages:
        # 获取消息的工具调用记录
        tool_calls = await get_tool_calls_by_message(db, msg.id)
        
        # 转换为响应格式
        message_data = {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "tokens": msg.tokens,
            "prompt_tokens": msg.prompt_tokens,
            "total_tokens": msg.total_tokens,
            "agent_id": msg.agent_id,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
            "tool_calls": [
                {
                    "id": tc.id,
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