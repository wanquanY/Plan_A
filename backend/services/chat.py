import openai
from openai import OpenAI, AsyncOpenAI
from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
import os

from backend.core.config import settings
from backend.schemas.chat import Message, ChatRequest, ChatCompletionResponse
from backend.utils.logging import api_logger
from backend.crud.chat import create_chat, get_chat, add_message, get_chat_messages, update_chat_agent
from backend.crud.agent import agent as agent_crud
from backend.services.memory import memory_service

# 获取配置并进行调整
api_key = settings.OPENAI_API_KEY
base_url = settings.OPENAI_BASE_URL
model = settings.OPENAI_MODEL

# 确保base_url以/v1结尾
if base_url and not base_url.endswith('/v1'):
    base_url = base_url.rstrip() + '/v1'
    api_logger.info(f"修正后的BASE URL: {base_url}")

# 打印OpenAI配置信息
api_logger.info(f"OpenAI配置 - API KEY: {api_key[:5]}*****, BASE URL: {base_url}, 模型: {model}")

# 配置OpenAI客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 配置异步OpenAI客户端
async_client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url
)

# 打印客户端信息
api_logger.info(f"OpenAI客户端初始化完成 - 同步客户端: {client.base_url}, 异步客户端: {async_client.base_url}")


async def generate_chat_response(
    chat_request: ChatRequest,
    db: Optional[AsyncSession] = None,
    user_id: Optional[int] = None
) -> ChatCompletionResponse:
    """
    调用OpenAI API生成对话响应，并保存对话记录
    """
    try:
        api_logger.info(f"开始调用OpenAI API, 模型: {model}, API地址: {base_url}")
        
        # 获取或确认聊天会话ID
        conversation_id = chat_request.conversation_id
        
        # 获取Agent信息
        agent_id = chat_request.agent_id
        current_agent = None
        
        # 设置默认参数
        use_model = model
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
        
        api_logger.debug(f"请求消息: {json.dumps(messages, ensure_ascii=False)}")
        
        # 如果有Agent，使用Agent的设置
        if current_agent:
            # 先备份使用默认模型，以防指定模型不可用
            agent_model = current_agent.model
            use_model = agent_model if agent_model else model
            
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
        
        # 调用API - 尝试直接使用同步客户端
        try:
            api_logger.info(f"使用同步客户端调用API - URL: {client.base_url}")
            response = client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False
            )
            
            api_logger.debug(f"API原始响应类型: {type(response)}")
            # 记录原始响应内容
            api_logger.info(f"API原始响应内容: {json.dumps(response.model_dump(), ensure_ascii=False)}")
            
            # 检查响应类型
            if isinstance(response, str):
                api_logger.error(f"API返回了字符串而不是对象: {response}")
                raise ValueError(f"API返回了错误格式: {response}")
                
            # 提取并返回响应
            assistant_message = response.choices[0].message
            token_usage = response.usage
            assistant_content = assistant_message.content
            
            # 将助手消息添加到记忆中
            memory_service.add_assistant_message(conversation_id, assistant_content, user_id)
            
            api_logger.info(f"OpenAI API调用成功, 生成文本长度: {len(assistant_content)}")
            
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
        except Exception as api_error:
            api_logger.error(f"OpenAI API调用出错: {str(api_error)}", exc_info=True)
            
            # 如果是因为模型不可用，尝试使用默认模型
            if "无可用渠道" in str(api_error) and current_agent and use_model != model:
                api_logger.info(f"尝试使用默认模型 {model} 重新请求")
                try:
                    response = client.chat.completions.create(
                        model=model,
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
                    
                    api_logger.info(f"使用默认模型 {model} 成功, 生成文本长度: {len(assistant_content)}")
                    
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
                    api_logger.error(f"使用默认模型 {model} 仍然失败: {str(fallback_error)}", exc_info=True)
            
            # 创建一个简单的响应，避免进一步的错误
            error_message = f"AI服务暂时不可用: {str(api_error)}"
            
            if db and user_id and conversation_id:
                await add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=error_message
                )
            
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
        api_logger.info(f"开始调用OpenAI流式API, 模型: {model}, API地址: {base_url}")
        
        # 获取或确认聊天会话ID
        conversation_id = chat_request.conversation_id
        new_session_created = False
        
        # 获取Agent信息
        agent_id = chat_request.agent_id
        current_agent = None
        
        # 设置默认参数
        use_model = model
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
            use_model = agent_model if agent_model else model
            
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
        
        # 调用流式API
        try:
            api_logger.info(f"尝试同步调用流式API - URL: {client.base_url}")
            
            # 直接使用同步客户端，但开启流式响应
            response = client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True  # 开启流式响应
            )
            
            api_logger.debug(f"获取到流式响应: {type(response)}")
            
            # 这里response是一个迭代器，需要遍历每个部分
            collected_content = ""
            is_first_chunk = True
            chunk_count = 0
            
            for chunk in response:
                # 记录流式响应的每个块的原始内容
                chunk_count += 1
                api_logger.info(f"流式响应块 #{chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    
                    # 提取当前块的内容
                    content = delta.content or ""
                    
                    # 累加内容
                    collected_content += content
                    
                    # 对第一个有内容的块特殊处理
                    if is_first_chunk and content:
                        is_first_chunk = False
                        # 对第一个块，我们总是返回会话ID，不管是否是新会话
                        yield (content, conversation_id)
                    else:
                        # 后续块只返回内容
                        yield content
            
            # 流式响应结束，保存AI回复到数据库
            api_logger.info(f"流式响应完成，共接收 {chunk_count} 个块")
            api_logger.info(f"流式响应完整内容: {collected_content}")
            
            if db and user_id and conversation_id and collected_content:
                # 估算token数量（简单实现）
                tokens = len(collected_content) // 4
                prompt_tokens = len(str(messages)) // 4
                total_tokens = tokens + prompt_tokens
                
                await add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=collected_content,
                    tokens=tokens,
                    prompt_tokens=prompt_tokens,
                    total_tokens=total_tokens,
                    agent_id=agent_id
                )
                
                # 保存到记忆
                memory_service.add_assistant_message(conversation_id, collected_content, user_id)
                
                api_logger.info(f"流式聊天完成，内容长度: {len(collected_content)}")
        
        except Exception as api_error:
            api_logger.error(f"流式API调用出错: {str(api_error)}", exc_info=True)
            
            # 如果是因为模型不可用，尝试使用默认模型
            if "无可用渠道" in str(api_error) and current_agent and use_model != model:
                api_logger.info(f"流式接口尝试使用默认模型 {model} 重新请求")
                try:
                    # 使用默认模型重试
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        stream=True  # 仍然保持流式响应
                    )
                    
                    api_logger.debug(f"使用默认模型获取到流式响应: {type(response)}")
                    
                    # 这里response是一个迭代器，需要遍历每个部分
                    collected_content = ""
                    is_first_chunk = True
                    chunk_count = 0
                    
                    for chunk in response:
                        # 记录流式响应的每个块的原始内容
                        chunk_count += 1
                        api_logger.info(f"流式响应块 #{chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                        
                        if hasattr(chunk, 'choices') and chunk.choices:
                            delta = chunk.choices[0].delta
                            
                            # 提取当前块的内容
                            content = delta.content or ""
                            
                            # 累加内容
                            collected_content += content
                            
                            # 对第一个有内容的块特殊处理
                            if is_first_chunk and content:
                                is_first_chunk = False
                                # 对第一个块，我们总是返回会话ID，不管是否是新会话
                                yield (content, conversation_id)
                            else:
                                # 后续块只返回内容
                                yield content
                    
                    # 流式响应结束，保存AI回复到数据库
                    api_logger.info(f"使用默认模型流式响应完成，共接收 {chunk_count} 个块")
                    api_logger.info(f"使用默认模型流式响应完整内容: {collected_content}")
                    
                    if db and user_id and conversation_id and collected_content:
                        # 估算token数量（简单实现）
                        tokens = len(collected_content) // 4
                        prompt_tokens = len(str(messages)) // 4
                        total_tokens = tokens + prompt_tokens
                        
                        await add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=collected_content,
                            tokens=tokens,
                            prompt_tokens=prompt_tokens,
                            total_tokens=total_tokens,
                            agent_id=agent_id
                        )
                        
                        # 保存到记忆
                        memory_service.add_assistant_message(conversation_id, collected_content, user_id)
                        
                        api_logger.info(f"使用默认模型流式聊天完成，内容长度: {len(collected_content)}")
                        
                        # 由于已经生成了内容并返回，这里直接退出函数
                        return
                    
                except Exception as fallback_error:
                    api_logger.error(f"使用默认模型 {model} 流式响应仍然失败: {str(fallback_error)}", exc_info=True)
            
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


