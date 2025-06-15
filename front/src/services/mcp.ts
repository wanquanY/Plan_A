import api from './api';

// MCP服务器接口定义
export interface MCPServer {
  id: string;
  name: string;
  description: string;
  transport_type: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  enabled: boolean;
  auto_start?: boolean;
  is_public?: boolean;
  tags?: string[];
  created_at: string;
  updated_at?: string;
  user_id?: number;
  // 运行时状态字段
  connected?: boolean;
  initialized?: boolean;
  tools_count?: number;
  resources_count?: number;
  prompts_count?: number;
  // 工具、资源、提示列表
  tools?: MCPTool[];
  resources?: MCPResource[];
  prompts?: MCPPrompt[];
}

// MCP工具接口定义
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: any;
}

// MCP资源接口定义
export interface MCPResource {
  uri: string;
  name?: string;
  description?: string;
  mimeType?: string;
}

// MCP提示接口定义
export interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: any[];
}

export interface MCPServerCreate {
  name: string;
  description: string;
  transport_type: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  enabled?: boolean;
  tags?: string[];
}

export interface MCPServerUpdate {
  name?: string;
  description?: string;
  transport_type?: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  enabled?: boolean;
  tags?: string[];
}

export interface MCPServerStatus {
  connected: boolean;
  initialized: boolean;
  error?: string;
  tools: any[];
  resources: any[];
  prompts: any[];
}

export interface MCPServerListResponse {
  servers: MCPServer[];
  total: number;
  skip: number;
  limit: number;
}

class MCPService {
  // 获取用户的MCP服务器列表
  async getUserServers(skip = 0, limit = 100): Promise<MCPServerListResponse> {
    const response = await api.get('/mcp/servers', {
      params: { skip, limit }
    });
    return response.data.data;
  }

  // 获取公开的MCP服务器列表
  async getPublicServers(skip = 0, limit = 100): Promise<MCPServerListResponse> {
    const response = await api.get('/mcp/public-servers', {
      params: { skip, limit }
    });
    return response.data.data;
  }

  // 创建MCP服务器
  async createServer(serverData: MCPServerCreate): Promise<MCPServer> {
    const response = await api.post('/mcp/servers', serverData);
    return response.data.data;
  }

  // 获取指定MCP服务器详情
  async getServer(serverId: string): Promise<MCPServer> {
    const response = await api.get(`/mcp/servers/${serverId}`);
    return response.data.data;
  }

  // 更新MCP服务器
  async updateServer(serverId: string, updateData: MCPServerUpdate): Promise<MCPServer> {
    const response = await api.put(`/mcp/servers/${serverId}`, updateData);
    return response.data.data;
  }

  // 删除MCP服务器
  async deleteServer(serverId: string): Promise<void> {
    await api.delete(`/mcp/servers/${serverId}`);
  }

  // 切换MCP服务器启用状态
  async toggleServer(serverId: string): Promise<MCPServer> {
    const response = await api.post(`/mcp/servers/${serverId}/toggle`);
    return response.data.data;
  }

  // 获取MCP服务器状态
  async getServerStatus(serverId: string): Promise<MCPServerStatus> {
    const response = await api.get(`/mcp/servers/${serverId}/status`);
    return response.data.data;
  }

  // 重新连接MCP服务器
  async reconnectServer(serverId: string): Promise<void> {
    await api.post(`/mcp/servers/${serverId}/reconnect`);
  }

  // 获取MCP服务整体状态
  async getMCPStatus(): Promise<any> {
    const response = await api.get('/mcp/status');
    return response.data.data;
  }

  // 健康检查
  async healthCheck(): Promise<any> {
    const response = await api.get('/mcp/health');
    return response.data.data;
  }

  // 获取用户服务器统计信息
  async getUserServersStatistics(): Promise<any> {
    const response = await api.get('/mcp/servers/statistics');
    return response.data.data;
  }

  // 导出用户服务器配置
  async exportUserServers(): Promise<any> {
    const response = await api.get('/mcp/servers/export');
    return response.data.data;
  }

  // 批量导入服务器配置
  async importUserServers(servers: MCPServerCreate[], overwrite = false): Promise<any> {
    const response = await api.post('/mcp/servers/import', {
      servers,
      overwrite
    });
    return response.data.data;
  }
}

export default new MCPService(); 