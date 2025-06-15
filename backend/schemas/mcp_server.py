"""
MCP服务器配置相关的Pydantic schemas

用于API请求和响应的数据验证和序列化。
"""

from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class MCPServerBase(BaseModel):
    """MCP服务器配置基础schema"""
    name: str = Field(..., description="服务器名称", max_length=100)
    description: Optional[str] = Field(None, description="服务器描述")
    
    # 公开性控制
    is_public: bool = Field(False, description="是否公开分享")
    share_link: Optional[str] = Field(None, description="分享链接", max_length=255)
    
    # 连接配置
    transport_type: str = Field("stdio", description="传输类型: stdio, sse")
    command: Optional[str] = Field(None, description="启动命令", max_length=500)
    args: Optional[List[str]] = Field(default_factory=list, description="命令参数数组")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="环境变量")
    cwd: Optional[str] = Field(None, description="工作目录", max_length=500)
    
    # SSE配置
    url: Optional[str] = Field(None, description="SSE服务器URL", max_length=500)
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP请求头")
    api_key: Optional[str] = Field(None, description="API密钥", max_length=500)
    
    # 状态配置
    enabled: bool = Field(True, description="是否启用")
    auto_start: bool = Field(True, description="是否自动启动")
    
    # 连接配置
    timeout: int = Field(30, description="连接超时时间(秒)", ge=1, le=300)
    retry_attempts: int = Field(3, description="重试次数", ge=0, le=10)
    retry_delay: int = Field(1, description="重试延迟(秒)", ge=0, le=60)
    
    # 扩展配置
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外配置信息")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    
    @validator('transport_type')
    def validate_transport_type(cls, v):
        if v not in ['stdio', 'sse']:
            raise ValueError('transport_type must be either "stdio" or "sse"')
        return v
    
    @validator('command')
    def validate_command_for_stdio(cls, v, values):
        if values.get('transport_type') == 'stdio' and not v:
            raise ValueError('command is required for stdio transport type')
        return v
    
    @validator('url')
    def validate_url_for_sse(cls, v, values):
        if values.get('transport_type') == 'sse' and not v:
            raise ValueError('url is required for sse transport type')
        return v


class MCPServerCreate(MCPServerBase):
    """创建MCP服务器配置的schema"""
    pass


class MCPServerUpdate(BaseModel):
    """更新MCP服务器配置的schema"""
    name: Optional[str] = Field(None, description="服务器名称", max_length=100)
    description: Optional[str] = Field(None, description="服务器描述")
    
    # 公开性控制
    is_public: Optional[bool] = Field(None, description="是否公开分享")
    share_link: Optional[str] = Field(None, description="分享链接", max_length=255)
    
    # 连接配置
    transport_type: Optional[str] = Field(None, description="传输类型: stdio, sse")
    command: Optional[str] = Field(None, description="启动命令", max_length=500)
    args: Optional[List[str]] = Field(None, description="命令参数数组")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量")
    cwd: Optional[str] = Field(None, description="工作目录", max_length=500)
    
    # SSE配置
    url: Optional[str] = Field(None, description="SSE服务器URL", max_length=500)
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP请求头")
    api_key: Optional[str] = Field(None, description="API密钥", max_length=500)
    
    # 状态配置
    enabled: Optional[bool] = Field(None, description="是否启用")
    auto_start: Optional[bool] = Field(None, description="是否自动启动")
    
    # 连接配置
    timeout: Optional[int] = Field(None, description="连接超时时间(秒)", ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, description="重试次数", ge=0, le=10)
    retry_delay: Optional[int] = Field(None, description="重试延迟(秒)", ge=0, le=60)
    
    # 扩展配置
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置信息")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    
    @validator('transport_type')
    def validate_transport_type(cls, v):
        if v is not None and v not in ['stdio', 'sse']:
            raise ValueError('transport_type must be either "stdio" or "sse"')
        return v


