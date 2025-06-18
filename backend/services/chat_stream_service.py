from typing import Dict, List, Any, AsyncGenerator, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import aiohttp
import base64
import asyncio

from backend.schemas.chat import ChatRequest
from backend.utils.logging import api_logger
from backend.crud.chat import create_chat, get_chat, add_message, update_chat_agent
from backend.crud.agent import agent as agent_crud
from backend.services.memory import memory_service
from backend.services.openai_client import openai_client_service
from backend.services.chat_tool_handler import chat_tool_handler
from backend.services.chat_tool_processor import chat_tool_processor
from backend.services.chat_session_manager import chat_session_manager
from backend.crud.note_session import note_session


class ChatStreamService:
    """流式聊天响应服务"""
    
    @staticmethod
    async def _process_tool_calls_with_interaction_flow(
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
        session_id: int,
        db: Optional[AsyncSession] = None,
        message_id: Optional[int] = None,
        interaction_flow: List[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        max_iterations: int = 20  # 防止无限循环
    ):
        """
        递归处理工具调用，支持无限次调用（流式版本），并记录到交互流程中
        """
        if interaction_flow is None:
            interaction_flow = []
            
        iteration = 0
        current_content = content
        current_tool_calls = tool_calls
        
        # 记录工具调用历史，防止重复调用
        tool_call_history = []
        consecutive_failures = 0  # 连续失败计数
        max_consecutive_failures = 3  # 最大连续失败次数
        
        # 进行递归处理
        while current_tool_calls and iteration < max_iterations:
            iteration += 1
            api_logger.info(f"开始第 {iteration} 轮工具调用处理，共 {len(current_tool_calls)} 个工具调用")
            
            # 检测是否有重复的工具调用
            current_tool_signature = []
            for tc in current_tool_calls:
                if tc is not None and tc.get('function'):
                    signature = f"{tc['function']['name']}:{tc['function']['arguments']}"
                    current_tool_signature.append(signature)
            
            # 检查是否与最近的工具调用重复
            if tool_call_history and current_tool_signature == tool_call_history[-1]:
                api_logger.warning(f"检测到重复的工具调用，停止处理：{current_tool_signature}")
                break
            
            # 检查是否连续多次调用同一组工具
            if len(tool_call_history) >= 3:
                last_three = tool_call_history[-3:]
                if all(sig == current_tool_signature for sig in last_three):
                    api_logger.warning(f"检测到连续多次重复工具调用，停止处理：{current_tool_signature}")
                    break
            
            # 记录当前工具调用
            tool_call_history.append(current_tool_signature)
            
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
                arguments_str = tc['function']['arguments'].strip()
                
                # 对于某些工具（如note_reader），空参数是合法的
                if arguments_str or tc['function']['name'] in ['note_reader']:
                    try:
                        # 验证JSON格式，空字符串默认为空对象
                        if not arguments_str:
                            arguments_str = '{}'
                            tc['function']['arguments'] = arguments_str
                        
                        json.loads(arguments_str)
                        valid_tool_calls.append(tc)
                        
                        if arguments_str == '{}':
                            api_logger.info(f"工具调用 {tc['function']['name']} 使用默认参数（空参数）")
                        else:
                            api_logger.info(f"工具调用 {tc['function']['name']} 参数完整: {arguments_str}")
                    except json.JSONDecodeError as e:
                        api_logger.error(f"工具调用 {tc['function']['name']} 参数JSON格式错误: {arguments_str}, 错误: {e}")
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
            
            # 处理当前的工具调用 - 逐个执行，每执行完一个就继续AI响应
            tool_results = []
            tool_index = 0
            while tool_index < len(valid_tool_calls):
                tc = valid_tool_calls[tool_index]
                # 构造工具调用对象
                func = Function(tc['function']['name'], tc['function']['arguments'])
                tool_call_obj = ToolCall(tc['id'], tc['type'], func)
                
                # 记录工具调用开始到交互流程
                tool_call_start_time = datetime.now()
                tool_call_record = {
                    "type": "tool_call",
                    "id": tool_call_obj.id,
                    "name": tool_call_obj.function.name,
                    "arguments": json.loads(tool_call_obj.function.arguments),
                    "status": "preparing",  # 修改为preparing状态
                    "started_at": tool_call_start_time.isoformat()
                }
                interaction_flow.append(tool_call_record)
                
                # 发送工具调用开始状态
                tool_status = {
                    "type": "tool_call_start",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "preparing"
                }
                # 添加日志确认状态事件发送
                api_logger.info(f"🚀 发送工具调用开始状态: {tool_call_obj.function.name} (ID: {tool_call_obj.id})")
                # 统一使用四元组格式：(content, session_id, reasoning_content, tool_status)
                yield ("", session_id, "", tool_status)
                
                # 立即发送一个空的内容响应，强制刷新异步生成器
                yield ("", session_id, "", None)
                
                # 发送工具调用执行状态
                tool_status = {
                    "type": "tool_call_executing",
                    "tool_call_id": tool_call_obj.id,
                    "tool_name": tool_call_obj.function.name,
                    "status": "executing"
                }
                # 添加日志确认状态事件发送
                api_logger.info(f"⚙️ 发送工具调用执行状态: {tool_call_obj.function.name} (ID: {tool_call_obj.id})")
                # 统一使用四元组格式：(content, session_id, reasoning_content, tool_status)
                yield ("", session_id, "", tool_status)
                
                # 立即发送一个空的内容响应，强制刷新异步生成器
                yield ("", session_id, "", None)
                
                # 执行单个工具调用（传递message_id关联到特定消息）
                try:
                    # 获取agent的数据库ID，避免在handle_tool_calls中懒加载
                    # 修复：避免在异步上下文中访问SQLAlchemy关系属性
                    agent_db_id = getattr(agent, 'id', None) if agent else None
                    
                    # 更新交互流程中的工具调用记录为执行中
                    tool_call_record["status"] = "executing"
                    
                    # 创建异步任务来执行工具调用
                    async def execute_tool():
                        return await chat_tool_handler.handle_tool_calls(
                            [tool_call_obj], 
                            agent, 
                            db,  # 传递数据库连接，保存工具调用记录
                            session_id,
                            message_id=message_id,  # 关联到特定消息
                            user_id=user_id,  # 传递用户ID
                            agent_id=agent_db_id  # 传递agent_id，避免懒加载
                        )
                    
                    # 状态更新任务
                    async def send_progress_updates():
                        execution_time = 0
                        while True:
                            await asyncio.sleep(1)  # 每秒发送一次执行状态
                            execution_time += 1
                            
                            # 发送持续的执行状态更新
                            progress_status = {
                                "type": "tool_call_executing",
                                "tool_call_id": tool_call_obj.id,
                                "tool_name": tool_call_obj.function.name,
                                "status": "executing",
                                "execution_time": execution_time,
                                "message": f"工具正在执行中... ({execution_time}s)"
                            }
                            yield ("", session_id, "", progress_status)
                            
                            # 为执行时间较长的工具添加更详细的进度信息
                            if tool_call_obj.function.name == "note_editor" and execution_time > 2:
                                progress_status["message"] = f"正在编辑笔记内容，请稍候... ({execution_time}s)"
                                yield ("", session_id, "", progress_status)
                    
                    # 同时运行工具执行和状态更新
                    tool_task = asyncio.create_task(execute_tool())
                    
                    # 在工具执行期间持续发送状态更新
                    execution_time = 0
                    while not tool_task.done():
                        try:
                            # 等待1秒或工具完成
                            await asyncio.wait_for(asyncio.shield(tool_task), timeout=1.0)
                            break  # 工具执行完成
                        except asyncio.TimeoutError:
                            # 超时，发送进度更新
                            execution_time += 1
                            progress_status = {
                                "type": "tool_call_executing",
                                "tool_call_id": tool_call_obj.id,
                                "tool_name": tool_call_obj.function.name,
                                "status": "executing",
                                "execution_time": execution_time,
                                "message": f"工具正在执行中... ({execution_time}s)"
                            }
                            
                            # 为不同工具添加特定的进度信息
                            if tool_call_obj.function.name == "note_editor":
                                if execution_time <= 2:
                                    progress_status["message"] = f"正在分析笔记内容... ({execution_time}s)"
                                elif execution_time <= 4:
                                    progress_status["message"] = f"正在处理编辑操作... ({execution_time}s)"
                                else:
                                    progress_status["message"] = f"正在保存笔记更改... ({execution_time}s)"
                            elif tool_call_obj.function.name == "note_reader":
                                progress_status["message"] = f"正在读取笔记内容... ({execution_time}s)"
                            
                            yield ("", session_id, "", progress_status)
                    
                    # 获取工具执行结果
                    single_result, single_tool_data = await tool_task
                    
                    # 收集工具结果
                    tool_results.extend(single_result)
                    
                    # 重置连续失败计数（工具执行成功）
                    consecutive_failures = 0
                    
                    # 更新交互流程中的工具调用记录
                    tool_call_end_time = datetime.now()
                    tool_call_record["status"] = "completed"
                    tool_call_record["completed_at"] = tool_call_end_time.isoformat()
                    tool_call_record["result"] = json.loads(single_result[0]["content"]) if single_result else None
                    
                    # 发送工具调用完成状态，包含结果内容
                    tool_result_content = single_result[0]["content"] if single_result else ""
                    tool_status = {
                        "type": "tool_call_completed",
                        "tool_call_id": tool_call_obj.id,
                        "tool_name": tool_call_obj.function.name,
                        "status": "completed",
                        "result": tool_result_content
                    }
                    # 添加日志确认状态事件发送
                    api_logger.info(f"✅ 发送工具调用完成状态: {tool_call_obj.function.name} (ID: {tool_call_obj.id}), 结果长度: {len(tool_result_content)}")
                    # 统一使用四元组格式：(content, session_id, reasoning_content, tool_status)
                    yield ("", session_id, "", tool_status)
                    
                    # 立即将这个工具调用和结果添加到消息列表，然后调用API获取基于此工具结果的响应
                    # 只使用初始内容，避免累积重复
                    messages.append({
                        "role": "assistant",
                        "content": content if iteration == 1 else "",  # 只在第一轮使用初始内容
                        "tool_calls": [
                            {
                                "id": tc['id'],
                                "type": "function",
                                "function": {
                                    "name": tc['function']['name'],
                                    "arguments": tc['function']['arguments']
                                }
                            }
                        ]
                    })
                    
                    # 添加工具结果
                    for tool_result in single_result:
                        messages.append(tool_result)
                    
                    # 立即调用API获取基于此工具结果的响应
                    api_logger.info(f"第 {iteration} 轮工具 {tool_call_obj.function.name} 执行完成，立即获取AI响应")
                    
                    next_response = await openai_client_service.async_client.chat.completions.create(
                        model=use_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        stream=True,
                        tools=tools if has_tools else None
                    )
                    
                    # 收集这次AI响应的内容和新工具调用
                    stream_content = ""
                    stream_tool_calls = []
                    
                    async for chunk in next_response:
                        if chunk.choices[0].delta.content:
                            stream_content += chunk.choices[0].delta.content
                            yield chunk.choices[0].delta.content  # 使用单个内容格式，避免混乱的三元组
                        
                        # 检查新的工具调用
                        if chunk.choices[0].delta.tool_calls:
                            for delta_tool_call in chunk.choices[0].delta.tool_calls:
                                # 扩展工具调用列表以适应索引
                                while len(stream_tool_calls) <= delta_tool_call.index:
                                    stream_tool_calls.append(None)
                                
                                if stream_tool_calls[delta_tool_call.index] is None:
                                    stream_tool_calls[delta_tool_call.index] = {
                                        "id": delta_tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": delta_tool_call.function.name if delta_tool_call.function.name else "",
                                            "arguments": delta_tool_call.function.arguments if delta_tool_call.function.arguments else ""
                                        }
                                    }
                                else:
                                    # 累积参数
                                    if delta_tool_call.function.arguments:
                                        stream_tool_calls[delta_tool_call.index]["function"]["arguments"] += delta_tool_call.function.arguments
                    
                    # ✅ 修复：将工具调用后的AI响应内容添加到交互流程中
                    if stream_content.strip():
                        interaction_flow.append({
                            "type": "text",
                            "content": stream_content,
                            "timestamp": datetime.now().isoformat()
                        })
                        api_logger.info(f"已将工具调用后的AI响应添加到交互流程: 内容长度={len(stream_content)}")
                    
                    # 更新当前内容和工具调用以供下次循环
                    current_content = stream_content
                    current_tool_calls = [tc for tc in stream_tool_calls if tc is not None]
                    
                    api_logger.info(f"第 {iteration} 轮工具 {tool_call_obj.function.name} 后得到 AI 响应，内容长度: {len(stream_content)}, 新工具调用数量: {len(current_tool_calls)}")
                    
                    # 进入下一个工具
                    tool_index += 1
                    
                    # 如果没有新的工具调用，处理下一个工具；如果有新的工具调用，直接跳到下一轮iteration
                    if current_tool_calls:
                        api_logger.info(f"检测到新工具调用，跳转到下一轮iteration")
                        break  # 跳出当前工具循环，进入下一轮iteration
                        
                except Exception as e:
                    api_logger.error(f"工具调用失败: {e}")
                    # 更新交互流程中的工具调用记录
                    tool_call_end_time = datetime.now()
                    tool_call_record["status"] = "failed"
                    tool_call_record["completed_at"] = tool_call_end_time.isoformat()
                    tool_call_record["error"] = str(e)
                    
                    # 更新连续失败计数
                    consecutive_failures += 1
                    
                    # 发送工具调用失败状态
                    tool_status = {
                        "type": "tool_call_failed",
                        "tool_call_id": tool_call_obj.id,
                        "tool_name": tool_call_obj.function.name,
                        "status": "failed",
                        "error": str(e)
                    }
                    yield ("", session_id, "", tool_status)
                    
                    # 如果连续失败次数过多，也要结束整个循环
                    if consecutive_failures >= max_consecutive_failures:
                        api_logger.warning(f"连续工具调用失败 {consecutive_failures} 次，结束所有工具处理")
                        break
                    
                    # 跳过这个工具，继续下一个
                    tool_index += 1
                    continue
            
            # 如果没有更多工具调用了，结束循环
            if not current_tool_calls:
                api_logger.info(f"第 {iteration} 轮处理完成，没有更多工具调用")
                break
        
        # 发送最终完成状态
        final_status = {
            "type": "tools_processing_completed",
            "total_iterations": iteration,
            "interaction_flow": interaction_flow
        }
        yield ("", session_id, "", final_status)
        
        api_logger.info(f"工具调用处理完成，共进行了 {iteration} 轮，交互流程记录数: {len(interaction_flow)}")

    @staticmethod
    async def generate_chat_stream(
        chat_request: ChatRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        调用OpenAI API生成对话流式响应，并保存对话记录
        
        返回的是生成内容的异步生成器。第一个内容会额外返回session_id
        """
        # 初始化交互流程记录
        interaction_flow = []
        
        try:
            api_logger.info(f"开始调用OpenAI流式API, 模型: {openai_client_service.model}, API地址: {openai_client_service.async_client.base_url}")
            
            # 获取或确认聊天会话ID
            session_id = chat_request.session_id
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
                api_logger.info(f"流式响应使用Agent: AI助手, ID={current_agent.public_id}")
            
            if db and user_id:
                # 获取或创建聊天会话
                if not session_id:
                    # 创建新的聊天会话
                    if note_id:
                        # 查询笔记信息，获取标题
                        from backend.models.note import Note
                        from sqlalchemy import select
                        from backend.utils.id_converter import IDConverter
                        
                        # 初始化note变量
                        note = None
                        
                        # 将 public_id 转换为数据库 ID
                        db_note_id = await IDConverter.get_note_db_id(db, note_id)
                        if not db_note_id:
                            api_logger.warning(f"笔记 {note_id} 不存在，跳过笔记关联")
                        else:
                            # 查询笔记是否存在
                            note_stmt = select(Note).where(
                                Note.id == db_note_id,
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
                            # 🔍 使用新的多对多关联方式
                            api_logger.info(f"🔍 流式服务: 开始处理笔记关联: note_id={note_id}, session_id={chat.public_id}")
                            
                            # 检查是否已有主要会话，如果没有则设为主要会话
                            existing_primary = await note_session.get_primary_session_by_note(db, note_id)
                            is_primary = existing_primary is None  # 如果没有主要会话，这个就是主要会话
                            
                            api_logger.info(f"🔍 流式服务: 现有主要会话: {existing_primary}, 新会话是否为主要: {is_primary}")
                            
                            await note_session.create_note_session_link(
                                db, 
                                note_id=note_id, 
                                session_id=chat.public_id,
                                is_primary=is_primary
                            )
                            
                            api_logger.info(f"🔍 流式服务: 笔记ID {note_id} 已关联到会话ID {chat.public_id}，是否为主要会话: {is_primary}")
                            
                            # 验证关联是否真的被创建
                            verification_sessions = await note_session.get_sessions_by_note(db, note_id)
                            verification_session_ids = [s.public_id for s in verification_sessions]
                            api_logger.info(f"🔍 流式服务: 验证笔记 {note_id} 关联的会话列表: {verification_session_ids}")
                            
                            if chat.public_id in verification_session_ids:
                                api_logger.info(f"✅ 流式服务: 笔记 {note_id} 与会话 {chat.public_id} 关联创建成功")
                            else:
                                api_logger.error(f"❌ 流式服务: 笔记 {note_id} 与会话 {chat.public_id} 关联创建失败！")
                    else:
                        # 常规创建会话
                        chat = await create_chat(db, user_id, agent_id=agent_id)
                    
                    session_id = chat.public_id
                    new_session_created = True
                    api_logger.info(f"创建新聊天会话: session_id={session_id}, user_id={user_id}, agent_id={agent_id}")
                else:
                    # 验证会话存在且属于当前用户
                    chat = await get_chat(db, session_id)
                    if not chat or chat.user_id != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="聊天会话不存在或无权访问"
                        )
                    
                    # 如果当前会话没有关联Agent，但请求中有Agent，则更新会话
                    if agent_id and not chat.agent_id:
                        await update_chat_agent(db, session_id=session_id, agent_id=agent_id)
                        api_logger.info(f"更新会话的Agent: session_id={session_id}, agent_id={agent_id}")
                    
                    # 如果当前会话已关联Agent，使用该Agent的信息
                    elif chat.agent_id and not agent_id:
                        agent_id = chat.agent_id
                        current_agent = await agent_crud.get_agent_by_id(db, agent_id=agent_id)
                        if current_agent:
                            api_logger.info(f"从会话加载Agent: AI助手, ID={current_agent.public_id}")
                            
                    api_logger.info(f"使用现有会话: session_id={session_id}")
            else:
                # 如果session_id已经存在，直接使用（API层预创建的情况）
                if session_id:
                    api_logger.info(f"使用API层预创建的会话: session_id={session_id}")
                else:
                    api_logger.warning("没有数据库连接或用户ID，无法创建或验证会话")
            
            # 获取用户发送的内容
            user_content = chat_request.content
            
            # 检查是否跳过用户消息创建（用于编辑重新执行场景）
            skip_user_message = getattr(chat_request, '_skip_user_message', False)
            
            if not skip_user_message:
                # 正常情况：处理图片消息 - 构建包含图片的消息格式
                user_message_content = []
                
                # 添加文本内容
                if user_content and user_content.strip():
                    user_message_content.append({
                        "type": "text",
                        "text": user_content
                    })
                
                # 添加图片内容
                if hasattr(chat_request, 'images') and chat_request.images:
                    api_logger.info(f"流式聊天用户消息包含 {len(chat_request.images)} 张图片，已尝试转换为base64格式")
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
                                    else:
                                        # 如果下载失败，仍然尝试使用原URL
                                        user_message_content.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image.url,
                                                "detail": "high"
                                            }
                                        })
                        except Exception as download_error:
                            # 如果转换失败，回退到原URL
                            user_message_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": image.url,
                                    "detail": "high"
                                }
                            })
                    
                    api_logger.info(f"流式聊天用户消息包含 {len(chat_request.images)} 张图片，已尝试转换为base64格式")
                
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
                memory_service.add_user_message(session_id, content_for_memory, user_id)
                
                # 保存用户消息到数据库（保存完整的图片信息）
                if db and user_id and session_id:
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
                            session_id=session_id,
                            role="user",
                            content=json.dumps(full_message_content, ensure_ascii=False)
                        )
                        api_logger.info(f"保存包含{len(chat_request.images)}张图片的用户消息到数据库")
                    else:
                        # 纯文本消息，直接保存
                        await add_message(
                            db=db,
                            session_id=session_id,
                            role="user",
                            content=content_for_memory
                        )
            else:
                api_logger.info(f"编辑重新执行模式：跳过用户消息创建，直接使用现有记忆")
                
                # 即使在编辑重新执行模式下，也需要处理图片数据，构建相关变量
                user_message_content = []
                
                # 添加文本内容
                if user_content and user_content.strip():
                    user_message_content.append({
                        "type": "text",
                        "text": user_content
                    })
                
                # 添加图片内容
                if hasattr(chat_request, 'images') and chat_request.images:
                    api_logger.info(f"编辑重新执行：用户消息包含 {len(chat_request.images)} 张图片，处理图片格式")
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
                                    else:
                                        # 如果下载失败，仍然尝试使用原URL
                                        user_message_content.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image.url,
                                                "detail": "high"
                                            }
                                        })
                        except Exception as download_error:
                            api_logger.warning(f"编辑重新执行：图片处理失败 {image.url}: {download_error}")
                            # 如果转换失败，回退到原URL
                            user_message_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": image.url,
                                    "detail": "high"
                                }
                            })
                
                # 构建最终的用户消息
                if len(user_message_content) > 1:  # 有图片或多个内容元素
                    final_user_message = user_message_content
                else:  # 只有文本
                    final_user_message = user_content
            
            # 从记忆服务获取完整的消息记录
            messages = memory_service.get_messages(session_id)
            
            # 如果当前请求包含图片，需要替换最后一条用户消息为包含图片的格式
            # 注意：编辑重新执行模式下也需要处理图片数据
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
            
            api_logger.debug(f"流式请求消息: {json.dumps(messages, ensure_ascii=False)}")
            
            # 如果有Agent，使用Agent的设置
            if current_agent:
                # 确保用户的MCP服务器已加载（如果有的话）
                try:
                    from backend.services.mcp_service import mcp_service
                    if user_id and mcp_service.is_enabled():
                        await mcp_service.ensure_user_servers_loaded(user_id)
                        api_logger.info(f"已为用户 {user_id} 加载MCP服务器")
                except Exception as e:
                    api_logger.warning(f"加载用户MCP服务器失败: {e}")
                
                # 优先使用请求中的模型，如果没有提供则使用Agent的默认模型
                if chat_request.model:
                    use_model = chat_request.model
                    api_logger.info(f"流式响应使用请求中指定的模型: {use_model}")
                else:
                    # 先备份使用默认模型，以防指定模型不可用
                    agent_model = current_agent.model
                    use_model = agent_model if agent_model else openai_client_service.model
                    api_logger.info(f"流式响应使用Agent默认模型: {use_model}")
                
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
                api_logger.info(f"流式响应没有Agent，使用请求中指定的模型: {use_model}")
            else:
                # 都没有则使用默认模型
                api_logger.info(f"流式响应使用系统默认模型: {use_model}")
            
            # 获取工具配置
            tools = await chat_tool_handler.get_agent_tools_async(current_agent, user_id, db) if current_agent else []
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
                    
                    # 添加详细的工具格式调试日志
                    for i, tool in enumerate(tools[:3]):  # 只显示前3个工具
                        api_logger.info(f"工具 {i+1}: {json.dumps(tool, ensure_ascii=False, indent=2)}")
                
                # 记录请求参数详情
                api_logger.info(f"[流式请求] API调用参数详情: model={use_model}, max_tokens={max_tokens}, temperature={temperature}, 消息数量={len(messages)}, 启用工具={has_tools}")
                
                # 添加完整API参数的调试日志（不包含敏感信息）
                debug_params = api_params.copy()
                if 'tools' in debug_params:
                    # 显示工具的基本信息而不是完整内容
                    tools_info = []
                    for tool in debug_params['tools']:
                        if tool.get('type') == 'mcp':
                            tools_info.append({
                                'type': 'mcp',
                                'server': tool.get('mcp', {}).get('server'),
                                'tool_name': tool.get('mcp', {}).get('tool', {}).get('name')
                            })
                        else:
                            tools_info.append({
                                'type': tool.get('type'),
                                'name': tool.get('function', {}).get('name')
                            })
                    debug_params['tools'] = tools_info
                api_logger.info(f"[调试] 完整API参数: {json.dumps(debug_params, ensure_ascii=False, indent=2)}")
                
                # 临时：显示实际发送的工具格式（用于调试）
                if 'tools' in api_params and api_params['tools']:
                    api_logger.info(f"[实际发送] 工具数量: {len(api_params['tools'])}")
                    api_logger.info(f"[实际发送] 第一个工具: {json.dumps(api_params['tools'][0], ensure_ascii=False, indent=2)}")
                
                # 验证工具格式是否正确
                if has_tools and tools:
                    api_logger.info(f"[验证] 工具数据类型: {type(tools)}")
                    api_logger.info(f"[验证] 第一个工具类型: {type(tools[0]) if tools else 'None'}")
                    if tools:
                        first_tool = tools[0]
                        api_logger.info(f"[验证] 第一个工具内容: {json.dumps(first_tool, ensure_ascii=False)}")
                        
                        # 检查MCP工具格式
                        if first_tool.get('type') == 'mcp':
                            mcp_data = first_tool.get('mcp', {})
                            api_logger.info(f"[验证] MCP服务器: {mcp_data.get('server')}")
                            api_logger.info(f"[验证] MCP工具名: {mcp_data.get('tool', {}).get('name')}")
                            api_logger.info(f"[验证] MCP工具描述: {mcp_data.get('tool', {}).get('description', '')[:50]}...")
                else:
                    api_logger.info("[验证] 没有工具数据")
                
                # 直接使用异步客户端，但开启流式响应
                response = await openai_client_service.async_client.chat.completions.create(**api_params)
                
                api_logger.info(f"[流式响应] 获取到流式响应: {type(response)}")
                
                # 这里response是一个异步迭代器，需要使用async for遍历每个部分
                collected_content = ""
                collected_reasoning_content = ""  # 添加思考内容收集
                collected_tool_calls = []
                is_first_chunk = True
                chunk_count = 0
                current_text_segment = ""  # 当前文本片段
                current_reasoning_segment = ""  # 当前思考片段
                
                async for chunk in response:
                    chunk_count += 1
                    
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        
                        # 检查是否有工具调用
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            # 如果当前有累积的文本内容，先保存到交互流程中
                            if current_text_segment.strip():
                                interaction_flow.append({
                                    "type": "text",
                                    "content": current_text_segment,
                                    "timestamp": datetime.now().isoformat()
                                })
                                current_text_segment = ""
                            
                            # 如果当前有累积的思考内容，先保存到交互流程中
                            if current_reasoning_segment.strip():
                                interaction_flow.append({
                                    "type": "reasoning",
                                    "content": current_reasoning_segment,
                                    "timestamp": datetime.now().isoformat()
                                })
                                current_reasoning_segment = ""
                            
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
                        
                        content_chunk = delta.content or ""
                        reasoning_chunk = ""
                        # 确保reasoning_chunk只包含真正的思考内容，并且是字符串类型
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            reasoning_content = delta.reasoning_content
                            # 只有当reasoning_content是字符串时才使用，避免对象类型的混淆
                            if isinstance(reasoning_content, str):
                                reasoning_chunk = reasoning_content
                            else:
                                api_logger.warning(f"检测到非字符串类型的reasoning_content: {type(reasoning_content)}, 忽略")
                        
                        # 累加总内容（用于记忆和token计算）
                        collected_content += content_chunk
                        collected_reasoning_content += reasoning_chunk
                        
                        # 如果有思考内容，立即保存到交互流程
                        if reasoning_chunk:
                            # 如果当前有累积的正式内容，先保存
                            if current_text_segment.strip():
                                interaction_flow.append({
                                    "type": "text",
                                    "content": current_text_segment,
                                    "timestamp": datetime.now().isoformat()
                                })
                                current_text_segment = ""
                            
                            # 累积思考内容，而不是立即保存
                            current_reasoning_segment += reasoning_chunk
                        
                        # 如果有正式内容，累积到当前段落
                        if content_chunk:
                            # 如果当前有累积的思考内容，先保存
                            if current_reasoning_segment.strip():
                                interaction_flow.append({
                                    "type": "reasoning",
                                    "content": current_reasoning_segment,
                                    "timestamp": datetime.now().isoformat()
                                })
                                current_reasoning_segment = ""
                            
                            current_text_segment += content_chunk
                        
                            # 修复yield格式：统一使用四元组格式或单内容格式
                            if is_first_chunk and (content_chunk or reasoning_chunk):
                                is_first_chunk = False
                                # 第一个chunk需要传递session_id，使用四元组格式
                                yield (content_chunk, session_id, reasoning_chunk or "", None)
                            elif content_chunk or reasoning_chunk:
                                # 后续chunk使用三元组格式：(content, reasoning_content, tool_status)
                                yield (content_chunk, reasoning_chunk or "", None)
                        
                        # 如果只有推理内容没有正式内容，也要yield推理内容
                        elif reasoning_chunk:
                            if is_first_chunk:
                                is_first_chunk = False
                                # 第一个chunk需要传递session_id，使用四元组格式
                                yield ("", session_id, reasoning_chunk, None)
                            else:
                                # 后续chunk使用三元组格式：(content, reasoning_content, tool_status)
                                yield ("", reasoning_chunk, None)
                
                # 如果最后还有未保存的文本内容，保存到交互流程中
                if current_text_segment.strip():
                    interaction_flow.append({
                        "type": "text",
                        "content": current_text_segment,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # 如果最后还有未保存的思考内容，保存到交互流程中
                if current_reasoning_segment.strip():
                    interaction_flow.append({
                        "type": "reasoning",
                        "content": current_reasoning_segment,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # 流式响应结束，检查是否有工具调用需要处理
                api_logger.info(f"流式响应完成，共接收 {chunk_count} 个块")
                api_logger.info(f"流式响应内容长度: {len(collected_content)}")
                api_logger.info(f"流式响应思考内容长度: {len(collected_reasoning_content)}")
                api_logger.info(f"收集到的工具调用: {len(collected_tool_calls)} 个")
                
                # 先保存AI消息（即使内容为空，也要保存以便后续更新）
                ai_message = None
                saved_prompt_tokens = 0  # 提前保存prompt_tokens
                if db and user_id and session_id:
                    # 估算token数量（简单实现）
                    tokens = len(collected_content) // 4 if collected_content else 0
                    prompt_tokens = len(str(messages)) // 4
                    total_tokens = tokens + prompt_tokens
                    saved_prompt_tokens = prompt_tokens  # 保存这个值供后续使用
                    
                    ai_message = await add_message(
                        db=db,
                        session_id=session_id,
                        role="assistant",
                        content=collected_content or "",  # 即使为空也保存
                        tokens=tokens,
                        prompt_tokens=prompt_tokens,
                        total_tokens=total_tokens,
                        agent_id=agent_id
                    )
                    api_logger.info(f"AI消息已保存: id={ai_message.public_id}, 初始内容长度: {len(collected_content or '')}")
                
                # 检查是否有有效的工具调用需要处理
                valid_tool_calls = [tc for tc in collected_tool_calls if tc is not None and tc.get('function', {}).get('name')]
                
                if valid_tool_calls:
                    api_logger.info(f"检测到 {len(valid_tool_calls)} 个有效工具调用，开始递归处理")
                    # 递归处理工具调用，支持无限次调用
                    final_content = collected_content or ""  # 保存初始内容，确保不为None
                    async for content_chunk in ChatStreamService._process_tool_calls_with_interaction_flow(
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
                        session_id,
                        db,
                        message_id=ai_message.public_id if ai_message else None,
                        interaction_flow=interaction_flow,
                        user_id=user_id
                    ):
                        if isinstance(content_chunk, tuple):
                            # 工具状态信息
                            yield content_chunk
                        else:
                            # 内容块 - 累积到最终内容中
                            yield content_chunk
                            final_content += content_chunk
                    
                    # 构建最终的JSON结构
                    final_json_content = {
                        "type": "agent_response",
                        "interaction_flow": interaction_flow
                    }
                    
                    # 更新AI消息内容
                    if ai_message:
                        ai_message.content = json.dumps(final_json_content, ensure_ascii=False)
                        ai_message.tokens = len(final_content) // 4
                        # 使用之前保存的prompt_tokens值，避免延迟加载
                        ai_message.total_tokens = saved_prompt_tokens + ai_message.tokens
                        await db.commit()
                        await db.refresh(ai_message)
                    
                    # 保存到记忆 - 使用最终完整内容（纯文本，用于对话上下文）
                    if final_content:
                        memory_service.add_assistant_message(session_id, final_content, user_id)
                        api_logger.info(f"流式聊天完成，最终内容长度: {len(final_content)}")
                else:
                    # 没有工具调用，检查是否有交互流程
                    if interaction_flow:
                        final_json_content = {
                            "type": "agent_response",
                            "interaction_flow": interaction_flow
                        }
                        
                        # 更新AI消息内容
                        if ai_message:
                            ai_message.content = json.dumps(final_json_content, ensure_ascii=False)
                            await db.commit()
                            await db.refresh(ai_message)
                        
                        api_logger.info("fallback模式：没有工具调用，保存包含交互流程的JSON结构")
                    
                    # 保存纯文本内容到记忆（用于对话上下文）
                    if collected_content:
                        memory_service.add_assistant_message(session_id, collected_content, user_id)
                        api_logger.info(f"fallback模式：流式聊天完成，内容长度: {len(collected_content)}")
                
                # 检查是否需要自动生成标题
                if db and session_id and user_content:
                    await chat_session_manager.auto_generate_title_if_needed(db, session_id, user_content)
            
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
                        
                        api_logger.info(f"使用默认模型获取到流式响应: {type(response)}")
                        
                        # 处理流式响应（与上面相同的逻辑）
                        collected_content = ""
                        collected_reasoning_content = ""  # 添加思考内容收集
                        collected_tool_calls = []
                        is_first_chunk = True
                        chunk_count = 0
                        current_text_segment = ""  # 当前文本片段
                        current_reasoning_segment = ""  # 当前思考片段
                        
                        async for chunk in response:
                            chunk_count += 1
                            
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
                                
                                content_chunk = delta.content or ""
                                reasoning_chunk = ""
                                # 确保reasoning_chunk只包含真正的思考内容，并且是字符串类型
                                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                                    reasoning_content = delta.reasoning_content
                                    # 只有当reasoning_content是字符串时才使用，避免对象类型的混淆
                                    if isinstance(reasoning_content, str):
                                        reasoning_chunk = reasoning_content
                                    else:
                                        api_logger.warning(f"检测到非字符串类型的reasoning_content: {type(reasoning_content)}, 忽略")
                                
                                # 累加总内容（用于记忆和token计算）
                                collected_content += content_chunk
                                collected_reasoning_content += reasoning_chunk
                                
                                # 如果有思考内容，立即保存到交互流程
                                if reasoning_chunk:
                                    # 如果当前有累积的正式内容，先保存
                                    if current_text_segment.strip():
                                        interaction_flow.append({
                                            "type": "text",
                                            "content": current_text_segment,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        current_text_segment = ""
                                    
                                    # 累积思考内容，而不是立即保存
                                    current_reasoning_segment += reasoning_chunk
                                
                                # 如果有正式内容，累积到当前段落
                                if content_chunk:
                                    # 如果当前有累积的思考内容，先保存
                                    if current_reasoning_segment.strip():
                                        interaction_flow.append({
                                            "type": "reasoning",
                                            "content": current_reasoning_segment,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                        current_reasoning_segment = ""
                                    
                                    current_text_segment += content_chunk
                                
                                # 修复yield格式：统一使用四元组格式或单内容格式
                                if is_first_chunk and (content_chunk or reasoning_chunk):
                                    is_first_chunk = False
                                    # 第一个chunk需要传递session_id，使用四元组格式
                                    yield (content_chunk, session_id, reasoning_chunk or "", None)
                                elif content_chunk or reasoning_chunk:
                                    # 后续chunk使用三元组格式：(content, reasoning_content, tool_status)
                                    yield (content_chunk, reasoning_chunk or "", None)
                        
                                # 如果只有推理内容没有正式内容，也要yield推理内容
                                elif reasoning_chunk:
                                    if is_first_chunk:
                                        is_first_chunk = False
                                        # 第一个chunk需要传递session_id，使用四元组格式
                                        yield ("", session_id, reasoning_chunk, None)
                                    else:
                                        # 后续chunk使用三元组格式：(content, reasoning_content, tool_status)
                                        yield ("", reasoning_chunk, None)
                        
                        # 如果最后还有文本内容，保存到交互流程中
                        if current_text_segment.strip():
                            interaction_flow.append({
                                "type": "text",
                                "content": current_text_segment,
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        # 如果最后还有思考内容，保存到交互流程中
                        if current_reasoning_segment.strip():
                            interaction_flow.append({
                                "type": "reasoning",
                                "content": current_reasoning_segment,
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        # 处理工具调用和保存消息（与上面相同的逻辑）
                        ai_message = None
                        saved_prompt_tokens_fallback = 0  # 提前保存prompt_tokens
                        if db and user_id and session_id:
                            tokens = len(collected_content) // 4 if collected_content else 0
                            prompt_tokens = len(str(messages)) // 4
                            total_tokens = tokens + prompt_tokens
                            saved_prompt_tokens_fallback = prompt_tokens  # 保存这个值供后续使用
                            
                            ai_message = await add_message(
                                db=db,
                                session_id=session_id,
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
                            async for content_chunk in ChatStreamService._process_tool_calls_with_interaction_flow(
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
                                session_id,
                                db,
                                message_id=ai_message.public_id if ai_message else None,
                                interaction_flow=interaction_flow,
                                user_id=user_id
                            ):
                                if isinstance(content_chunk, tuple):
                                    yield content_chunk
                                else:
                                    yield content_chunk
                                    final_content += content_chunk
                            
                            # 构建最终的JSON结构
                            final_json_content = {
                                "type": "agent_response",
                                "interaction_flow": interaction_flow
                            }
                            
                            # 更新AI消息内容
                            if ai_message:
                                ai_message.content = json.dumps(final_json_content, ensure_ascii=False)
                                ai_message.tokens = len(final_content) // 4
                                # 使用之前保存的prompt_tokens值，避免延迟加载
                                ai_message.total_tokens = saved_prompt_tokens_fallback + ai_message.tokens
                                await db.commit()
                                await db.refresh(ai_message)
                            
                            # 保存最终内容到记忆
                            if final_content:
                                memory_service.add_assistant_message(session_id, final_content, user_id)
                                api_logger.info(f"流式聊天完成，最终内容长度: {len(final_content)}")
                        else:
                            # 没有工具调用，检查是否有交互流程
                            if interaction_flow:
                                final_json_content = {
                                    "type": "agent_response",
                                    "interaction_flow": interaction_flow
                                }
                                
                                # 更新AI消息内容
                                if ai_message:
                                    ai_message.content = json.dumps(final_json_content, ensure_ascii=False)
                                    await db.commit()
                                    await db.refresh(ai_message)
                                
                                api_logger.info("fallback模式：没有工具调用，保存包含交互流程的JSON结构")
                            
                            # 保存纯文本内容到记忆（用于对话上下文）
                            if collected_content:
                                memory_service.add_assistant_message(session_id, collected_content, user_id)
                                api_logger.info(f"fallback模式：流式聊天完成，内容长度: {len(collected_content)}")
                        
                        # 检查是否需要自动生成标题
                        if db and session_id and user_content:
                            await chat_session_manager.auto_generate_title_if_needed(db, session_id, user_content)
                    
                    except Exception as fallback_error:
                        api_logger.error(f"使用默认模型 {openai_client_service.model} 流式响应仍然失败: {str(fallback_error)}", exc_info=True)
                
                # 发送错误信息作为流式内容
                error_message = f"AI服务暂时不可用: {str(api_error)}"
                
                # 总是返回会话ID，不管是否是新会话
                # 使用四元组格式保持一致性
                yield (error_message, session_id, "", None)
                
                # 保存错误信息到数据库
                if db and user_id and session_id:
                    await add_message(
                        db=db,
                        session_id=session_id,
                        role="assistant",
                        content=error_message
                    )
        
        except Exception as e:
            api_logger.error(f"流式聊天生成失败: {str(e)}", exc_info=True)
            
            # 发送一个错误消息，包含会话ID
            error_message = f"AI服务发生错误: {str(e)}"
            # 使用四元组格式保持一致性
            yield (error_message, session_id, "", None)


# 创建全局流式聊天服务实例
chat_stream_service = ChatStreamService() 