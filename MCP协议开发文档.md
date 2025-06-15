# MCP (Model Context Protocol) 协议开发文档

## 1. MCP协议概述

### 1.1 什么是MCP协议

Model Context Protocol (MCP) 是由Anthropic在2024年11月25日发布的开源协议，旨在标准化AI应用程序和大语言模型之间的上下文交换方式。MCP被视为AI应用程序的"USB-C接口"，为AI模型提供标准化的方式连接不同的数据源和工具。

### 1.2 核心价值

- **标准化接口**：统一LLM与外部工具的交互方式
- **生态丰富**：提供大量现成的插件和工具
- **平台无关**：不依赖特定AI模型，支持任意支持MCP的模型
- **数据安全**：敏感数据可保留在本地，通过接口控制数据传输
- **简化开发**：降低AI应用开发复杂度，提高集成效率

### 1.3 MCP架构组件

```
+----------+         +----------+         +----------+
|   Host   | <-----> |  Client  | <-----> |  Server  |
+----------+         +----------+         +----------+
```

- **Host**: 宿主应用（如Claude Desktop、Cursor等）
- **Client**: MCP客户端，负责与服务器通信
- **Server**: MCP服务器，提供具体的工具和资源

## 2. MCP核心功能

### 2.1 Resources（资源）
类似文件的数据，可被客户端读取（如API响应、文件内容）

### 2.2 Tools（工具）
可被LLM调用的函数（需用户批准）

### 2.3 Prompts（提示）
预设模板，帮助用户完成特定任务

### 2.4 Sampling（采样）
工具执行前后的回调接口

### 2.5 Roots（根目录）
文件系统根目录管理

### 2.6 Transports（传输层）
支持stdio（标准输入/输出）和SSE（服务器发送事件）两种协议

## 3. 技术架构详解

### 3.1 通信流程

1. **客户端发送查询**：用户提问发送给Claude等LLM
2. **工具选择**：LLM分析可用工具并决定使用哪些
3. **工具执行**：客户端通过MCP服务器执行工具
4. **结果返回**：工具执行结果返回给LLM
5. **生成回答**：LLM基于结果生成自然语言回答
6. **展示结果**：回答展示给用户

### 3.2 消息格式

```json
{
  "version": "mcp-0.5",
  "metadata": {
    "conversation_id": "conv_12345",
    "timestamp": "2025-01-18T10:15:30Z",
    "token_count": {
      "prompt": 350,
      "completion_max": 1000
    }
  },
  "messages": [
    {
      "role": "system",
      "content": "你是一个有用的助手",
      "metadata": {
        "priority": "high",
        "persistent": true
      }
    },
    {
      "role": "user", 
      "content": "查询今天天气",
      "metadata": {
        "timestamp": "2025-01-18T10:15:20Z"
      }
    }
  ]
}
```

## 4. 项目集成设计

### 4.1 当前项目架构分析

基于FreeWrite项目，我们有：
- **后端**：基于FastAPI的异步API服务
- **数据库**：PostgreSQL + SQLAlchemy ORM
- **认证**：JWT认证系统
- **服务层**：模块化的服务架构

### 4.2 MCP集成方案

#### 4.2.1 目录结构设计

```
backend/
├── mcp/                    # MCP模块
│   ├── __init__.py
│   ├── client.py          # MCP客户端封装
│   ├── server.py          # MCP服务器实现
│   ├── tools/             # 工具定义
│   │   ├── __init__.py
│   │   ├── base.py        # 工具基类
│   │   ├── database.py    # 数据库工具
│   │   ├── file.py        # 文件操作工具
│   │   └── api.py         # API调用工具
│   ├── schemas/           # MCP数据模型
│   │   ├── __init__.py
│   │   ├── request.py
│   │   └── response.py
│   └── config.py          # MCP配置
├── services/
│   └── mcp_service.py     # MCP服务层
└── api/
    └── v1/
        └── mcp.py         # MCP API接口
```

#### 4.2.2 核心实现组件

##### A. MCP客户端封装

