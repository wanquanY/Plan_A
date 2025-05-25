import openai
from openai import OpenAI, AsyncOpenAI
from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
import os
from datetime import datetime

from backend.core.config import settings
from backend.schemas.chat import Message, ChatRequest, ChatCompletionResponse
from backend.utils.logging import api_logger
from backend.crud.chat import create_chat, get_chat, add_message, get_chat_messages, update_chat_agent
from backend.crud.agent import agent as agent_crud
from backend.services.memory import memory_service
from backend.services.tools import tools_service
from backend.config.tools_config import AVAILABLE_TOOLS, get_tools_by_provider, get_tool_by_name
from backend.config.tools_manager import tools_manager

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


# 获取Agent配置的工具列表
def get_agent_tools(agent):
    """根据Agent的配置返回可用工具列表"""
    if not agent or not agent.tools_enabled:
        return []
    
    # 使用工具管理器获取工具列表
    tools = tools_manager.get_agent_tools(agent.tools_enabled)
    
    api_logger.info(f"为Agent {agent.name} 配置了 {len(tools)} 个工具")
    return tools


# 处理工具调用请求
async def handle_tool_calls(tool_calls, agent, db: Optional[AsyncSession] = None, conversation_id: Optional[int] = None):
    """处理工具调用请求并返回结果"""
    results = []
    tool_calls_data = []  # 用于保存到数据库的工具调用信息
    
    for tool_call in tool_calls:
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        api_logger.info(f"处理工具调用: {function_name}, 参数: {function_args}")
        
        # 初始化工具调用数据
        tool_call_data = {
            "id": tool_call_id,
            "name": function_name,
            "arguments": function_args,
            "status": "preparing",
            "result": None,
            "error": None,
            "started_at": datetime.now().isoformat()
        }
        tool_calls_data.append(tool_call_data)
        
        # 使用工具管理器获取API密钥
        api_key = None
        if agent and agent.tools_enabled:
            api_key = tools_manager.get_tool_api_key(function_name, agent.tools_enabled)
        
        try:
            # 更新状态为执行中
            tool_call_data["status"] = "executing"
            
            # 根据函数名执行相应的工具
            tool_result = None
            if function_name == "tavily_search":
                tool_result = tools_service.execute_tool(
                    tool_name="tavily",
                    action="search",
                    params={
                        "query": function_args.get("query"),
                        "max_results": function_args.get("max_results", 10)
                    },
                    config={"api_key": api_key} if api_key else None
                )
                
            elif function_name == "tavily_extract":
                tool_result = tools_service.execute_tool(
                    tool_name="tavily",
                    action="extract",
                    params={
                        "urls": function_args.get("urls"),
                        "include_images": function_args.get("include_images", False)
                    },
                    config={"api_key": api_key} if api_key else None
                )
            
            elif function_name == "serper_search":
                tool_result = tools_service.execute_tool(
                    tool_name="serper",
                    action="search",
                    params={
                        "query": function_args.get("query"),
                        "max_results": function_args.get("max_results", 10),
                        "gl": function_args.get("gl", "cn"),
                        "hl": function_args.get("hl", "zh-cn")
                    },
                    config={"api_key": api_key} if api_key else None
                )
            
            elif function_name == "serper_news":
                tool_result = tools_service.execute_tool(
                    tool_name="serper",
                    action="news_search",
                    params={
                        "query": function_args.get("query"),
                        "max_results": function_args.get("max_results", 10),
                        "gl": function_args.get("gl", "cn"),
                        "hl": function_args.get("hl", "zh-cn")
                    },
                    config={"api_key": api_key} if api_key else None
                )
            
            elif function_name == "serper_scrape":
                tool_result = tools_service.execute_tool(
                    tool_name="serper",
                    action="scrape_url",
                    params={
                        "url": function_args.get("url"),
                        "include_markdown": function_args.get("include_markdown", True)
                    },
                    config={"api_key": api_key} if api_key else None
                )
            
            # 更新状态为完成
            tool_call_data["status"] = "completed"
            tool_call_data["result"] = tool_result
            tool_call_data["completed_at"] = datetime.now().isoformat()
            
            results.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })
            
        except Exception as e:
            api_logger.error(f"工具调用失败: {function_name}, 错误: {str(e)}")
            
            # 更新状态为错误
            tool_call_data["status"] = "error"
            tool_call_data["error"] = str(e)
            tool_call_data["completed_at"] = datetime.now().isoformat()
            
            # 返回错误结果
            results.append({
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps({"error": str(e)}, ensure_ascii=False)
            })
    
    api_logger.info(f"完成 {len(results)} 个工具调用")
    return results, tool_calls_data


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
        
        # 获取工具配置
        tools = get_agent_tools(current_agent) if current_agent else []
        has_tools = len(tools) > 0
        api_logger.info(f"当前聊天启用工具: {has_tools}, 工具数量: {len(tools)}")
        
        # 调用API - 尝试直接使用同步客户端
        try:
            api_logger.info(f"使用同步客户端调用API - URL: {client.base_url}")
            
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
            
            # 调用API
            response = client.chat.completions.create(**api_params)
            
            api_logger.debug(f"API原始响应类型: {type(response)}")
            # 记录原始响应内容
            api_logger.info(f"API原始响应内容: {json.dumps(response.model_dump(), ensure_ascii=False)}")
            
            # 检查响应类型
            if isinstance(response, str):
                api_logger.error(f"API返回了字符串而不是对象: {response}")
                raise ValueError(f"API返回了错误格式: {response}")
            
            # 检查是否有工具调用
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
            
            # 如果有工具调用
            if tool_calls:
                api_logger.info(f"检测到工具调用请求: {len(tool_calls)} 个工具调用")
                
                # 处理工具调用
                tool_results, tool_calls_data = await handle_tool_calls(tool_calls, current_agent, db, conversation_id)
                
                # 将工具调用和结果添加到消息列表
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
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
                
                api_logger.info(f"使用工具结果调用第二次API")
                
                # 第二次调用API，包含工具结果
                second_response = client.chat.completions.create(
                    model=use_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=False
                )
                
                # 提取最终响应
                token_usage = second_response.usage
                assistant_content = second_response.choices[0].message.content
                
                # 将最终的助手消息添加到记忆中
                memory_service.add_assistant_message(conversation_id, assistant_content, user_id)
                
                # 如果提供了数据库会话，保存AI回复（包含工具调用信息）
                if db and user_id and conversation_id:
                    await add_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=assistant_content,
                        tokens=token_usage.completion_tokens,
                        prompt_tokens=token_usage.prompt_tokens,
                        total_tokens=token_usage.total_tokens,
                        agent_id=agent_id,
                        tool_calls_data=tool_calls_data
                    )
                
                api_logger.info(f"工具调用完成，最终响应长度: {len(assistant_content)}")
            else:
                # 常规响应处理
                token_usage = response.usage
                assistant_content = assistant_message.content
                
                # 将助手消息添加到记忆中
                memory_service.add_assistant_message(conversation_id, assistant_content, user_id)
                
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
                
                api_logger.info(f"OpenAI API调用成功, 生成文本长度: {len(assistant_content)}")
            
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
        note_id = None
        
        # 检查是否有笔记ID需要关联
        if hasattr(chat_request, "note_id") and chat_request.note_id:
            note_id = chat_request.note_id
        
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
        
        # 获取工具配置
        tools = get_agent_tools(current_agent) if current_agent else []
        has_tools = len(tools) > 0
        api_logger.info(f"流式聊天启用工具: {has_tools}, 工具数量: {len(tools)}")
        
        # 调用流式API
        try:
            api_logger.info(f"尝试同步调用流式API - URL: {client.base_url}")
            
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
            
            # 直接使用同步客户端，但开启流式响应
            response = client.chat.completions.create(**api_params)
            
            api_logger.debug(f"获取到流式响应: {type(response)}")
            
            # 这里response是一个迭代器，需要遍历每个部分
            collected_content = ""
            collected_tool_calls = []
            is_first_chunk = True
            chunk_count = 0
            
            for chunk in response:
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
            
            # 逐个处理工具调用，发送状态更新
            tool_results = []
            all_tool_calls_data = []
            
            # 构造工具调用对象
            class ToolCall:
                def __init__(self, id, type, function):
                    self.id = id
                    self.type = type
                    self.function = function
            
            class Function:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments
            
            for tc in collected_tool_calls:
                if tc is None:
                    continue
                    
                # 构造工具调用对象
                func = Function(tc['function']['name'], tc['function']['arguments'])
                tool_call_obj = ToolCall(tc['id'], tc['type'], func)
                
                # 发送工具调用执行状态
                tool_status = {
                    "type": "tool_call_executing",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "executing"
                }
                yield ("", conversation_id, tool_status)
                
                # 执行单个工具调用
                single_result, single_tool_data = await handle_tool_calls([tool_call_obj], current_agent, db, conversation_id)
                tool_results.extend(single_result)
                all_tool_calls_data.extend(single_tool_data)
                
                # 发送工具调用完成状态，包含结果内容
                tool_result_content = single_result[0]["content"] if single_result else ""
                tool_status = {
                    "type": "tool_call_completed",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "completed",
                    "result": tool_result_content  # 添加工具调用结果
                }
                yield ("", conversation_id, tool_status)
                
                # 在工具调用完成后，发送一个特殊的文本标记，表示工具调用已完成
                tool_completion_text = f"\n\n🔧 {tool_call_obj.function.name} 执行完成\n\n"
                yield (tool_completion_text, conversation_id)
            
            # 递归处理工具调用，支持无限次调用
            async for content_chunk in process_tool_calls_recursively_stream(
                collected_content, 
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
                db
            ):
                if isinstance(content_chunk, tuple):
                    # 工具状态信息
                    yield content_chunk
                else:
                    # 内容块
                    yield content_chunk
                    collected_content += content_chunk
            
            # 保存最终内容到数据库
            if db and user_id and conversation_id and collected_content:
                # 估算token数量（简单实现）
                tokens = len(collected_content) // 4
                prompt_tokens = len(str(messages)) // 4
                total_tokens = tokens + prompt_tokens
                
                # 如果有工具调用，需要收集工具调用数据
                final_tool_calls_data = None
                if collected_tool_calls:
                    # 这里需要从工具调用处理中获取完整的工具调用数据
                    # 由于流式处理的复杂性，我们先保存基本信息
                    final_tool_calls_data = []
                    for tc in collected_tool_calls:
                        if tc:  # 跳过None值
                            final_tool_calls_data.append({
                                "id": tc.get("id", ""),
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments": json.loads(tc.get("function", {}).get("arguments", "{}")),
                                "status": "completed",  # 流式响应完成时默认为completed
                                "result": None,  # 在递归处理中会更新
                                "error": None,
                                "started_at": datetime.now().isoformat(),
                                "completed_at": datetime.now().isoformat()
                            })
                
                await add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=collected_content,
                    tokens=tokens,
                    prompt_tokens=prompt_tokens,
                    total_tokens=total_tokens,
                    agent_id=agent_id,
                    tool_calls_data=final_tool_calls_data
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
                    # 准备默认模型的API调用参数
                    fallback_api_params = {
                        "model": model,
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
                    response = client.chat.completions.create(**fallback_api_params)
                    
                    api_logger.debug(f"使用默认模型获取到流式响应: {type(response)}")
                    
                    # 这里response是一个迭代器，需要遍历每个部分
                    collected_content = ""
                    collected_tool_calls = []
                    is_first_chunk = True
                    chunk_count = 0
                    
                    for chunk in response:
                        # 记录流式响应的每个块的原始内容
                        chunk_count += 1
                        api_logger.debug(f"流式响应块 #{chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
                        
                        if hasattr(chunk, 'choices') and chunk.choices:
                            delta = chunk.choices[0].delta
                            
                            # 检查是否有工具调用
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                api_logger.info(f"流式响应中检测到工具调用: {len(delta.tool_calls)} 个")
                                
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
                    
                    # 逐个处理工具调用，发送状态更新
                    tool_results = []
                    all_tool_calls_data = []
                    
                    for tool_call_obj in collected_tool_calls:
                        # 发送工具调用执行状态
                        tool_status = {
                            "type": "tool_call_executing",
                            "tool_call_id": tool_call_obj.id,
                            "tool_name": tool_call_obj.function.name,
                            "status": "executing"
                        }
                        yield ("", conversation_id, tool_status)
                        
                        # 执行单个工具调用
                        single_result, single_tool_data = await handle_tool_calls([tool_call_obj], current_agent, db, conversation_id)
                        tool_results.extend(single_result)
                        all_tool_calls_data.extend(single_tool_data)
                        
                        # 发送工具调用完成状态，包含结果内容
                        tool_result_content = single_result[0]["content"] if single_result else ""
                        tool_status = {
                            "type": "tool_call_completed",
                            "tool_call_id": tool_call_obj.id,
                            "tool_name": tool_call_obj.function.name,
                            "status": "completed",
                            "result": tool_result_content  # 添加工具调用结果
                        }
                        yield ("", conversation_id, tool_status)
                        
                        # 在工具调用完成后，发送一个特殊的文本标记，表示工具调用已完成
                        tool_completion_text = f"\n\n🔧 {tool_call_obj.function.name} 执行完成\n\n"
                        yield (tool_completion_text, conversation_id)
                    
                    # 递归处理工具调用，支持无限次调用
                    async for content_chunk in process_tool_calls_recursively_stream(
                        collected_content, 
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
                        db
                    ):
                        if isinstance(content_chunk, tuple):
                            # 工具状态信息
                            yield content_chunk
                        else:
                            # 内容块
                            yield content_chunk
                            collected_content += content_chunk
                    
                    # 保存最终内容到数据库
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
                            agent_id=agent_id,
                            tool_calls_data=all_tool_calls_data
                        )
                        
                        # 保存到记忆
                        memory_service.add_assistant_message(conversation_id, collected_content, user_id)
                        
                        api_logger.info(f"流式聊天完成，内容长度: {len(collected_content)}")
                
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


async def process_tool_calls_recursively(
    content: str, 
    tool_calls: List[Dict[str, Any]], 
    messages: List[Dict[str, Any]], 
    agent, 
    use_model: str, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    tools: List[Dict[str, Any]], 
    has_tools: bool, 
    conversation_id: int,
    max_iterations: int = 10  # 防止无限循环
) -> str:
    """
    递归处理工具调用，支持无限次调用
    """
    iteration = 0
    current_content = content
    current_tool_calls = tool_calls
    
    while current_tool_calls and iteration < max_iterations:
        iteration += 1
        api_logger.info(f"开始第 {iteration} 轮工具调用处理，共 {len(current_tool_calls)} 个工具调用")
        
        # 验证工具调用参数的完整性
        valid_tool_calls = []
        for tc in current_tool_calls:
            # 跳过None值（可能由索引填充产生）
            if tc is None:
                continue
                
            # 检查函数名是否有效
            if not tc['function']['name']:
                api_logger.warning(f"工具调用 {tc['id']} 函数名为空，跳过")
                continue
            
            # 检查参数是否有效
            if tc['function']['arguments'].strip():
                try:
                    # 验证JSON格式
                    json.loads(tc['function']['arguments'])
                    valid_tool_calls.append(tc)
                    api_logger.info(f"工具调用 {tc['function']['name']} 参数完整: {tc['function']['arguments']}")
                except json.JSONDecodeError as e:
                    api_logger.error(f"工具调用 {tc['function']['name']} 参数JSON格式错误: {tc['function']['arguments']}, 错误: {e}")
            else:
                api_logger.warning(f"工具调用 {tc['function']['name']} 参数为空，跳过")
        
        if not valid_tool_calls:
            api_logger.warning("没有有效的工具调用，结束工具处理")
            break
        
        # 构造工具调用对象
        class ToolCall:
            def __init__(self, id, type, function):
                self.id = id
                self.type = type
                self.function = function
        
        class Function:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments
        
        tool_call_objects = []
        for tc in valid_tool_calls:
            func = Function(tc['function']['name'], tc['function']['arguments'])
            tool_call_obj = ToolCall(tc['id'], tc['type'], func)
            tool_call_objects.append(tool_call_obj)
        
        # 处理工具调用
        tool_results, tool_calls_data = await handle_tool_calls(tool_call_objects, agent, db, conversation_id)
        
        # 将工具调用和结果添加到消息列表
        messages.append({
            "role": "assistant",
            "content": current_content,
            "tool_calls": [
                {
                    "id": tc['id'],
                    "type": "function",
                    "function": {
                        "name": tc['function']['name'],
                        "arguments": tc['function']['arguments']
                    }
                } for tc in valid_tool_calls
            ]
        })
        
        # 添加工具结果
        for tool_result in tool_results:
            messages.append(tool_result)
        
        api_logger.info(f"第 {iteration} 轮工具调用完成，调用下一次API")
        
        # 调用API获取下一次响应
        next_response = client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=False,
            tools=tools if has_tools else None  # 确保每次调用都包含工具配置
        )
        
        # 提取响应
        assistant_message = next_response.choices[0].message
        current_content = assistant_message.content or ""
        
        # 检查是否有新的工具调用
        new_tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
        
        if new_tool_calls:
            api_logger.info(f"第 {iteration} 轮响应中检测到新的工具调用: {len(new_tool_calls)} 个")
            
            # 转换工具调用格式
            current_tool_calls = []
            for tc in new_tool_calls:
                current_tool_calls.append({
                    'id': tc.id,
                    'type': tc.type,
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                })
        else:
            api_logger.info(f"第 {iteration} 轮响应中没有新的工具调用，结束处理")
            current_tool_calls = None
    
    if iteration >= max_iterations:
        api_logger.warning(f"工具调用达到最大迭代次数 {max_iterations}，强制结束")
    
    api_logger.info(f"工具调用处理完成，共进行了 {iteration} 轮，最终内容长度: {len(current_content)}")
    return current_content 