class MCPServerResponse(MCPServerBase):
    """MCP服务器配置响应schema"""
    id: int = Field(..., description="数据库ID")
    public_id: str = Field(..., description="公开ID")
    user_id: int = Field(..., description="所属用户ID")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 软删除
    is_deleted: bool = Field(..., description="是否已删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    
    class Config:
        from_attributes = True


class MCPServerPublicResponse(MCPServerBase):
    """MCP服务器配置公开响应schema - 只返回public_id作为id"""
    id: str = Field(..., description="公开ID")
    user_id: int = Field(..., description="所属用户ID")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 软删除
    is_deleted: bool = Field(..., description="是否已删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @classmethod
    def from_orm_model(cls, mcp_server):
        """从ORM模型创建响应对象，将public_id映射为id"""
        # 构建基础数据字典
        data = {
            'id': mcp_server.public_id,  # 使用public_id作为id
            'user_id': mcp_server.user_id,
            'name': mcp_server.name,
            'description': mcp_server.description,
            'is_public': mcp_server.is_public,
            'share_link': mcp_server.share_link,
            'transport_type': mcp_server.transport_type,
            'command': mcp_server.command,
            'args': mcp_server.args or [],
            'env': mcp_server.env or {},
            'cwd': mcp_server.cwd,
            'url': mcp_server.url,
            'headers': mcp_server.headers or {},
            'enabled': mcp_server.enabled,
            'auto_start': mcp_server.auto_start,
            'timeout': mcp_server.timeout,
            'retry_attempts': mcp_server.retry_attempts,
            'retry_delay': mcp_server.retry_delay,
            'config': mcp_server.config or {},
            'tags': mcp_server.tags or [],
            'created_at': mcp_server.created_at,
            'updated_at': mcp_server.updated_at,
            'is_deleted': mcp_server.is_deleted,
            'deleted_at': mcp_server.deleted_at,
        }
        return cls(**data)


class MCPServerListResponse(BaseModel):
    """MCP服务器配置列表响应schema"""
    servers: List[MCPServerPublicResponse] = Field(..., description="服务器列表")
    total: int = Field(..., description="总数量")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")


class MCPServerConfigImport(BaseModel):
    """MCP服务器配置导入schema"""
    servers: Dict[str, Dict[str, Any]] = Field(..., description="服务器配置字典")
    overwrite: bool = Field(False, description="是否覆盖现有配置")


class MCPServerConfigExport(BaseModel):
    """MCP服务器配置导出schema"""
    servers: Dict[str, Dict[str, Any]] = Field(..., description="服务器配置字典")
    export_time: datetime = Field(..., description="导出时间")
    user_id: int = Field(..., description="导出用户ID")


class MCPServerImportResult(BaseModel):
    """MCP服务器配置导入结果schema"""
    created: List[str] = Field(..., description="新创建的服务器名称列表")
    updated: List[str] = Field(..., description="更新的服务器名称列表")
    skipped: List[str] = Field(..., description="跳过的服务器名称列表")
    errors: Dict[str, str] = Field(..., description="错误信息字典")


class MCPServerSearchParams(BaseModel):
    """MCP服务器搜索参数schema"""
    name: Optional[str] = Field(None, description="服务器名称（模糊搜索）")
    transport_type: Optional[str] = Field(None, description="传输类型")
    enabled: Optional[bool] = Field(None, description="是否启用")
    is_public: Optional[bool] = Field(None, description="是否公开")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    skip: int = Field(0, description="跳过数量", ge=0)
    limit: int = Field(100, description="限制数量", ge=1, le=1000)


class MCPServerStatistics(BaseModel):
    """MCP服务器统计信息schema"""
    total: int = Field(..., description="总服务器数量")
    enabled: int = Field(..., description="启用的服务器数量")
    disabled: int = Field(..., description="禁用的服务器数量")
    stdio_count: int = Field(..., description="stdio类型服务器数量")
    sse_count: int = Field(..., description="sse类型服务器数量")
    public_count: int = Field(..., description="公开的服务器数量")
    private_count: int = Field(..., description="私有的服务器数量")
    connected: int = Field(..., description="当前连接的服务器数量")
    runtime_servers: int = Field(..., description="运行时服务器数量")


class MCPServerToggleResponse(BaseModel):
    """MCP服务器状态切换响应schema"""
    id: str = Field(..., description="服务器公开ID")
    action: str = Field(..., description="执行的操作: enabled/disabled")
    message: str = Field(..., description="操作结果消息")


class MCPServerStatus(BaseModel):
    """MCP服务器状态schema"""
    name: str
    enabled: bool
    connected: bool
    initialized: bool
    last_error: Optional[str] = None
    connection_time: Optional[datetime] = None
    tools_count: int = 0
    resources_count: int = 0
    prompts_count: int = 0


class MCPServerInDB(MCPServerBase):
    """数据库中的MCP服务器schema"""
    id: int
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPServerListResponse(BaseModel):
    """MCP服务器列表响应schema"""
    servers: List[MCPServerResponse]
    total: int
    enabled_count: int
    connected_count: int


class MCPServerConfigImport(BaseModel):
    """MCP服务器配置导入schema"""
    servers: Dict[str, Dict[str, Any]] = Field(..., description="服务器配置字典")
    overwrite: bool = Field(False, description="是否覆盖已存在的服务器")
    
    @validator('servers')
    def validate_servers_config(cls, v):
        """验证服务器配置格式"""
        if not v:
            raise ValueError('至少需要提供一个服务器配置')
        
        for name, config in v.items():
            if not isinstance(config, dict):
                raise ValueError(f'服务器 {name} 的配置必须是字典格式')
            
            transport_type = config.get('type', 'stdio')
            if transport_type not in ['stdio', 'sse']:
                raise ValueError(f'服务器 {name} 的传输类型必须是 stdio 或 sse')
            
            if transport_type == 'stdio' and not config.get('command'):
                raise ValueError(f'stdio服务器 {name} 必须提供 command')
            
            if transport_type == 'sse' and not config.get('url'):
                raise ValueError(f'sse服务器 {name} 必须提供 url')
        
        return v


class MCPServerConfigExport(BaseModel):
    """MCP服务器配置导出schema"""
    servers: Dict[str, Dict[str, Any]]
    export_time: datetime
    total_count: int


class MCPServerCreateResponse(BaseModel):
    """MCP服务器创建响应schema"""
    id: str = Field(..., description="服务器公开ID")
    name: str = Field(..., description="服务器名称")
    message: str = Field(..., description="创建结果消息")


class MCPServerDeleteResponse(BaseModel):
    """MCP服务器删除响应schema"""
    id: str = Field(..., description="服务器公开ID")
    message: str = Field(..., description="删除结果消息") 