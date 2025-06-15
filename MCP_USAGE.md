# MCP (Model Context Protocol) 使用指南

## 概述

本项目已集成MCP (Model Context Protocol) 客户端，支持连接和管理多个MCP服务器，为AI应用提供强大的工具和资源访问能力。

## 功能特性

- ✅ **多服务器支持**: 同时连接多个MCP服务器
- ✅ **多种传输协议**: 支持stdio和SSE传输
- ✅ **工具调用**: 调用MCP服务器提供的工具
- ✅ **资源访问**: 读取MCP服务器的资源
- ✅ **提示管理**: 获取和使用MCP提示
- ✅ **自动重连**: 自动处理连接故障和重连
- ✅ **API接口**: 完整的REST API支持
- ✅ **内置服务器**: 包含笔记管理服务器

## 配置说明

### 环境变量

在`.env`文件中添加以下配置：

```bash
# MCP基础配置
MCP_ENABLED=true
MCP_CONNECTION_TIMEOUT=30
MCP_REQUEST_TIMEOUT=60
MCP_RETRY_ATTEMPTS=3
MCP_RETRY_DELAY=1.0

# MCP内置服务器配置
MCP_NOTE_ENABLED=true

# MCP服务器配置 (JSON格式)
MCP_SERVERS='{
  "note": {
    "enabled": true,
    "type": "stdio",
    "command": "python",
    "args": ["-m", "backend.mcp.servers.note_server"],
    "description": "笔记阅读和编辑服务"
  }
}'
```

### 服务器配置格式

每个MCP服务器配置包含以下字段：

- `enabled`: 是否启用该服务器
- `type`: 传输类型 ("stdio" 或 "sse")
- `command`: 启动命令
- `args`: 命令参数数组
- `description`: 服务器描述

## API 接口

### 状态管理

#### 获取MCP服务状态
```http
GET /api/v1/mcp/status
```

#### 健康检查
```http
GET /api/v1/mcp/health
```

#### 获取服务器列表
```http
GET /api/v1/mcp/servers
```

#### 获取指定服务器状态
```http
GET /api/v1/mcp/servers/{server_name}/status
```

#### 重连服务器
```http
POST /api/v1/mcp/servers/{server_name}/reconnect
```

### 服务器管理

#### 动态添加服务器
```http
POST /api/v1/mcp/servers
Content-Type: application/json

{
  "name": "new_server",
  "config": {
    "enabled": true,
    "type": "stdio",
    "command": "python",
    "args": ["-m", "some.mcp.server"],
    "description": "新的MCP服务器"
  }
}
```

#### 移除服务器
```http
DELETE /api/v1/mcp/servers/{server_name}
```

### 工具操作

#### 获取工具列表
```http
GET /api/v1/mcp/tools?server_name=note&force_refresh=false
```

#### 调用指定服务器的工具
```http
POST /api/v1/mcp/tools/call
Content-Type: application/json

{
  "server_name": "note",
  "tool_name": "read_note",
  "arguments": {
    "note_id": "abc123",
    "include_metadata": true
  }
}
```

#### 自动查找并调用工具
```http
POST /api/v1/mcp/tools/call-auto
Content-Type: application/json

{
  "tool_name": "read_note",
  "arguments": {
    "note_id": "abc123",
    "include_metadata": true
  }
}
```

### 资源操作

#### 获取资源列表
```http
GET /api/v1/mcp/resources?server_name=note
```

#### 读取指定服务器的资源
```http
POST /api/v1/mcp/resources/read
Content-Type: application/json

{
  "server_name": "note",
  "uri": "note://abc123"
}
```

#### 自动查找并读取资源
```http
POST /api/v1/mcp/resources/read-auto
Content-Type: application/json

{
  "uri": "note://abc123"
}
```

### 提示操作

#### 获取提示列表
```http
GET /api/v1/mcp/prompts?server_name=note
```

#### 获取指定服务器的提示
```http
POST /api/v1/mcp/prompts/get
Content-Type: application/json

{
  "server_name": "note",
  "prompt_name": "analyze_note",
  "arguments": {
    "note_id": "abc123"
  }
}
```

## 内置服务器

### 笔记服务器

项目包含一个内置的笔记MCP服务器，提供以下工具：

#### read_note
读取笔记内容，支持通过笔记ID或标题搜索笔记，可指定阅读范围和是否包含元数据。

**参数:**
- `note_id` (可选): 要读取的笔记ID
- `search_title` (可选): 通过标题搜索笔记，支持模糊匹配
- `start_line` (可选): 开始阅读的行数，默认1
- `line_count` (可选): 要读取的行数，-1表示读取全部，默认-1
- `include_metadata` (可选): 是否包含笔记元数据，默认true

#### edit_note
编辑笔记内容，支持多种编辑操作：完全替换、追加、前置、插入、替换行、替换文本等。

**参数:**
- `note_id` (可选): 要编辑的笔记ID
- `search_title` (可选): 通过标题搜索要编辑的笔记
- `edit_type` (可选): 编辑类型，默认"replace"
- `content` (可选): 新内容
- `title` (可选): 新标题
- `save_immediately` (可选): 是否立即保存，默认false

#### create_note
创建新笔记，可以指定标题、内容，以及是否关联到当前会话。

**参数:**
- `title` (可选): 笔记标题，默认"新笔记"
- `content` (可选): 笔记内容，默认空
- `link_to_session` (可选): 是否关联到当前会话，默认true

#### list_notes
列出用户的笔记，支持搜索、分页和排序。

**参数:**
- `search` (可选): 搜索关键词
- `limit` (可选): 返回结果数量限制，默认10
- `offset` (可选): 偏移量，默认0
- `sort_by` (可选): 排序字段，默认"updated_at"
- `sort_order` (可选): 排序顺序，默认"desc"

## 使用示例

### Python客户端示例

```python
import asyncio
from backend.services.mcp_service import mcp_service

async def main():
    # 初始化MCP服务
    await mcp_service.initialize()
    
    # 调用笔记工具
    result = await mcp_service.call_tool_auto(
        "read_note",
        {"note_id": "abc123", "include_metadata": True}
    )
    
    print(f"笔记内容: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 聊天集成

MCP工具已集成到聊天系统中，AI助手可以自动调用笔记工具来：

- 读取和搜索笔记
- 编辑和创建笔记
- 分析笔记内容
- 管理笔记结构

## 故障排除

### 常见问题

1. **连接失败**: 检查服务器配置和网络连接
2. **工具调用失败**: 验证参数格式和权限
3. **性能问题**: 调整超时和重试参数

### 日志查看

```bash
# 查看MCP相关日志
tail -f logs/app.log | grep MCP
```

### 调试模式

在环境变量中设置：
```bash
LOG_LEVEL=DEBUG
```

## 扩展开发

### 添加新工具

1. 在笔记服务器中添加新的工具定义
2. 实现工具的处理逻辑
3. 更新工具列表
4. 测试工具功能

### 添加新服务器

1. 创建新的MCP服务器实现
2. 在配置中添加服务器定义
3. 实现必要的协议方法
4. 集成到系统中

更多详细信息请参考 [MCP协议开发文档.md](./MCP协议开发文档.md)。 