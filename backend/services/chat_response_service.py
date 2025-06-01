from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import aiohttp
import base64

from backend.schemas.chat import Message, ChatRequest, ChatCompletionResponse
from backend.utils.logging import api_logger
from backend.crud.chat import create_chat, get_chat, add_message, update_chat_agent
from backend.crud.agent import agent as agent_crud
from backend.services.memory import memory_service
from backend.services.openai_client import openai_client_service
from backend.services.chat_tool_handler import chat_tool_handler
from backend.services.chat_tool_processor import chat_tool_processor
from backend.services.chat_session_manager import chat_session_manager


class ChatResponseService:
    """聊天响应服务"""
    
    @staticmethod
    async def _process_tool_calls_with_interaction_flow_non_stream(
        content: str,
        tool_calls: List[Any],
        messages: List[Dict[str, Any]],
        agent,
        use_model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        tools: List[Dict[str, Any]],
        has_tools: bool,
        conversation_id: int,
        db: Optional[AsyncSession] = None,
        message_id: Optional[int] = None,
        interaction_flow: List[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> str:
        """
        处理工具调用并记录到交互流程中（非流式版本）
        """
        if interaction_flow is None:
            interaction_flow = []
        
        # 如果有初始内容，先记录到交互流程
        if content and content.strip():
            interaction_flow.append({
                "type": "text",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
        
        # 处理工具调用
        if tool_calls:
            api_logger.info(f"检测到工具调用请求: {len(tool_calls)} 个工具调用")
            
            # 处理工具调用
            tool_results, tool_calls_data = await chat_tool_handler.handle_tool_calls(
                tool_calls, 
                agent, 
                db, 
                conversation_id,
                message_id=message_id,
                user_id=user_id
            )
            
            # 记录工具调用到交互流程
            for i, tool_call in enumerate(tool_calls):
                tool_call_record = {
                    "type": "tool_call",
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                    "status": "completed",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat()
                }
                
                # 添加结果
                if i < len(tool_results):
                    try:
                        tool_call_record["result"] = json.loads(tool_results[i]["content"])
                    except (json.JSONDecodeError, KeyError):
                        tool_call_record["result"] = tool_results[i]["content"]
                
                interaction_flow.append(tool_call_record)
            
            # 将工具调用和结果添加到消息列表
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls
                ]
            })
            
            # 添加工具结果
            for tool_result in tool_results:
                messages.append(tool_result)
            
            # 递归处理工具调用
            final_content = await chat_tool_processor.process_tool_calls_recursively(
                content, 
                [
                    {
                        'id': tc.id,
                        'type': tc.type,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    } for tc in tool_calls
                ], 
                messages, 
                agent, 
                use_model, 
                max_tokens, 
                temperature, 
                top_p, 
                tools, 
                has_tools, 
                conversation_id,
                db,
                message_id=message_id
            )
            
            # 如果有额外的内容，记录到交互流程
            additional_content = final_content[len(content):] if len(final_content) > len(content) else ""
            if additional_content.strip():
                interaction_flow.append({
                    "type": "text",
                    "content": additional_content,
                    "timestamp": datetime.now().isoformat()
                })
            
            return final_content
        
        return content
    
    @staticmethod
    async def generate_chat_response(
        chat_request: ChatRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None
    ) -> ChatCompletionResponse:
        """
        调用OpenAI API生成对话响应，并保存对话记录
        """
        try:
            api_logger.info(f"开始调用OpenAI API, 模型: {openai_client_service.model}, API地址: {openai_client_service.async_client.base_url}")
            
            # 获取或确认聊天会话ID
            conversation_id = chat_request.conversation_id
            
            # 获取Agent信息
            agent_id = chat_request.agent_id
            current_agent = None
            
            # 设置默认参数
            use_model = openai_client_service.model
            max_tokens = 4000
            temperature = 0.7
            top_p = 1.0
            
            if agent_id and db:
                # 获取Agent信息
                current_agent = await agent_crud.get_agent_for_user(db, agent_id=agent_id, user_id=user_id)
                if not current_agent:
                    api_logger.warning(f"Agent不存在或无权访问: agent_id={agent_id}, user_id={user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Agent不存在或无权访问"
                    )
                api_logger.info(f"使用Agent: {current_agent.name}, ID={current_agent.id}")
            
            # 会话创建或验证
            if db and user_id:
                # 获取或创建聊天会话
                if not conversation_id:
                    # 创建新的聊天会话
                    if hasattr(chat_request, "note_id") and chat_request.note_id:
                        # 查询笔记信息，获取标题
                        from backend.models.note import Note
                        from sqlalchemy import select
                        
                        # 查询笔记是否存在
                        note_stmt = select(Note).where(
                            Note.id == chat_request.note_id,
                            Note.user_id == user_id,
                            Note.is_deleted == False
                        )
                        note_result = await db.execute(note_stmt)
                        note = note_result.scalar_one_or_none()
                        
                        # 创建聊天对象并传递note_id
                        from backend.schemas.chat import ChatCreate
                        
                        # 不使用笔记标题，让系统自动生成会话标题
                        chat_data = ChatCreate(title="新对话")
                        api_logger.info(f"从笔记创建新会话，使用默认标题'新对话'，后续将自动生成")
                        
                        chat = await create_chat(db, user_id, chat_data=chat_data, agent_id=agent_id)
                        
                        # 如果创建成功，将会话ID关联到笔记
                        if chat and chat_request.note_id and note:
                            note.session_id = chat.id
                            await db.commit()
                            api_logger.info(f"笔记ID {chat_request.note_id} 已关联到会话ID {chat.id}")
                    else:
                        # 常规创建会话
                        chat = await create_chat(db, user_id, agent_id=agent_id)
                        
                    conversation_id = chat.id
                    api_logger.info(f"创建新聊天会话: conversation_id={conversation_id}, user_id={user_id}, agent_id={agent_id}")
                else:
                    # 验证会话存在且属于当前用户
                    chat = await get_chat(db, conversation_id)
                    if not chat or chat.user_id != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="聊天会话不存在或无权访问"
                        )
                    
                    # 如果当前会话没有关联Agent，但请求中有Agent，则更新会话
                    if agent_id and not chat.agent_id:
                        await update_chat_agent(db, conversation_id=conversation_id, agent_id=agent_id)
                        api_logger.info(f"更新会话的Agent: conversation_id={conversation_id}, agent_id={agent_id}")
                    
                    # 如果当前会话已关联Agent，使用该Agent的信息
                    elif chat.agent_id and not agent_id:
                        agent_id = chat.agent_id
                        current_agent = await agent_crud.get_agent_by_id(db, agent_id=agent_id)
                        if current_agent:
                            api_logger.info(f"从会话加载Agent: {current_agent.name}, ID={current_agent.id}")
            
            # 获取用户发送的内容
            user_content = chat_request.content
            
            # 处理图片消息 - 构建包含图片的消息格式
            user_message_content = []
            
            # 添加文本内容
            if user_content and user_content.strip():
                user_message_content.append({
                    "type": "text",
                    "text": user_content
                })
            
            # 添加图片内容
            if hasattr(chat_request, 'images') and chat_request.images:
                for image in chat_request.images:
                    try:
                        # 尝试下载图片并转换为base64
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image.url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                                if response.status == 200:
                                    image_data = await response.read()
                                    # 检测图片格式
                                    content_type = response.headers.get('content-type', 'image/png')
                                    if 'image/' in content_type:
                                        image_format = content_type.split('/')[-1]
                                    else:
                                        image_format = 'png'  # 默认格式
                                    
                                    # 转换为base64
                                    base64_image = base64.b64encode(image_data).decode('utf-8')
                                    data_url = f"data:{content_type};base64,{base64_image}"
                                    
                                    user_message_content.append({
                                        "type": "image_url",
                                        "image_url": {
                                            "url": data_url,
                                            "detail": "high"  # 使用高细节模式
                                        }
                                    })
                                    api_logger.info(f"成功转换图片为base64格式: {image.name}, 大小: {len(image_data)} 字节")
                                else:
                                    api_logger.error(f"下载图片失败，状态码: {response.status}, URL: {image.url}")
                                    # 如果下载失败，仍然尝试使用原URL
                                    user_message_content.append({
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image.url,
                                            "detail": "high"
                                        }
                                    })
                    except Exception as download_error:
                        api_logger.error(f"下载图片时发生错误: {str(download_error)}, URL: {image.url}")
                        # 如果转换失败，回退到原URL
                        user_message_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image.url,
                                "detail": "high"
                            }
                        })
                
                api_logger.info(f"用户消息包含 {len(chat_request.images)} 张图片，已尝试转换为base64格式")
            
            # 构建最终的用户消息
            if len(user_message_content) > 1:  # 有图片或多个内容元素
                final_user_message = user_message_content
                # 用于记忆和数据库的纯文本内容
                content_for_memory = user_content
                if hasattr(chat_request, 'images') and chat_request.images:
                    image_info = f" [包含{len(chat_request.images)}张图片]"
                    content_for_memory = (user_content + image_info) if user_content else f"发送了{len(chat_request.images)}张图片"
            else:  # 只有文本
                final_user_message = user_content
                content_for_memory = user_content
            
            # 将用户消息添加到记忆中（使用纯文本格式）
            memory_service.add_user_message(conversation_id, content_for_memory, user_id)
            
            # 保存用户消息到数据库（保存完整的图片信息）
            if db and user_id and conversation_id:
                # 构建完整的消息内容，包含图片信息
                if hasattr(chat_request, 'images') and chat_request.images:
                    # 构建包含图片和文本的完整消息结构
                    full_message_content = {
                        "type": "user_message",
                        "text_content": user_content,
                        "images": [
                            {
                                "url": image.url,
                                "name": image.name,
                                "size": image.size
                            } for image in chat_request.images
                        ]
                    }
                    # 保存JSON格式的完整消息
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=json.dumps(full_message_content, ensure_ascii=False)
                    )
                    api_logger.info(f"保存包含{len(chat_request.images)}张图片的用户消息到数据库")
                else:
                    # 纯文本消息，直接保存
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=content_for_memory
                    )
            
            # 从记忆服务获取完整的消息记录
            messages = memory_service.get_messages(conversation_id)
            
            # 如果当前请求包含图片，需要替换最后一条用户消息为包含图片的格式
            if hasattr(chat_request, 'images') and chat_request.images and len(user_message_content) > 1:
                api_logger.info(f"检测到图片消息，准备替换最后一条用户消息格式")
                
                # 找到最后一条用户消息并替换为包含图片的格式
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        api_logger.info(f"替换用户消息索引 {i}，原内容: {str(messages[i]['content'])[:50]}...")
                        messages[i]["content"] = final_user_message
                        api_logger.info(f"替换后的消息格式: {json.dumps(final_user_message, ensure_ascii=False)[:200]}...")
                        break
                else:
                    api_logger.warning("未找到用户消息进行图片格式替换")
            else:
                api_logger.info("当前请求不包含图片或图片数据为空")
                
            # 记录最终发送给AI模型的消息格式
            if hasattr(chat_request, 'images') and chat_request.images:
                # 安全地记录消息格式，避免过长的日志
                api_logger.info(f"准备发送给AI模型的消息数量: {len(messages)}")
                for idx, msg in enumerate(messages):
                    if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                        api_logger.info(f"消息 {idx} (用户): 复杂格式，包含 {len(msg['content'])} 个元素")
                        for elem_idx, elem in enumerate(msg["content"]):
                            if isinstance(elem, dict):
                                if elem.get("type") == "text":
                                    api_logger.info(f"  元素 {elem_idx}: 文本 - {elem.get('text', '')[:50]}...")
                                elif elem.get("type") == "image_url":
                                    api_logger.info(f"  元素 {elem_idx}: 图片 - URL: {elem.get('image_url', {}).get('url', 'unknown')}")
                    else:
                        content_preview = str(msg.get("content", ""))[:50]
                        api_logger.info(f"消息 {idx} ({msg.get('role', 'unknown')}): {content_preview}...")
            
            # 添加Agent的系统提示词
            if current_agent and current_agent.system_prompt:
                # 在消息开头添加系统提示
                system_prompt = {"role": "system", "content": current_agent.system_prompt}
                messages.insert(0, system_prompt)
                api_logger.info(f"添加Agent系统提示词: {current_agent.system_prompt[:30]}...")
            
            api_logger.debug(f"请求消息: {json.dumps(messages, ensure_ascii=False)}")
            
            # 如果有Agent，使用Agent的设置
            if current_agent:
                # 优先使用请求中的模型，如果没有提供则使用Agent的默认模型
                if chat_request.model:
                    use_model = chat_request.model
                    api_logger.info(f"使用请求中指定的模型: {use_model}")
                else:
                    # 先备份使用默认模型，以防指定模型不可用
                    agent_model = current_agent.model
                    use_model = agent_model if agent_model else openai_client_service.model
                    api_logger.info(f"使用Agent默认模型: {use_model}")
                
                # 如果Agent有模型设置，使用Agent的模型设置
                if current_agent.model_settings:
                    model_settings = current_agent.model_settings
                    # 确保model_settings是字典
                    if not isinstance(model_settings, dict) and hasattr(model_settings, "dict"):
                        model_settings = model_settings.dict()
                    elif not isinstance(model_settings, dict):
                        model_settings = {}
                    
                    if "temperature" in model_settings:
                        temperature = model_settings["temperature"]
                    if "top_p" in model_settings:
                        top_p = model_settings["top_p"]
                    if "max_tokens" in model_settings:
                        max_tokens = model_settings["max_tokens"]
                
                api_logger.info(f"使用Agent模型设置: model={use_model}, temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
            elif chat_request.model:
                # 如果没有Agent但请求中指定了模型，使用请求中的模型
                use_model = chat_request.model
                api_logger.info(f"没有Agent，使用请求中指定的模型: {use_model}")
            else:
                # 都没有则使用默认模型
                api_logger.info(f"使用系统默认模型: {use_model}")
            
            # 获取工具配置
            tools = chat_tool_handler.get_agent_tools(current_agent) if current_agent else []
            has_tools = len(tools) > 0
            api_logger.info(f"当前聊天启用工具: {has_tools}, 工具数量: {len(tools)}")
            
            # 调用API - 尝试直接使用异步客户端
            try:
                api_logger.info(f"使用异步客户端调用API - URL: {openai_client_service.async_client.base_url}")
                
                # 准备API调用参数
                api_params = {
                    "model": use_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": False
                }
                
                # 如果有工具，添加工具配置
                if has_tools:
                    api_params["tools"] = tools
                
                # 记录请求参数详情
                api_logger.info(f"[大模型请求] API调用参数详情: model={use_model}, max_tokens={max_tokens}, temperature={temperature}, 消息数量={len(messages)}, 启用工具={has_tools}")
                
                # 调用API
                response = await openai_client_service.async_client.chat.completions.create(**api_params)
                
                api_logger.info(f"[大模型响应] API响应类型: {type(response)}")
                
                # 检查响应类型
                if isinstance(response, str):
                    api_logger.error(f"API返回了字符串而不是对象: {response}")
                    raise ValueError(f"API返回了错误格式: {response}")
                
                # 检查是否有工具调用
                assistant_message = response.choices[0].message
                tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
                
                # 初始化交互流程记录
                interaction_flow = []
                
                # 如果有工具调用
                if tool_calls:
                    api_logger.info(f"检测到工具调用请求: {len(tool_calls)} 个工具调用")
                    
                    # 先保存AI消息（不包含工具调用数据）
                    ai_message = None
                    if db and user_id and conversation_id:
                        ai_message = await add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=assistant_message.content or "",
                            agent_id=agent_id
                        )
                    
                    # 使用新的交互流程处理方法
                    final_assistant_content = await ChatResponseService._process_tool_calls_with_interaction_flow_non_stream(
                        assistant_message.content or "",
                        tool_calls,
                        messages,
                        current_agent,
                        use_model,
                        max_tokens,
                        temperature,
                        top_p,
                        tools,
                        has_tools,
                        conversation_id,
                        db,
                        ai_message.id if ai_message else None,
                        interaction_flow,
                        user_id
                    )
                    
                    # 估算token使用量（因为递归调用可能无法准确获取）
                    estimated_tokens = len(final_assistant_content) // 4
                    estimated_prompt_tokens = len(str(messages)) // 4
                    estimated_total_tokens = estimated_tokens + estimated_prompt_tokens
                    
                    # 构建最终的JSON结构
                    final_json_content = {
                        "type": "agent_response",
                        "interaction_flow": interaction_flow
                    }
                    
                    # 将最终的助手消息添加到记忆中（使用纯文本）
                    memory_service.add_assistant_message(conversation_id, final_assistant_content, user_id)
                    
                    # 更新AI消息的内容为JSON结构
                    if ai_message:
                        ai_message.content = json.dumps(final_json_content, ensure_ascii=False)
                        ai_message.tokens = estimated_tokens
                        ai_message.prompt_tokens = estimated_prompt_tokens
                        ai_message.total_tokens = estimated_total_tokens
                        await db.commit()
                        await db.refresh(ai_message)
                    
                    api_logger.info(f"递归工具调用完成，最终响应长度: {len(final_assistant_content)}")
                    
                    # 使用最终内容和估算的token数量
                    assistant_content = final_assistant_content
                    token_usage_dict = {
                        "prompt_tokens": estimated_prompt_tokens,
                        "completion_tokens": estimated_tokens,
                        "total_tokens": estimated_total_tokens
                    }
                else:
                    # 常规响应处理（没有工具调用）
                    token_usage = response.usage
                    assistant_content = assistant_message.content
                    
                    # 如果有内容，记录到交互流程
                    if assistant_content and assistant_content.strip():
                        interaction_flow.append({
                            "type": "text",
                            "content": assistant_content,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # 构建JSON结构
                    final_json_content = {
                        "type": "agent_response",
                        "interaction_flow": interaction_flow
                    }
                    
                    # 将助手消息添加到记忆中（使用纯文本）
                    memory_service.add_assistant_message(conversation_id, assistant_content, user_id)
                    
                    # 如果提供了数据库会话，保存AI回复（使用JSON结构）
                    if db and user_id and conversation_id:
                        await add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=json.dumps(final_json_content, ensure_ascii=False),
                            tokens=token_usage.completion_tokens,
                            prompt_tokens=token_usage.prompt_tokens,
                            total_tokens=token_usage.total_tokens,
                            agent_id=agent_id
                        )
                    
                    api_logger.info(f"OpenAI API调用成功, 生成文本长度: {len(assistant_content)}")
                    
                    # 设置token使用量字典
                    token_usage_dict = {
                        "prompt_tokens": token_usage.prompt_tokens,
                        "completion_tokens": token_usage.completion_tokens,
                        "total_tokens": token_usage.total_tokens
                    }
                
                # 检查是否需要自动生成标题
                if db and conversation_id and user_content:
                    await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
                
                return ChatCompletionResponse(
                    message=Message(
                        content=assistant_content
                    ),
                    usage=token_usage_dict,
                    conversation_id=conversation_id
                )
            except Exception as api_error:
                api_logger.error(f"OpenAI API调用出错: {str(api_error)}", exc_info=True)
                
                # 如果是因为模型不可用，尝试使用默认模型
                if "无可用渠道" in str(api_error) and current_agent and use_model != openai_client_service.model:
                    api_logger.info(f"尝试使用默认模型 {openai_client_service.model} 重新请求")
                    try:
                        response = await openai_client_service.async_client.chat.completions.create(
                            model=openai_client_service.model,
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            stream=False
                        )
                        
                        # 提取并返回响应
                        assistant_message = response.choices[0].message
                        token_usage = response.usage
                        assistant_content = assistant_message.content
                        
                        # 将助手消息添加到记忆中
                        memory_service.add_assistant_message(conversation_id, assistant_content, user_id)
                        
                        api_logger.info(f"使用默认模型 {openai_client_service.model} 成功, 生成文本长度: {len(assistant_content)}")
                        
                        # 如果提供了数据库会话，保存AI回复
                        if db and user_id and conversation_id:
                            await add_message(
                                db=db,
                                conversation_id=conversation_id,
                                role="assistant",
                                content=assistant_content,
                                tokens=token_usage.completion_tokens,
                                prompt_tokens=token_usage.prompt_tokens,
                                total_tokens=token_usage.total_tokens,
                                agent_id=agent_id
                            )
                        
                        # 检查是否需要自动生成标题
                        if db and conversation_id and user_content:
                            await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
                        
                        return ChatCompletionResponse(
                            message=Message(
                                content=assistant_content
                            ),
                            usage={
                                "prompt_tokens": token_usage.prompt_tokens,
                                "completion_tokens": token_usage.completion_tokens,
                                "total_tokens": token_usage.total_tokens
                            },
                            conversation_id=conversation_id
                        )
                    except Exception as fallback_error:
                        api_logger.error(f"使用默认模型 {openai_client_service.model} 仍然失败: {str(fallback_error)}", exc_info=True)
                
                # 创建一个简单的响应，避免进一步的错误
                error_message = f"AI服务暂时不可用: {str(api_error)}"
                
                if db and user_id and conversation_id:
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_message
                    )
                
                # 检查是否需要自动生成标题
                if db and conversation_id and user_content:
                    await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
                
                return ChatCompletionResponse(
                    message=Message(
                        content=error_message
                    ),
                    usage={
                        "prompt_tokens": len(str(messages)),
                        "completion_tokens": len(error_message),
                        "total_tokens": len(str(messages)) + len(error_message)
                    },
                    conversation_id=conversation_id
                )
                
        except Exception as e:
            api_logger.error(f"OpenAI API调用失败: {str(e)}", exc_info=True)
            
            # 创建一个简单的响应，避免进一步的错误
            error_message = f"AI服务发生错误: {str(e)}"
            
            if db and user_id and conversation_id:
                try:
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_message
                    )
                except Exception as db_error:
                    api_logger.error(f"保存错误信息到数据库失败: {str(db_error)}")
            
            # 检查是否需要自动生成标题
            if db and conversation_id and user_content:
                await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
            
            return ChatCompletionResponse(
                message=Message(
                    content=error_message
                ),
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                conversation_id=conversation_id
            )


# 创建全局聊天响应服务实例
chat_response_service = ChatResponseService() 