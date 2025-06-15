#!/usr/bin/env python3
"""
笔记MCP服务器

提供笔记阅读和编辑功能的MCP服务器。
这个服务器将现有的笔记工具功能通过MCP协议提供给客户端。
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from ..schemas.protocol import (
    MCPRequest, MCPResponse, MCPNotification,
    Tool, ToolInputSchema, ToolResult,
    ServerCapabilities, Implementation,
    InitializeResponse,
    create_response, create_error, create_notification,
    RequestMethod, NotificationType, ErrorCode
)
from backend.utils.logging import app_logger


class NoteMCPServer:
    """笔记MCP服务器"""
    
    def __init__(self, db_session=None):
        self.name = "note-server"
        self.version = "1.0.0"
        self.initialized = False
        self.db_session = db_session
        
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """处理请求"""
        try:
            if request.method == RequestMethod.INITIALIZE:
                return await self._handle_initialize(request)
            elif request.method == RequestMethod.LIST_TOOLS:
                return await self._handle_list_tools(request)
            elif request.method == RequestMethod.CALL_TOOL:
                return await self._handle_call_tool(request)
            elif request.method == RequestMethod.PING:
                return await self._handle_ping(request)
            else:
                return create_response(
                    request.id,
                    error=create_error(ErrorCode.METHOD_NOT_FOUND, f"方法未找到: {request.method}")
                )
        except Exception as e:
            app_logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
            return create_response(
                request.id,
                error=create_error(ErrorCode.INTERNAL_ERROR, f"服务器内部错误: {str(e)}")
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """处理初始化请求"""
        capabilities = ServerCapabilities(
            tools={"listChanged": True},
            logging={}
        )
        
        server_info = Implementation(
            name=self.name,
            version=self.version
        )
        
        result = InitializeResponse(
            protocolVersion="2024-11-05",
            capabilities=capabilities,
            serverInfo=server_info
        )
        
        self.initialized = True
        app_logger.info(f"笔记MCP服务器已初始化")
        return create_response(request.id, result=result.model_dump())
    
    async def _handle_list_tools(self, request: MCPRequest) -> MCPResponse:
        """处理获取工具列表请求"""
        tools = [
            Tool(
                name="read_note",
                description="读取笔记内容。支持通过笔记ID或标题搜索笔记，可指定阅读范围和是否包含元数据。在会话中会自动关联当前笔记。",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "note_id": {
                            "type": "string",
                            "description": "要读取的笔记ID（可选，会话中会自动关联）"
                        },
                        "search_title": {
                            "type": "string",
                            "description": "通过标题搜索笔记，支持模糊匹配"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "开始阅读的行数（从1开始）",
                            "default": 1
                        },
                        "line_count": {
                            "type": "integer",
                            "description": "要读取的行数，-1表示读取全部",
                            "default": -1
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "是否包含笔记元数据",
                            "default": True
                        }
                    }
                )
            ),
            Tool(
                name="edit_note",
                description="编辑笔记内容。支持多种编辑操作：完全替换、追加、前置、插入、替换行、替换文本等。可选择预览模式或立即保存。",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "note_id": {
                            "type": "string",
                            "description": "要编辑的笔记ID（可选，会话中会自动关联）"
                        },
                        "search_title": {
                            "type": "string",
                            "description": "通过标题搜索要编辑的笔记"
                        },
                        "edit_type": {
                            "type": "string",
                            "enum": ["replace", "append", "prepend", "insert", "replace_lines", "replace_text"],
                            "description": "编辑类型：replace(完全替换), append(追加), prepend(前置), insert(插入), replace_lines(替换行), replace_text(替换文本)",
                            "default": "replace"
                        },
                        "content": {
                            "type": "string",
                            "description": "新内容（用于replace、append、prepend、insert、replace_lines操作）"
                        },
                        "title": {
                            "type": "string",
                            "description": "新标题（可选）"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "开始行号（用于replace_lines操作）"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "结束行号（用于replace_lines操作）"
                        },
                        "insert_position": {
                            "type": "string",
                            "description": "插入位置：start(开头), end(结尾), after_line:N(第N行后), before_line:N(第N行前)"
                        },
                        "search_text": {
                            "type": "string",
                            "description": "要搜索的文本（用于replace_text操作）"
                        },
                        "replace_text": {
                            "type": "string",
                            "description": "替换的文本（用于replace_text操作）"
                        },
                        "save_immediately": {
                            "type": "boolean",
                            "description": "是否立即保存（默认为预览模式）",
                            "default": False
                        }
                    }
                )
            ),
            Tool(
                name="create_note",
                description="创建新笔记。可以指定标题、内容，以及是否关联到当前会话。",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "title": {
                            "type": "string",
                            "description": "笔记标题",
                            "default": "新笔记"
                        },
                        "content": {
                            "type": "string",
                            "description": "笔记内容",
                            "default": ""
                        },
                        "link_to_session": {
                            "type": "boolean",
                            "description": "是否关联到当前会话",
                            "default": True
                        }
                    }
                )
            ),
            Tool(
                name="list_notes",
                description="列出用户的笔记。支持搜索、分页和排序。",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "search_query": {
                            "type": "string",
                            "description": "搜索关键词（搜索标题和内容）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量限制",
                            "default": 10
                        },
                        "offset": {
                            "type": "integer",
                            "description": "偏移量（用于分页）",
                            "default": 0
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["created_at", "updated_at", "title"],
                            "description": "排序字段",
                            "default": "updated_at"
                        },
                        "sort_order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "排序顺序",
                            "default": "desc"
                        }
                    }
                )
            )
        ]
        
        return create_response(
            request.id,
            result={"tools": [tool.model_dump() for tool in tools]}
        )
    
    async def _handle_call_tool(self, request: MCPRequest) -> MCPResponse:
        """处理工具调用请求"""
        if not request.params:
            return create_response(
                request.id,
                error=create_error(ErrorCode.INVALID_PARAMS, "缺少工具调用参数")
            )
        
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        try:
            if tool_name == "read_note":
                result = await self._read_note(arguments)
            elif tool_name == "edit_note":
                result = await self._edit_note(arguments)
            elif tool_name == "create_note":
                result = await self._create_note(arguments)
            elif tool_name == "list_notes":
                result = await self._list_notes(arguments)
            else:
                return create_response(
                    request.id,
                    error=create_error(ErrorCode.METHOD_NOT_FOUND, f"工具未找到: {tool_name}")
                )
            
            return create_response(request.id, result=result.model_dump())
            
        except Exception as e:
            app_logger.error(f"工具调用失败 {tool_name}: {str(e)}", exc_info=True)
            return create_response(
                request.id,
                error=create_error(ErrorCode.TOOL_ERROR, f"工具执行失败: {str(e)}")
            )
    
    async def _handle_ping(self, request: MCPRequest) -> MCPResponse:
        """处理ping请求"""
        return create_response(request.id, result={})
    
    async def _read_note(self, arguments: Dict[str, Any]) -> ToolResult:
        """读取笔记内容"""
        try:
            # 导入笔记工具
            from backend.services.tools import NoteReaderTool
            from backend.db.session import get_async_session
            
            # 如果没有数据库会话，创建一个
            if not self.db_session:
                async for db in get_async_session():
                    self.db_session = db
                    break
            
            # 创建笔记阅读工具实例
            reader = NoteReaderTool(
                db_session=self.db_session,
                session_id=arguments.get("session_id")
            )
            
            # 执行读取操作
            result = await reader.read_note(
                note_id=arguments.get("note_id"),
                search_title=arguments.get("search_title"),
                start_line=arguments.get("start_line", 1),
                line_count=arguments.get("line_count", -1),
                include_metadata=arguments.get("include_metadata", True)
            )
            
            # 处理结果
            if "error" in result:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"错误: {result['error']}"
                    }],
                    isError=True
                )
            
            # 构建成功响应
            content_text = f"笔记标题: {result.get('title', '无标题')}\n"
            content_text += f"笔记ID: {result.get('note_id', '未知')}\n"
            
            if result.get("content_info"):
                info = result["content_info"]
                content_text += f"内容信息: 第{info['start_line']}-{info['end_line']}行 (共{info['total_lines']}行)\n"
            
            content_text += f"\n内容:\n{result.get('content', '')}"
            
            if result.get("metadata"):
                metadata = result["metadata"]
                content_text += f"\n\n元数据:\n"
                content_text += f"- 创建时间: {metadata.get('created_at', '未知')}\n"
                content_text += f"- 更新时间: {metadata.get('updated_at', '未知')}\n"
                content_text += f"- 是否公开: {metadata.get('is_public', False)}\n"
                if metadata.get("session_ids"):
                    content_text += f"- 关联会话: {', '.join(metadata['session_ids'])}\n"
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": content_text
                }],
                isError=False
            )
            
        except Exception as e:
            app_logger.error(f"读取笔记时发生错误: {str(e)}", exc_info=True)
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"读取笔记时发生错误: {str(e)}"
                }],
                isError=True
            )
    
    async def _edit_note(self, arguments: Dict[str, Any]) -> ToolResult:
        """编辑笔记内容"""
        try:
            # 导入笔记工具
            from backend.services.tools import NoteEditorTool
            from backend.db.session import get_async_session
            
            # 如果没有数据库会话，创建一个
            if not self.db_session:
                async for db in get_async_session():
                    self.db_session = db
                    break
            
            # 创建笔记编辑工具实例
            editor = NoteEditorTool(
                db_session=self.db_session,
                session_id=arguments.get("session_id")
            )
            
            # 执行编辑操作
            result = await editor.edit_note(
                note_id=arguments.get("note_id"),
                search_title=arguments.get("search_title"),
                edit_type=arguments.get("edit_type", "replace"),
                content=arguments.get("content"),
                title=arguments.get("title"),
                start_line=arguments.get("start_line"),
                end_line=arguments.get("end_line"),
                insert_position=arguments.get("insert_position"),
                search_text=arguments.get("search_text"),
                replace_text=arguments.get("replace_text"),
                save_immediately=arguments.get("save_immediately", False)
            )
            
            # 处理结果
            if "error" in result:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": f"错误: {result['error']}"
                    }],
                    isError=True
                )
            
            # 构建成功响应
            content_text = f"笔记编辑{'成功' if result.get('success') else '失败'}\n"
            content_text += f"笔记ID: {result.get('note_id', '未知')}\n"
            content_text += f"标题: {result.get('title', '无标题')}\n"
            content_text += f"编辑类型: {result.get('edit_type', '未知')}\n"
            content_text += f"模式: {'预览' if result.get('is_preview') else '已保存'}\n"
            
            if result.get("changes"):
                changes = result["changes"]
                content_text += f"\n变更统计:\n"
                content_text += f"- 原内容长度: {changes.get('original_length', 0)} 字符\n"
                content_text += f"- 新内容长度: {changes.get('new_length', 0)} 字符\n"
                content_text += f"- 原行数: {changes.get('original_lines', 0)}\n"
                content_text += f"- 新行数: {changes.get('new_lines', 0)}\n"
                content_text += f"- 标题是否改变: {'是' if changes.get('title_changed') else '否'}\n"
            
            if result.get("content_preview"):
                content_text += f"\n内容预览:\n{result['content_preview']}"
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": content_text
                }],
                isError=False
            )
            
        except Exception as e:
            app_logger.error(f"编辑笔记时发生错误: {str(e)}", exc_info=True)
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"编辑笔记时发生错误: {str(e)}"
                }],
                isError=True
            )
    
    async def _create_note(self, arguments: Dict[str, Any]) -> ToolResult:
        """创建新笔记"""
        try:
            # 这里需要实现创建笔记的逻辑
            # 由于原始代码中没有专门的创建笔记工具，我们需要直接操作数据库
            
            if not self.db_session:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": "错误: 数据库连接不可用"
                    }],
                    isError=True
                )
            
            from backend.models.note import Note
            from backend.models.user import User
            from backend.models.chat import Chat
            from backend.models.note_session import NoteSession
            from sqlalchemy import select
            
            # 获取用户信息（通过会话ID）
            session_id = arguments.get("session_id")
            user_id = None
            
            if session_id:
                chat_stmt = select(Chat).where(Chat.public_id == session_id)
                chat_result = await self.db_session.execute(chat_stmt)
                chat = chat_result.scalar_one_or_none()
                if chat:
                    user_id = chat.user_id
            
            if not user_id:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": "错误: 无法确定用户身份"
                    }],
                    isError=True
                )
            
            # 创建新笔记
            new_note = Note(
                title=arguments.get("title", "新笔记"),
                content=arguments.get("content", ""),
                user_id=user_id,
                is_public=False
            )
            
            self.db_session.add(new_note)
            await self.db_session.flush()  # 获取新笔记的ID
            
            # 如果需要关联到会话
            if arguments.get("link_to_session", True) and session_id:
                # 查找会话
                if chat:
                    note_session = NoteSession(
                        note_id=new_note.id,
                        session_id=chat.id,
                        is_primary=True
                    )
                    self.db_session.add(note_session)
            
            await self.db_session.commit()
            await self.db_session.refresh(new_note)
            
            content_text = f"笔记创建成功\n"
            content_text += f"笔记ID: {new_note.public_id}\n"
            content_text += f"标题: {new_note.title}\n"
            content_text += f"内容长度: {len(new_note.content)} 字符\n"
            content_text += f"创建时间: {new_note.created_at.isoformat() if new_note.created_at else '未知'}\n"
            
            if arguments.get("link_to_session", True) and session_id:
                content_text += f"已关联到会话: {session_id}\n"
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": content_text
                }],
                isError=False
            )
            
        except Exception as e:
            app_logger.error(f"创建笔记时发生错误: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"创建笔记时发生错误: {str(e)}"
                }],
                isError=True
            )
    
    async def _list_notes(self, arguments: Dict[str, Any]) -> ToolResult:
        """列出用户笔记"""
        try:
            if not self.db_session:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": "错误: 数据库连接不可用"
                    }],
                    isError=True
                )
            
            from backend.models.note import Note
            from backend.models.chat import Chat
            from sqlalchemy import select, or_, and_, desc, asc
            
            # 获取用户信息
            session_id = arguments.get("session_id")
            user_id = None
            
            if session_id:
                chat_stmt = select(Chat).where(Chat.public_id == session_id)
                chat_result = await self.db_session.execute(chat_stmt)
                chat = chat_result.scalar_one_or_none()
                if chat:
                    user_id = chat.user_id
            
            if not user_id:
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": "错误: 无法确定用户身份"
                    }],
                    isError=True
                )
            
            # 构建查询条件
            query_conditions = [
                Note.user_id == user_id,
                Note.is_deleted == False
            ]
            
            # 搜索条件
            search_query = arguments.get("search_query")
            if search_query:
                search_pattern = f"%{search_query}%"
                query_conditions.append(
                    or_(
                        Note.title.ilike(search_pattern),
                        Note.content.ilike(search_pattern)
                    )
                )
            
            # 构建查询
            stmt = select(Note).where(and_(*query_conditions))
            
            # 排序
            sort_by = arguments.get("sort_by", "updated_at")
            sort_order = arguments.get("sort_order", "desc")
            
            if sort_by == "created_at":
                stmt = stmt.order_by(desc(Note.created_at) if sort_order == "desc" else asc(Note.created_at))
            elif sort_by == "title":
                stmt = stmt.order_by(desc(Note.title) if sort_order == "desc" else asc(Note.title))
            else:  # updated_at
                stmt = stmt.order_by(desc(Note.updated_at) if sort_order == "desc" else asc(Note.updated_at))
            
            # 分页
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)
            stmt = stmt.limit(limit).offset(offset)
            
            # 执行查询
            result = await self.db_session.execute(stmt)
            notes = result.scalars().all()
            
            # 构建响应
            if not notes:
                content_text = "没有找到匹配的笔记。"
            else:
                content_text = f"找到 {len(notes)} 条笔记:\n\n"
                
                for i, note in enumerate(notes, 1):
                    content_text += f"{i}. {note.title}\n"
                    content_text += f"   ID: {note.public_id}\n"
                    content_text += f"   更新时间: {note.updated_at.isoformat() if note.updated_at else '未知'}\n"
                    content_text += f"   内容长度: {len(note.content or '')} 字符\n"
                    
                    # 显示内容摘要
                    content_preview = (note.content or "")[:100]
                    if len(note.content or "") > 100:
                        content_preview += "..."
                    content_text += f"   内容摘要: {content_preview}\n"
                    content_text += "-" * 50 + "\n"
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": content_text
                }],
                isError=False
            )
            
        except Exception as e:
            app_logger.error(f"列出笔记时发生错误: {str(e)}", exc_info=True)
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"列出笔记时发生错误: {str(e)}"
                }],
                isError=True
            )


async def main():
    """主函数 - 运行MCP服务器"""
    server = NoteMCPServer()
    
    try:
        while True:
            # 从stdin读取一行
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                # 解析消息
                data = json.loads(line)
                
                # 检查是否为通知消息（没有id字段）
                if "id" not in data:
                    # 这是一个通知消息，我们可以忽略或记录日志
                    app_logger.debug(f"收到通知消息: {data.get('method', 'unknown')}")
                    continue
                
                # 解析为请求
                request = MCPRequest(**data)
                
                # 处理请求
                response = await server.handle_request(request)
                
                # 发送响应
                response_json = response.model_dump_json()
                print(response_json, flush=True)
                
            except json.JSONDecodeError as e:
                # JSON解析错误
                error_response = create_response(
                    0,  # 无法确定请求ID
                    error=create_error(ErrorCode.PARSE_ERROR, f"JSON解析错误: {str(e)}")
                )
                print(error_response.model_dump_json(), flush=True)
                
            except Exception as e:
                # 其他错误
                app_logger.error(f"处理请求时发生未知错误: {str(e)}", exc_info=True)
                error_response = create_response(
                    0,  # 无法确定请求ID
                    error=create_error(ErrorCode.INTERNAL_ERROR, f"服务器错误: {str(e)}")
                )
                print(error_response.model_dump_json(), flush=True)
                
    except KeyboardInterrupt:
        app_logger.info("接收到中断信号，正在关闭服务器...")
    except Exception as e:
        app_logger.error(f"服务器异常: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main()) 