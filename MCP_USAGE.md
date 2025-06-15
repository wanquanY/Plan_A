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
- ✅ **内置服务器**: 包含示例数据库查询服务器

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
MCP_DATABASE_ENABLED=true
MCP_FILESYSTEM_ENABLED=false
MCP_WEB_ENABLED=false

# MCP服务器配置 (JSON格式)
MCP_SERVERS='{
  "database": {
    "enabled": true,
    "type": "stdio",
    "command": "python",
    "args": ["-m", "backend.mcp.servers.database_server"],
    "description": "数据库查询服务"
  },
  "filesystem": {
    "enabled": false,
    "type": "stdio",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
    "description": "文件系统访问服务"
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
GET /api/v1/mcp/tools?server_name=database&force_refresh=false
```

#### 调用指定服务器的工具
```http
POST /api/v1/mcp/tools/call
Content-Type: application/json

{
  "server_name": "database",
  "tool_name": "query_notes",
  "arguments": {
    "query": "python",
    "limit": 5
  }
}
```

#### 自动查找并调用工具
```http
POST /api/v1/mcp/tools/call-auto
Content-Type: application/json

{
  "tool_name": "query_notes",
  "arguments": {
    "query": "python",
    "limit": 5
  }
}
```

### 资源操作

#### 获取资源列表
```http
GET /api/v1/mcp/resources?server_name=filesystem
```

#### 读取指定服务器的资源
```http
POST /api/v1/mcp/resources/read
Content-Type: application/json

{
  "server_name": "filesystem",
  "uri": "file:///tmp/example.txt"
}
```

#### 自动查找并读取资源
```http
POST /api/v1/mcp/resources/read-auto
Content-Type: application/json

{
  "uri": "file:///tmp/example.txt"
}
```

### 提示操作

#### 获取提示列表
```http
GET /api/v1/mcp/prompts?server_name=database
```

#### 获取指定服务器的提示
```http
POST /api/v1/mcp/prompts/get
Content-Type: application/json

{
  "server_name": "database",
  "prompt_name": "analyze_data",
  "arguments": {
    "dataset": "user_notes"
  }
}
```

## 内置服务器

### 数据库服务器

项目包含一个示例数据库MCP服务器，提供以下工具：

#### query_notes
查询笔记数据，支持按标题、内容、标签等条件搜索。

**参数:**
- `query` (必需): 搜索关键词
- `limit` (可选): 返回结果数量限制，默认10
- `user_id` (可选): 用户ID，如果提供则只查询该用户的笔记

**示例:**
```json
{
  "query": "python",
  "limit": 5,
  "user_id": 1
}
```

#### get_note_stats
获取笔记统计信息，包括总数、分类统计等。

**参数:**
- `user_id` (可选): 用户ID，如果提供则只统计该用户的笔记

#### query_users
查询用户信息。

**参数:**
- `username` (可选): 用户名
- `email` (可选): 邮箱

## 开发指南

### 添加新的MCP服务器

1. 在`backend/mcp/servers/`目录下创建新的服务器文件
2. 实现MCP协议的消息处理逻辑
3. 在配置中添加服务器信息
4. 重启应用即可自动连接

### 示例代码

#### Python客户端使用示例

```python
from backend.services.mcp_service import mcp_service

# 获取工具列表
tools = await mcp_service.list_tools()

# 调用工具
result = await mcp_service.call_tool_auto("query_notes", {
    "query": "python",
    "limit": 5
})

# 读取资源
content = await mcp_service.read_resource_auto("file:///tmp/data.txt")
```

#### 集成到聊天系统

```python
# 为聊天系统执行MCP工具
result = await mcp_service.execute_mcp_tool_for_chat("query_notes", {
    "query": "python"
})

if result["success"]:
    print(result["content"])
else:
    print(f"Error: {result['error']}")

# 获取可用于聊天的工具列表
available_tools = await mcp_service.get_available_tools_for_chat()
```

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查命令路径是否正确
   - 确认依赖包已安装
   - 查看应用日志获取详细错误信息

2. **工具调用失败**
   - 验证工具名称是否正确
   - 检查参数格式是否符合要求
   - 确认服务器状态正常

3. **性能问题**
   - 调整连接超时时间
   - 检查服务器响应时间
   - 考虑使用缓存减少重复请求

### 日志调试

启用调试日志：

```bash
LOG_LEVEL=DEBUG
CONSOLE_LOG_LEVEL=debug
```

查看MCP相关日志：

```bash
grep "MCP" logs/app.log
```

## 扩展功能

### 计划中的功能

- [ ] WebSocket传输支持
- [ ] 更多内置服务器
- [ ] 图形化管理界面
- [ ] 性能监控和指标
- [ ] 服务器负载均衡
- [ ] 缓存优化

### 贡献指南

欢迎提交Issue和Pull Request来改进MCP功能！

## 相关资源

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP规范](https://spec.modelcontextprotocol.io/)
- [示例MCP服务器](https://github.com/modelcontextprotocol) 