```python
# backend/mcp/client.py
import asyncio
import json
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from backend.core.config import settings
from backend.utils.logging import app_logger


class MCPClient:
    """MCP客户端封装"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.available_tools = []
        self.server_configs = {}
    
    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]):
        """连接到MCP服务器"""
        try:
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env")
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            await session.initialize()
            
            # 获取工具列表
            response = await session.list_tools()
            tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
            } for tool in response.tools]
            
            self.server_configs[server_name] = {
                "session": session,
                "tools": tools
            }
            self.available_tools.extend(tools)
            
            app_logger.info(f"成功连接到MCP服务器: {server_name}")
            return True
            
        except Exception as e:
            app_logger.error(f"连接MCP服务器失败 {server_name}: {e}")
            return False
    
    async def process_query(self, query: str, context: Optional[Dict] = None) -> str:
        """处理用户查询"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个有用的助手，可以使用各种工具来帮助用户。"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
            
            # 添加上下文信息
            if context:
                messages.insert(1, {
                    "role": "system",
                    "content": f"上下文信息: {json.dumps(context, ensure_ascii=False)}"
                })
            
            # 调用OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=self.available_tools,
                temperature=0.7
            )
            
            # 处理工具调用
            message = response.choices[0].message
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result = await self._execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_call.id
                    })
                
                # 获取最终回答
                final_response = await self.openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.7
                )
                return final_response.choices[0].message.content
            
            return message.content
            
        except Exception as e:
            app_logger.error(f"处理查询失败: {e}")
            raise
    
    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """执行工具调用"""
        for server_name, config in self.server_configs.items():
            for tool in config["tools"]:
                if tool["function"]["name"] == tool_name:
                    session = config["session"]
                    result = await session.call_tool(tool_name, tool_args)
                    return result.content[0].text if result.content else ""
        
        raise ValueError(f"工具 {tool_name} 未找到")
    
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()


# MCP客户端单例
mcp_client = MCPClient()
```

##### B. MCP工具定义

```python
# backend/mcp/tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class MCPToolBase(ABC):
    """MCP工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """输入参数模式"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具"""
        pass


# backend/mcp/tools/database.py
from typing import Dict, Any
from sqlalchemy import text

from backend.db.session import get_db_session
from .base import MCPToolBase


class DatabaseQueryTool(MCPToolBase):
    """数据库查询工具"""
    
    @property
    def name(self) -> str:
        return "database_query"
    
    @property
    def description(self) -> str:
        return "执行数据库查询，获取数据库中的信息"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL查询语句（只支持SELECT查询）"
                },
                "limit": {
                    "type": "integer",
                    "description": "结果数量限制",
                    "default": 100
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, limit: int = 100) -> str:
        """执行数据库查询"""
        try:
            # 安全检查：只允许SELECT查询
            if not query.strip().upper().startswith('SELECT'):
                return "错误：只支持SELECT查询语句"
            
            # 添加LIMIT限制
            if 'LIMIT' not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            async with get_db_session() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                
                if not rows:
                    return "查询无结果"
                
                # 格式化结果
                columns = result.keys()
                results = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)
                
                return f"查询结果：\n{json.dumps(results, ensure_ascii=False, indent=2)}"
                
        except Exception as e:
            return f"查询执行错误：{str(e)}"
```

## 5. 实施计划

### 5.1 阶段一：基础框架搭建（1-2周）
1. 安装MCP相关依赖
2. 创建基础目录结构
3. 实现MCP客户端封装
4. 基础配置管理

### 5.2 阶段二：内置工具开发（2-3周）
1. 数据库查询工具
2. 文件操作工具  
3. API调用工具
4. 系统信息工具

### 5.3 阶段三：外部服务集成（2-3周）
1. 网络搜索服务
2. 天气查询服务
3. 文档处理服务
4. 图像处理服务

### 5.4 阶段四：前端集成与优化（2-3周）
1. 前端MCP界面开发
2. 工具管理界面
3. 查询历史管理
4. 性能优化

## 6. 部署与运维

### 6.1 Docker部署

```dockerfile
# 在现有Dockerfile中添加MCP依赖
RUN pip install "mcp[cli]" httpx anthropic

# 添加MCP服务器脚本
COPY backend/mcp/servers/ /app/mcp/servers/
```

### 6.2 环境变量配置

```env
# MCP相关配置
MCP_ENABLED=true
MCP_DEFAULT_MODEL=deepseek-chat
MCP_TIMEOUT=30

# 外部服务API密钥
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
SEARCH_API_KEY=your_search_key
```

## 7. 安全考虑

### 7.1 权限控制
- 基于用户角色的工具访问控制
- 敏感操作需要额外授权
- 工具执行日志记录

### 7.2 数据安全
- 输入参数验证和清理
- SQL注入防护
- 文件路径限制

### 7.3 资源保护
- 查询频率限制
- 工具执行超时控制
- 资源使用监控

## 8. 测试策略

### 8.1 单元测试
```python
# tests/test_mcp/test_tools/test_database.py
import pytest
from backend.mcp.tools.database import DatabaseQueryTool

@pytest.mark.asyncio
async def test_database_query_tool():
    tool = DatabaseQueryTool()
    result = await tool.execute("SELECT 1 as test")
    assert "test" in result
```

这份文档提供了在FreeWrite项目中集成MCP协议的完整方案，包含了详细的技术实现、架构设计和实施计划。 