#!/usr/bin/env python3
"""
数据库MCP服务器

一个简单的MCP服务器示例，提供数据库查询工具。
这个服务器可以作为子进程运行，为MCP客户端提供数据库操作能力。
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..schemas.protocol import (
    MCPRequest, MCPResponse, MCPNotification,
    Tool, ToolInputSchema, ToolResult,
    ServerCapabilities, Implementation,
    InitializeResponse,
    create_response, create_error, create_notification,
    RequestMethod, NotificationType, ErrorCode
)
from backend.utils.logging import app_logger


class DatabaseMCPServer:
    """数据库MCP服务器"""
    
    def __init__(self):
        self.name = "database-server"
        self.version = "1.0.0"
        self.initialized = False
        
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
        return create_response(request.id, result=result.model_dump())
    
    async def _handle_list_tools(self, request: MCPRequest) -> MCPResponse:
        """处理获取工具列表请求"""
        tools = [
            Tool(
                name="query_notes",
                description="查询笔记数据，支持按标题、内容、标签等条件搜索",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量限制",
                            "default": 10
                        },
                        "user_id": {
                            "type": "integer",
                            "description": "用户ID，如果提供则只查询该用户的笔记"
                        }
                    },
                    required=["query"]
                )
            ),
            Tool(
                name="get_note_stats",
                description="获取笔记统计信息，包括总数、分类统计等",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "user_id": {
                            "type": "integer",
                            "description": "用户ID，如果提供则只统计该用户的笔记"
                        }
                    }
                )
            ),
            Tool(
                name="query_users",
                description="查询用户信息",
                inputSchema=ToolInputSchema(
                    type="object",
                    properties={
                        "username": {
                            "type": "string",
                            "description": "用户名"
                        },
                        "email": {
                            "type": "string",
                            "description": "邮箱"
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
        
        if tool_name == "query_notes":
            result = await self._query_notes(arguments)
        elif tool_name == "get_note_stats":
            result = await self._get_note_stats(arguments)
        elif tool_name == "query_users":
            result = await self._query_users(arguments)
        else:
            return create_response(
                request.id,
                error=create_error(ErrorCode.METHOD_NOT_FOUND, f"工具未找到: {tool_name}")
            )
        
        return create_response(request.id, result=result.model_dump())
    
    async def _handle_ping(self, request: MCPRequest) -> MCPResponse:
        """处理ping请求"""
        return create_response(request.id, result={})
    
    async def _query_notes(self, arguments: Dict[str, Any]) -> ToolResult:
        """查询笔记（模拟实现）"""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        user_id = arguments.get("user_id")
        
        # 这里是模拟数据，实际应该连接数据库
        mock_notes = [
            {
                "id": 1,
                "title": "Python学习笔记",
                "content": "Python基础语法和高级特性...",
                "tags": ["python", "编程"],
                "created_at": "2024-01-15T10:30:00",
                "user_id": 1
            },
            {
                "id": 2,
                "title": "FastAPI开发指南",
                "content": "FastAPI是一个现代、快速的Web框架...",
                "tags": ["fastapi", "python", "web"],
                "created_at": "2024-01-16T15:45:00",
                "user_id": 1
            },
            {
                "id": 3,
                "title": "数据库设计原则",
                "content": "关系型数据库设计的基本原则和最佳实践...",
                "tags": ["数据库", "设计"],
                "created_at": "2024-01-17T09:20:00",
                "user_id": 2
            }
        ]
        
        # 简单的查询过滤
        filtered_notes = []
        for note in mock_notes:
            if query.lower() in note["title"].lower() or query.lower() in note["content"].lower():
                if user_id is None or note["user_id"] == user_id:
                    filtered_notes.append(note)
        
        # 限制结果数量
        filtered_notes = filtered_notes[:limit]
        
        content_text = f"找到 {len(filtered_notes)} 条匹配的笔记:\n\n"
        for note in filtered_notes:
            content_text += f"标题: {note['title']}\n"
            content_text += f"内容: {note['content'][:100]}...\n"
            content_text += f"标签: {', '.join(note['tags'])}\n"
            content_text += f"创建时间: {note['created_at']}\n"
            content_text += "-" * 50 + "\n"
        
        return ToolResult(
            content=[{
                "type": "text",
                "text": content_text
            }],
            isError=False
        )
    
    async def _get_note_stats(self, arguments: Dict[str, Any]) -> ToolResult:
        """获取笔记统计（模拟实现）"""
        user_id = arguments.get("user_id")
        
        # 模拟统计数据
        stats = {
            "total_notes": 150,
            "notes_this_month": 12,
            "notes_this_week": 3,
            "top_tags": [
                {"tag": "python", "count": 25},
                {"tag": "javascript", "count": 18},
                {"tag": "数据库", "count": 15},
                {"tag": "算法", "count": 12},
                {"tag": "设计模式", "count": 10}
            ],
            "recent_activity": "过去7天内创建了3篇笔记"
        }
        
        if user_id:
            stats["user_id"] = user_id
            stats["total_notes"] = 45
            stats["notes_this_month"] = 5
        
        content_text = f"笔记统计信息:\n\n"
        content_text += f"总笔记数: {stats['total_notes']}\n"
        content_text += f"本月新增: {stats['notes_this_month']}\n"
        content_text += f"本周新增: {stats['notes_this_week']}\n"
        content_text += f"最近活动: {stats['recent_activity']}\n\n"
        content_text += "热门标签:\n"
        for tag_info in stats['top_tags']:
            content_text += f"  - {tag_info['tag']}: {tag_info['count']} 篇\n"
        
        return ToolResult(
            content=[{
                "type": "text",
                "text": content_text
            }],
            isError=False
        )
    
    async def _query_users(self, arguments: Dict[str, Any]) -> ToolResult:
        """查询用户（模拟实现）"""
        username = arguments.get("username")
        email = arguments.get("email")
        
        # 模拟用户数据
        mock_users = [
            {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "created_at": "2024-01-01T00:00:00",
                "note_count": 45
            },
            {
                "id": 2,
                "username": "bob",
                "email": "bob@example.com",
                "created_at": "2024-01-05T00:00:00",
                "note_count": 32
            }
        ]
        
        filtered_users = []
        for user in mock_users:
            if username and username.lower() not in user["username"].lower():
                continue
            if email and email.lower() not in user["email"].lower():
                continue
            filtered_users.append(user)
        
        content_text = f"找到 {len(filtered_users)} 个用户:\n\n"
        for user in filtered_users:
            content_text += f"用户名: {user['username']}\n"
            content_text += f"邮箱: {user['email']}\n"
            content_text += f"笔记数: {user['note_count']}\n"
            content_text += f"注册时间: {user['created_at']}\n"
            content_text += "-" * 30 + "\n"
        
        return ToolResult(
            content=[{
                "type": "text",
                "text": content_text
            }],
            isError=False
        )


async def main():
    """主函数 - 运行MCP服务器"""
    server = DatabaseMCPServer()
    
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
                # 解析请求
                data = json.loads(line)
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
                error_response = create_response(
                    0,  # 无法确定请求ID
                    error=create_error(ErrorCode.INTERNAL_ERROR, f"服务器错误: {str(e)}")
                )
                print(error_response.model_dump_json(), flush=True)
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"服务器异常: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main()) 