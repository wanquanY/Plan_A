from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json

from backend.schemas.chat import ChatRequest
from backend.utils.logging import api_logger
from backend.crud.chat import create_chat, get_chat, add_message, update_chat_agent
from backend.crud.agent import agent as agent_crud
from backend.services.memory import memory_service
from backend.services.openai_client import openai_client_service
from backend.services.chat_tool_handler import chat_tool_handler
from backend.services.chat_tool_processor import chat_tool_processor
from backend.services.chat_session_manager import chat_session_manager


class ChatStreamService:
    """流式聊天响应服务"""
    
    @staticmethod
    async def generate_chat_stream(
        chat_request: ChatRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        调用OpenAI API生成对话流式响应，并保存对话记录
        
        返回的是生成内容的异步生成器。第一个内容会额外返回conversation_id
        """
        try:
            api_logger.info(f"开始调用OpenAI流式API, 模型: {openai_client_service.model}, API地址: {openai_client_service.async_client.base_url}")
            
            # 获取或确认聊天会话ID
            conversation_id = chat_request.conversation_id
            new_session_created = False
            note_id = None
            
            # 检查是否有笔记ID需要关联
            if hasattr(chat_request, "note_id") and chat_request.note_id:
                note_id = chat_request.note_id
            
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
                api_logger.info(f"流式响应使用Agent: {current_agent.name}, ID={current_agent.id}")
            
            if db and user_id:
                # 获取或创建聊天会话
                if not conversation_id:
                    # 创建新的聊天会话
                    if note_id:
                        # 查询笔记信息，获取标题
                        from backend.models.note import Note
                        from sqlalchemy import select
                        
                        # 查询笔记是否存在
                        note_stmt = select(Note).where(
                            Note.id == note_id,
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
                        if chat and note_id and note:
                            note.session_id = chat.id
                            await db.commit()
                            api_logger.info(f"流式API: 笔记ID {note_id} 已关联到会话ID {chat.id}")
                    else:
                        # 常规创建会话
                        chat = await create_chat(db, user_id, agent_id=agent_id)
                    
                    conversation_id = chat.id
                    new_session_created = True
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
                            
                    api_logger.info(f"使用现有会话: conversation_id={conversation_id}")
            else:
                # 如果conversation_id已经存在，直接使用（API层预创建的情况）
                if conversation_id:
                    api_logger.info(f"使用API层预创建的会话: conversation_id={conversation_id}")
                else:
                    api_logger.warning("没有数据库连接或用户ID，无法创建或验证会话")
            
            # 获取用户发送的内容
            user_content = chat_request.content
            
            # 将用户消息添加到记忆中
            memory_service.add_user_message(conversation_id, user_content, user_id)
            
            # 保存用户消息到数据库
            if db and user_id and conversation_id:
                await add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=user_content
                )
            
            # 从记忆服务获取完整的消息记录
            messages = memory_service.get_messages(conversation_id)
            
            # 添加Agent的系统提示词
            if current_agent and current_agent.system_prompt:
                # 在消息开头添加系统提示
                system_prompt = {"role": "system", "content": current_agent.system_prompt}
                messages.insert(0, system_prompt)
                api_logger.info(f"添加Agent系统提示词: {current_agent.system_prompt[:30]}...")
            
            api_logger.debug(f"流式请求消息: {json.dumps(messages, ensure_ascii=False)}")
            
            # 如果有Agent，使用Agent的设置
            if current_agent:
                # 先备份使用默认模型，以防指定模型不可用
                agent_model = current_agent.model
                use_model = agent_model if agent_model else openai_client_service.model
                
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
            
            # 获取工具配置
            tools = chat_tool_handler.get_agent_tools(current_agent) if current_agent else []
            has_tools = len(tools) > 0
            api_logger.info(f"流式聊天启用工具: {has_tools}, 工具数量: {len(tools)}")
            
            # 调用流式API
            try:
                api_logger.info(f"尝试调用流式API - URL: {openai_client_service.async_client.base_url}")
                
                # 准备API调用参数
                api_params = {
                    "model": use_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": True  # 开启流式响应
                }
                
                # 如果有工具，添加工具配置
                if has_tools:
                    api_params["tools"] = tools
                    api_logger.info(f"流式响应中添加工具配置: {len(tools)} 个工具")
                
                # 直接使用异步客户端，但开启流式响应
                response = await openai_client_service.async_client.chat.completions.create(**api_params)
                
                api_logger.debug(f"获取到流式响应: {type(response)}")
                
                # 这里response是一个异步迭代器，需要使用async for遍历每个部分
                collected_content = ""
                collected_tool_calls = []
                is_first_chunk = True
                chunk_count = 0
                
                async for chunk in response:
                    # 记录流式响应的每个块的原始内容
                    chunk_count += 1
                    api_logger.debug(f"流式响应块 #{chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                    
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        
                        # 检查是否有工具调用
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            api_logger.debug(f"流式响应中检测到工具调用: {len(delta.tool_calls)} 个")
                            
                            # 收集工具调用信息
                            for tool_call in delta.tool_calls:
                                # 获取工具调用的索引（如果有）
                                tool_index = getattr(tool_call, 'index', None)
                                
                                # 查找是否已存在相同索引的工具调用
                                existing_call = None
                                if tool_index is not None:
                                    # 使用索引查找
                                    if tool_index < len(collected_tool_calls):
                                        existing_call = collected_tool_calls[tool_index]
                                else:
                                    # 使用ID查找
                                    for existing in collected_tool_calls:
                                        if existing.get('id') == tool_call.id:
                                            existing_call = existing
                                            break
                                
                                if existing_call:
                                    # 更新现有的工具调用
                                    if tool_call.function and tool_call.function.arguments:
                                        existing_call['function']['arguments'] += tool_call.function.arguments
                                        api_logger.debug(f"累积工具调用参数: {existing_call['id']}, 当前参数: {existing_call['function']['arguments']}")
                                    
                                    # 更新函数名（如果提供）
                                    if tool_call.function and tool_call.function.name:
                                        existing_call['function']['name'] = tool_call.function.name
                                    
                                    # 更新ID（如果提供）
                                    if tool_call.id:
                                        existing_call['id'] = tool_call.id
                                else:
                                    # 添加新的工具调用
                                    new_call = {
                                        'id': tool_call.id if tool_call.id else f"call_{len(collected_tool_calls)}",
                                        'type': tool_call.type if tool_call.type else 'function',
                                        'function': {
                                            'name': tool_call.function.name if tool_call.function and tool_call.function.name else '',
                                            'arguments': tool_call.function.arguments if tool_call.function and tool_call.function.arguments else ''
                                        }
                                    }
                                    
                                    # 如果有索引，确保列表足够大
                                    if tool_index is not None:
                                        while len(collected_tool_calls) <= tool_index:
                                            collected_tool_calls.append(None)
                                        collected_tool_calls[tool_index] = new_call
                                    else:
                                        collected_tool_calls.append(new_call)
                                    
                                    api_logger.debug(f"新增工具调用: {new_call['id']}, 名称: {new_call['function']['name']}, 初始参数: {new_call['function']['arguments']}")
                                    
                                    # 发送工具调用开始的状态信息
                                    tool_status = {
                                        "type": "tool_call_start",
                                        "tool_call_id": new_call['id'],
                                        "tool_name": new_call['function']['name'],
                                        "status": "preparing"
                                    }
                                    yield ("", conversation_id, tool_status)
                        
                        # 提取当前块的内容
                        content = delta.content or ""
                        
                        # 累加内容
                        collected_content += content
                        
                        # 对第一个有内容的块特殊处理
                        if is_first_chunk and content:
                            is_first_chunk = False
                            # 对第一个块，我们总是返回会话ID，不管是否是新会话
                            yield (content, conversation_id)
                        elif content:
                            # 后续块只返回内容
                            yield content
                
                # 流式响应结束，检查是否有工具调用需要处理
                api_logger.info(f"流式响应完成，共接收 {chunk_count} 个块")
                api_logger.info(f"流式响应完整内容: {collected_content}")
                api_logger.info(f"收集到的工具调用: {len(collected_tool_calls)} 个")
                
                # 先保存AI消息（即使内容为空，也要保存以便后续更新）
                ai_message = None
                if db and user_id and conversation_id:
                    # 估算token数量（简单实现）
                    tokens = len(collected_content) // 4 if collected_content else 0
                    prompt_tokens = len(str(messages)) // 4
                    total_tokens = tokens + prompt_tokens
                    
                    ai_message = await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=collected_content or "",  # 即使为空也保存
                        tokens=tokens,
                        prompt_tokens=prompt_tokens,
                        total_tokens=total_tokens,
                        agent_id=agent_id
                    )
                    api_logger.info(f"AI消息已保存: id={ai_message.id}, 初始内容长度: {len(collected_content or '')}")
                
                # 检查是否有有效的工具调用需要处理
                valid_tool_calls = [tc for tc in collected_tool_calls if tc is not None and tc.get('function', {}).get('name')]
                
                if valid_tool_calls:
                    api_logger.info(f"检测到 {len(valid_tool_calls)} 个有效工具调用，开始递归处理")
                    # 递归处理工具调用，支持无限次调用
                    final_content = collected_content or ""  # 保存初始内容，确保不为None
                    async for content_chunk in chat_tool_processor.process_tool_calls_recursively_stream(
                        collected_content or "", 
                        collected_tool_calls, 
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
                        message_id=ai_message.id if ai_message else None  # 传递AI消息ID
                    ):
                        if isinstance(content_chunk, tuple):
                            # 工具状态信息
                            yield content_chunk
                        else:
                            # 内容块 - 累积到最终内容中
                            yield content_chunk
                            final_content += content_chunk
                    
                    # 更新数据库中的消息内容为最终完整内容
                    if ai_message:
                        ai_message.content = final_content
                        # 重新计算token数量
                        ai_message.tokens = len(final_content) // 4
                        ai_message.total_tokens = ai_message.prompt_tokens + ai_message.tokens
                        await db.commit()
                        await db.refresh(ai_message)
                        api_logger.info(f"更新AI消息内容，最终长度: {len(final_content)}")
                    
                    # 保存到记忆 - 使用最终完整内容
                    if final_content:
                        memory_service.add_assistant_message(conversation_id, final_content, user_id)
                        api_logger.info(f"流式聊天完成，最终内容长度: {len(final_content)}")
                else:
                    api_logger.info("没有工具调用，直接保存初始内容")
                    # 没有工具调用，直接保存到记忆
                    if collected_content:
                        memory_service.add_assistant_message(conversation_id, collected_content, user_id)
                        api_logger.info(f"流式聊天完成，内容长度: {len(collected_content)}")
                
                # 检查是否需要自动生成标题
                if db and conversation_id and user_content:
                    await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
            
            except Exception as api_error:
                api_logger.error(f"流式API调用出错: {str(api_error)}", exc_info=True)
                
                # 如果是因为模型不可用，尝试使用默认模型
                if "无可用渠道" in str(api_error) and current_agent and use_model != openai_client_service.model:
                    api_logger.info(f"流式接口尝试使用默认模型 {openai_client_service.model} 重新请求")
                    try:
                        # 准备默认模型的API调用参数
                        fallback_api_params = {
                            "model": openai_client_service.model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "top_p": top_p,
                            "stream": True  # 仍然保持流式响应
                        }
                        
                        # 如果有工具，添加工具配置
                        if has_tools:
                            fallback_api_params["tools"] = tools
                        
                        # 使用默认模型重试
                        response = await openai_client_service.async_client.chat.completions.create(**fallback_api_params)
                        
                        api_logger.debug(f"使用默认模型获取到流式响应: {type(response)}")
                        
                        # 处理流式响应（与上面相同的逻辑）
                        collected_content = ""
                        collected_tool_calls = []
                        is_first_chunk = True
                        chunk_count = 0
                        
                        async for chunk in response:
                            chunk_count += 1
                            api_logger.debug(f"流式响应块 #{chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                            
                            if hasattr(chunk, 'choices') and chunk.choices:
                                delta = chunk.choices[0].delta
                                
                                # 检查是否有工具调用
                                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                    api_logger.info(f"流式响应中检测到工具调用: {len(delta.tool_calls)} 个")
                                    
                                    # 收集工具调用信息（与上面相同的逻辑）
                                    for tool_call in delta.tool_calls:
                                        tool_index = getattr(tool_call, 'index', None)
                                        existing_call = None
                                        
                                        if tool_index is not None:
                                            if tool_index < len(collected_tool_calls):
                                                existing_call = collected_tool_calls[tool_index]
                                        else:
                                            for existing in collected_tool_calls:
                                                if existing.get('id') == tool_call.id:
                                                    existing_call = existing
                                                    break
                                        
                                        if existing_call:
                                            if tool_call.function and tool_call.function.arguments:
                                                existing_call['function']['arguments'] += tool_call.function.arguments
                                            if tool_call.function and tool_call.function.name:
                                                existing_call['function']['name'] = tool_call.function.name
                                            if tool_call.id:
                                                existing_call['id'] = tool_call.id
                                        else:
                                            new_call = {
                                                'id': tool_call.id if tool_call.id else f"call_{len(collected_tool_calls)}",
                                                'type': tool_call.type if tool_call.type else 'function',
                                                'function': {
                                                    'name': tool_call.function.name if tool_call.function and tool_call.function.name else '',
                                                    'arguments': tool_call.function.arguments if tool_call.function and tool_call.function.arguments else ''
                                                }
                                            }
                                            
                                            if tool_index is not None:
                                                while len(collected_tool_calls) <= tool_index:
                                                    collected_tool_calls.append(None)
                                                collected_tool_calls[tool_index] = new_call
                                            else:
                                                collected_tool_calls.append(new_call)
                                
                                content = delta.content or ""
                                collected_content += content
                                
                                if is_first_chunk and content:
                                    is_first_chunk = False
                                    yield (content, conversation_id)
                                elif content:
                                    yield content
                        
                        # 处理工具调用和保存消息（与上面相同的逻辑）
                        ai_message = None
                        if db and user_id and conversation_id:
                            tokens = len(collected_content) // 4 if collected_content else 0
                            prompt_tokens = len(str(messages)) // 4
                            total_tokens = tokens + prompt_tokens
                            
                            ai_message = await add_message(
                                db=db,
                                conversation_id=conversation_id,
                                role="assistant",
                                content=collected_content or "",
                                tokens=tokens,
                                prompt_tokens=prompt_tokens,
                                total_tokens=total_tokens,
                                agent_id=agent_id
                            )
                        
                        # 检查是否有有效的工具调用需要处理
                        valid_tool_calls = [tc for tc in collected_tool_calls if tc is not None and tc.get('function', {}).get('name')]
                        
                        if valid_tool_calls:
                            # 递归处理工具调用
                            final_content = collected_content or ""
                            async for content_chunk in chat_tool_processor.process_tool_calls_recursively_stream(
                                collected_content or "", 
                                collected_tool_calls, 
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
                                message_id=ai_message.id if ai_message else None
                            ):
                                if isinstance(content_chunk, tuple):
                                    yield content_chunk
                                else:
                                    yield content_chunk
                                    final_content += content_chunk
                            
                            # 更新AI消息内容
                            if ai_message:
                                ai_message.content = final_content
                                ai_message.tokens = len(final_content) // 4
                                ai_message.total_tokens = ai_message.prompt_tokens + ai_message.tokens
                                await db.commit()
                                await db.refresh(ai_message)
                            
                            # 保存最终内容到记忆
                            if final_content:
                                memory_service.add_assistant_message(conversation_id, final_content, user_id)
                                api_logger.info(f"流式聊天完成，最终内容长度: {len(final_content)}")
                        else:
                            # 没有工具调用，保存初始内容到记忆
                            if collected_content:
                                memory_service.add_assistant_message(conversation_id, collected_content, user_id)
                                api_logger.info(f"流式聊天完成，内容长度: {len(collected_content)}")
                        
                        # 检查是否需要自动生成标题
                        if db and conversation_id and user_content:
                            await chat_session_manager.auto_generate_title_if_needed(db, conversation_id, user_content)
                    
                    except Exception as fallback_error:
                        api_logger.error(f"使用默认模型 {openai_client_service.model} 流式响应仍然失败: {str(fallback_error)}", exc_info=True)
                
                # 发送错误信息作为流式内容
                error_message = f"AI服务暂时不可用: {str(api_error)}"
                
                # 总是返回会话ID，不管是否是新会话
                yield (error_message, conversation_id)
                
                # 保存错误信息到数据库
                if db and user_id and conversation_id:
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=error_message
                    )
        
        except Exception as e:
            api_logger.error(f"流式聊天生成失败: {str(e)}", exc_info=True)
            
            # 发送一个错误消息，包含会话ID
            error_message = f"AI服务发生错误: {str(e)}"
            yield (error_message, conversation_id)


# 创建全局流式聊天服务实例
chat_stream_service = ChatStreamService() 