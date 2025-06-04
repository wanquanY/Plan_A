import apiClient from './api';

export interface AgentModelSettings {
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  max_tokens: number;
}

export interface ToolConfig {
  enabled: boolean;
  name: string;
  api_key?: string;
  config?: Record<string, any>;
}

export interface Agent {
  id: number;
  user_id: number;
  system_prompt: string;
  model: string;
  max_memory: number;
  model_settings: AgentModelSettings;
  tools_enabled?: Record<string, ToolConfig>;
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

// ===================== 新的API端点 - 用户唯一Agent =====================

// 获取当前用户的AI助手
const getMyAgent = async (): Promise<Agent | null> => {
  try {
    console.log('发起getMyAgent请求');
    const response = await apiClient.get<ApiResponse<Agent>>('/agent/my-agent');
    console.log('getMyAgent请求成功');
    return response.data.data;
  } catch (error: any) {
    if (error.response?.status === 404) {
      console.log('用户还没有AI助手');
      return null;
    }
    console.error('获取用户AI助手失败:', error);
    return null;
  }
};

// 创建或更新当前用户的AI助手
const createOrUpdateMyAgent = async (agentData: Omit<Agent, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<Agent | null> => {
  try {
    console.log('发起createOrUpdateMyAgent请求');
    const response = await apiClient.post<ApiResponse<Agent>>('/agent/my-agent', agentData);
    console.log('createOrUpdateMyAgent请求成功');
    return response.data.data;
  } catch (error) {
    console.error('创建或更新AI助手失败:', error);
    return null;
  }
};

// 更新当前用户的AI助手
const updateMyAgent = async (agentData: Partial<Omit<Agent, 'id' | 'user_id' | 'created_at' | 'updated_at'>>): Promise<Agent | null> => {
  try {
    console.log('发起updateMyAgent请求');
    const response = await apiClient.put<ApiResponse<Agent>>('/agent/my-agent', agentData);
    console.log('updateMyAgent请求成功');
    return response.data.data;
  } catch (error) {
    console.error('更新AI助手失败:', error);
    return null;
  }
};

// 删除当前用户的AI助手
const deleteMyAgent = async (): Promise<boolean> => {
  try {
    console.log('发起deleteMyAgent请求');
    const response = await apiClient.delete<ApiResponse<{deleted_agent_id: number}>>('/agent/my-agent');
    console.log('deleteMyAgent请求成功');
    return true;
  } catch (error) {
    console.error('删除AI助手失败:', error);
    return false;
  }
};

// 获取公开的AI助手列表
const getPublicAgents = async (skip = 0, limit = 100): Promise<Agent[]> => {
  try {
    console.log('发起getPublicAgents请求');
    const response = await apiClient.get<ApiResponse<Agent[]>>('/agent/public-agents', {
      params: { skip, limit }
    });
    console.log(`getPublicAgents请求成功，数据项: ${response.data.data.length}`);
    return response.data.data;
  } catch (error) {
    console.error('获取公开AI助手列表失败:', error);
    return [];
  }
};

// ===================== 旧的API端点（保持向后兼容，但功能受限） =====================

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

// 获取用户自己的所有agent列表（现在只会返回一个agent）
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

// 创建Agent（已弃用，重定向到新接口）
const createAgent = async (agentData: Omit<Agent, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<Agent | null> => {
  console.warn('createAgent已弃用，使用createOrUpdateMyAgent代替');
  return createOrUpdateMyAgent(agentData);
};

// 更新Agent（需要检查权限）
const updateAgent = async (agentId: number, agentData: Partial<Agent>): Promise<Agent | null> => {
  try {
    const response = await apiClient.put<ApiResponse<Agent>>(`/agent/agents/${agentId}`, agentData);
    return response.data.data;
  } catch (error) {
    console.error(`更新Agent(ID:${agentId})失败:`, error);
    return null;
  }
};

// 删除Agent（需要检查权限）
const deleteAgent = async (agentId: number): Promise<boolean> => {
  try {
    const response = await apiClient.delete<ApiResponse<{deleted_agent_id: number}>>(`/agent/agents/${agentId}`);
    return true;
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

// 基于公开Agent创建自己的Agent（从模板复制设置）
const createAgentFromTemplate = async (templateAgentId: number): Promise<Agent | null> => {
  try {
    // 先获取模板Agent的详情
    const templateAgent = await getAgentDetail(templateAgentId);
    if (!templateAgent) {
      console.error(`模板Agent(ID:${templateAgentId})不存在或无法访问`);
      return null;
    }
    
    // 检查当前用户是否已有Agent
    const existingAgent = await getMyAgent();
    if (existingAgent) {
      // 如果已有Agent，询问是否覆盖
      const shouldOverwrite = confirm(`您已有AI助手，是否要用模板覆盖当前设置？`);
      if (!shouldOverwrite) {
        return null;
      }
    }
    
    // 创建新Agent，复制模板Agent的关键设置
    const newAgentData = {
      system_prompt: templateAgent.system_prompt,
      model: templateAgent.model,
      max_memory: templateAgent.max_memory,
      model_settings: templateAgent.model_settings,
      tools_enabled: templateAgent.tools_enabled
    };
    
    // 创建或更新用户的Agent
    const result = await createOrUpdateMyAgent(newAgentData);
    return result;
  } catch (error) {
    console.error(`基于模板创建Agent失败:`, error);
    return null;
  }
};

export default {
  // 新的推荐API
  getMyAgent,
  createOrUpdateMyAgent,
  updateMyAgent,
  deleteMyAgent,
  getPublicAgents,
  
  // 旧的API（保持兼容性）
  getAllAgents,
  getUserAgents,
  getAgentDetail,
  createAgent,
  updateAgent,
  deleteAgent,
  getAvailableModels,
  createAgentFromTemplate
}; 