async def clear_memory(conversation_id: int):
    """
    清空指定会话的记忆
    """
    memory_service.clear_memory(conversation_id)
    api_logger.info(f"已清空会话 {conversation_id} 的记忆")


async def truncate_memory_after_message(conversation_id: int, message_index: int) -> bool:
    """
    截断指定消息后的所有记忆
    
    Args:
        conversation_id: 会话ID
        message_index: 消息索引，保留该索引及之前的消息，删除之后的消息
    
    Returns:
        bool: 是否截断成功
    """
    result = memory_service.truncate_memory_after_message(conversation_id, message_index)
    if result:
        api_logger.info(f"已截断会话 {conversation_id} 的记忆，保留到索引 {message_index}")
    else:
        api_logger.warning(f"截断会话 {conversation_id} 的记忆失败")
    return result


async def replace_message_and_truncate(conversation_id: int, message_index: int, new_content: str, role: str = None) -> bool:
    """
    替换指定消息的内容，并截断该消息之后的所有记忆
    
    Args:
        conversation_id: 会话ID
        message_index: 消息索引
        new_content: 新的消息内容
        role: 消息角色，如果为None则保持原角色
    
    Returns:
        bool: 是否操作成功
    """
    result = memory_service.replace_message_and_truncate(conversation_id, message_index, new_content, role)
    if result:
        api_logger.info(f"已替换会话 {conversation_id} 的消息 {message_index} 并截断后续消息")
    else:
        api_logger.warning(f"替换会话 {conversation_id} 的消息失败")
    return result


async def get_chat_history(
    db: AsyncSession, 
    conversation_id: int, 
    user_id: int
) -> List[Dict[str, Any]]:
    """
    获取指定会话的聊天历史记录
    """
    # 验证会话存在且属于当前用户
    chat = await get_chat(db, conversation_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="聊天会话不存在或无权访问"
        )
    
    # 获取聊天消息
    messages = await get_chat_messages(db, conversation_id)
    
    # 转换为前端需要的格式
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        for msg in messages
    ] 