async def process_tool_calls_recursively_stream(
    content: str, 
    tool_calls: List[Dict[str, Any]], 
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
    max_iterations: int = 10  # 防止无限循环
):
    """
    递归处理工具调用，支持无限次调用（流式版本）
    """
    iteration = 0
    current_content = content
    current_tool_calls = tool_calls
    
    while current_tool_calls and iteration < max_iterations:
        iteration += 1
        api_logger.info(f"开始第 {iteration} 轮工具调用处理，共 {len(current_tool_calls)} 个工具调用")
        
        # 验证工具调用参数的完整性
        valid_tool_calls = []
        for tc in current_tool_calls:
            # 跳过None值（可能由索引填充产生）
            if tc is None:
                continue
                
            # 检查函数名是否有效
            if not tc['function']['name']:
                api_logger.warning(f"工具调用 {tc['id']} 函数名为空，跳过")
                continue
            
            # 检查参数是否有效
            if tc['function']['arguments'].strip():
                try:
                    # 验证JSON格式
                    json.loads(tc['function']['arguments'])
                    valid_tool_calls.append(tc)
                    api_logger.info(f"工具调用 {tc['function']['name']} 参数完整: {tc['function']['arguments']}")
                except json.JSONDecodeError as e:
                    api_logger.error(f"工具调用 {tc['function']['name']} 参数JSON格式错误: {tc['function']['arguments']}, 错误: {e}")
            else:
                api_logger.warning(f"工具调用 {tc['function']['name']} 参数为空，跳过")
        
        if not valid_tool_calls:
            api_logger.warning("没有有效的工具调用，结束工具处理")
            break
        
        # 构造工具调用对象
        class ToolCall:
            def __init__(self, id, type, function):
                self.id = id
                self.type = type
                self.function = function
        
        class Function:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments
        
        tool_call_objects = []
        for tc in valid_tool_calls:
            func = Function(tc['function']['name'], tc['function']['arguments'])
            tool_call_obj = ToolCall(tc['id'], tc['type'], func)
            tool_call_objects.append(tool_call_obj)
        
        # 处理工具调用
        tool_results, tool_calls_data = await handle_tool_calls(tool_call_objects, agent, db, conversation_id)
        
        # 将工具调用和结果添加到消息列表
        messages.append({
            "role": "assistant",
            "content": current_content,
            "tool_calls": [
                {
                    "id": tc['id'],
                    "type": "function",
                    "function": {
                        "name": tc['function']['name'],
                        "arguments": tc['function']['arguments']
                    }
                } for tc in valid_tool_calls
            ]
        })
        
        # 添加工具结果
        for tool_result in tool_results:
            messages.append(tool_result)
        
        api_logger.info(f"第 {iteration} 轮工具调用完成，调用下一次流式API")
        
        # 调用API获取下一次响应（流式）
        next_response = client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
            tools=tools if has_tools else None  # 确保每次调用都包含工具配置
        )
        
        # 处理流式响应
        next_collected_content = ""
        next_collected_tool_calls = []
        next_chunk_count = 0
        
        for chunk in next_response:
            next_chunk_count += 1
            api_logger.debug(f"第 {iteration} 轮流式响应块 #{next_chunk_count}: {json.dumps(chunk.model_dump(), ensure_ascii=False)}")
            
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                
                # 检查是否有工具调用
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    api_logger.debug(f"第 {iteration} 轮流式响应中检测到工具调用: {len(delta.tool_calls)} 个")
                    
                    # 收集工具调用信息
                    for tool_call in delta.tool_calls:
                        # 获取工具调用的索引（如果有）
                        tool_index = getattr(tool_call, 'index', None)
                        
                        # 查找是否已存在相同索引的工具调用
                        existing_call = None
                        if tool_index is not None:
                            # 使用索引查找
                            if tool_index < len(next_collected_tool_calls):
                                existing_call = next_collected_tool_calls[tool_index]
                        else:
                            # 使用ID查找
                            for existing in next_collected_tool_calls:
                                if existing and existing.get('id') == tool_call.id:
                                    existing_call = existing
                                    break
                        
                        if existing_call:
                            # 更新现有的工具调用
                            if tool_call.function and tool_call.function.arguments:
                                existing_call['function']['arguments'] += tool_call.function.arguments
                                api_logger.debug(f"第 {iteration} 轮累积工具调用参数: {existing_call['id']}, 当前参数: {existing_call['function']['arguments']}")
                            
                            # 更新函数名（如果提供）
                            if tool_call.function and tool_call.function.name:
                                existing_call['function']['name'] = tool_call.function.name
                            
                            # 更新ID（如果提供）
                            if tool_call.id:
                                existing_call['id'] = tool_call.id
                        else:
                            # 添加新的工具调用
                            new_call = {
                                'id': tool_call.id if tool_call.id else f"call_iter_{iteration}_{len(next_collected_tool_calls)}",
                                'type': tool_call.type if tool_call.type else 'function',
                                'function': {
                                    'name': tool_call.function.name if tool_call.function and tool_call.function.name else '',
                                    'arguments': tool_call.function.arguments if tool_call.function and tool_call.function.arguments else ''
                                }
                            }
                            
                            # 如果有索引，确保列表足够大
                            if tool_index is not None:
                                while len(next_collected_tool_calls) <= tool_index:
                                    next_collected_tool_calls.append(None)
                                next_collected_tool_calls[tool_index] = new_call
                            else:
                                next_collected_tool_calls.append(new_call)
                            
                            api_logger.debug(f"第 {iteration} 轮新增工具调用: {new_call['id']}, 名称: {new_call['function']['name']}, 初始参数: {new_call['function']['arguments']}")
                            
                            # 发送工具调用开始的状态信息
                            tool_status = {
                                "type": "tool_call_start",
                                "tool_call_id": new_call['id'],
                                "tool_name": new_call['function']['name'],
                                "status": "preparing"
                            }
                            yield ("", conversation_id, tool_status)
                
                content_chunk = delta.content or ""
                next_collected_content += content_chunk
                
                if content_chunk:
                    yield content_chunk
        
        # 更新当前内容和工具调用
        current_content = next_collected_content
        
        # 检查是否有新的工具调用需要处理
        if next_collected_tool_calls:
            # 过滤掉None值
            current_tool_calls = [tc for tc in next_collected_tool_calls if tc is not None]
            api_logger.info(f"第 {iteration} 轮响应中检测到 {len(current_tool_calls)} 个新的工具调用")
        else:
            api_logger.info(f"第 {iteration} 轮响应中没有新的工具调用，结束处理")
            current_tool_calls = None
    
    if iteration >= max_iterations:
        api_logger.warning(f"工具调用达到最大迭代次数 {max_iterations}，强制结束")
    
    api_logger.info(f"流式工具调用处理完成，共进行了 {iteration} 轮，最终内容长度: {len(current_content)}")
    
    # 发送工具处理完成状态
    if iteration > 0:
        tool_status = {
            "type": "tools_completed",
            "status": "completed"
        }
        yield ("", conversation_id, tool_status) 