import apiClient from './api';

export interface AgentModelSettings {
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  max_tokens: number;
}

export interface Agent {
  id: number;
  user_id: number;
  name: string;
  avatar_url: string;
  system_prompt: string;
  model: string;
  max_memory: number;
  model_settings: AgentModelSettings;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
  errors: any;
  timestamp: string;
  request_id: string;
}

// 获取用户能看到的所有Agent（自己的+所有公开的）
const getAllAgents = async (skip = 0, limit = 100): Promise<Agent[]> => {
  try {
    console.log(`发起getAllAgents请求`);
    // 不传入is_public，获取用户能看到的所有agents（包括自己的和所有公开的）
    const response = await apiClient.get<ApiResponse<Agent[]>>('/agent/agents', {
      params: { skip, limit }
    });
    console.log(`getAllAgents请求成功，数据项: ${response.data.data.length}`);
    return response.data.data;
  } catch (error) {
    console.error('获取所有Agent列表失败:', error);
    return [];
  }
};

// 获取所有公开的agent列表
const getPublicAgents = async (skip = 0, limit = 100): Promise<Agent[]> => {
  try {
    const response = await apiClient.get<ApiResponse<Agent[]>>(`/agent/agents`, {
      params: { is_public: true, skip, limit }
    });
    return response.data.data;
  } catch (error) {
    console.error('获取公开Agent列表失败:', error);
    return [];
  }
};

// 获取用户自己的所有agent列表（包括公开和私有的）
const getUserAgents = async (skip = 0, limit = 100): Promise<Agent[]> => {
  try {
    const response = await apiClient.get<ApiResponse<Agent[]>>(`/agent/agents`, {
      params: { is_public: false, skip, limit }
    });
    return response.data.data;
  } catch (error) {
    console.error('获取用户Agent列表失败:', error);
    return [];
  }
};

// 获取Agent详情
const getAgentDetail = async (agentId: number): Promise<Agent | null> => {
  try {
    const response = await apiClient.get<ApiResponse<Agent>>(`/agent/agents/${agentId}`);
    return response.data.data;
  } catch (error) {
    console.error(`获取Agent(ID:${agentId})详情失败:`, error);
    return null;
  }
};

// 创建Agent
const createAgent = async (agentData: Omit<Agent, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<Agent | null> => {
  try {
    const response = await apiClient.post<ApiResponse<Agent>>('/agent/agents', agentData);
    return response.data.data;
  } catch (error) {
    console.error('创建Agent失败:', error);
    return null;
  }
};

// 更新Agent
const updateAgent = async (agentId: number, agentData: Partial<Agent>): Promise<Agent | null> => {
  try {
    const response = await apiClient.put<ApiResponse<Agent>>(`/agent/agents/${agentId}`, agentData);
    return response.data.data;
  } catch (error) {
    console.error(`更新Agent(ID:${agentId})失败:`, error);
    return null;
  }
};

// 删除Agent
const deleteAgent = async (agentId: number): Promise<boolean> => {
  try {
    const response = await apiClient.delete<ApiResponse<{success: boolean}>>(`/agent/agents/${agentId}`);
    return response.data.data.success;
  } catch (error) {
    console.error(`删除Agent(ID:${agentId})失败:`, error);
    return false;
  }
};

// 获取可用模型列表
const getAvailableModels = async (): Promise<string[]> => {
  try {
    const response = await apiClient.get<ApiResponse<string[]>>('/agent/models');
    return response.data.data;
  } catch (error) {
    console.error('获取可用模型列表失败:', error);
    return [];
  }
};

export default {
  getAllAgents,
  getPublicAgents,
  getUserAgents,
  getAgentDetail,
  createAgent,
  updateAgent,
  deleteAgent,
  getAvailableModels
}; 