import apiClient from './api';

// 工具详情接口
export interface ToolDetail {
  name: string;
  display_name: string;
  description: string;
  provider: string;
  provider_info: {
    name: string;
    description: string;
    api_key_required: boolean;
    website: string;
  };
  parameters: Record<string, any>;
  required_params: string[];
  api_key_required: boolean;
}

// 工具配置接口
export interface ToolConfig {
  enabled: boolean;
  name: string;
  api_key: string;
  provider?: string;
}

// 工具级别配置接口
export interface ToolLevelConfig {
  [toolName: string]: ToolConfig;
}

// 提供商级别配置接口
export interface ProviderLevelConfig {
  [providerName: string]: {
    enabled: boolean;
    name: string;
    api_key: string;
  };
}

// 配置验证结果接口
export interface ConfigValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  enabled_tools: string[];
  missing_api_keys: string[];
  config_type: 'tool_level' | 'provider_level' | 'unknown';
}

class ToolsService {
  /**
   * 获取所有可用工具的详细信息
   */
  async getToolsList(): Promise<ToolDetail[]> {
    try {
      const response = await apiClient.get('/tools/list');
      return response.data || [];
    } catch (error) {
      console.error('获取工具列表失败:', error);
      throw error;
    }
  }

  /**
   * 按提供商分组获取工具详情
   */
  async getToolsGroupedByProvider(): Promise<Record<string, ToolDetail[]>> {
    try {
      const response = await apiClient.get('/tools/grouped');
      return response.data || {};
    } catch (error) {
      console.error('获取分组工具列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有工具提供商信息
   */
  async getToolProviders(): Promise<Record<string, any>> {
    try {
      const response = await apiClient.get('/tools/providers');
      return response.data || {};
    } catch (error) {
      console.error('获取工具提供商信息失败:', error);
      throw error;
    }
  }

  /**
   * 验证工具配置
   */
  async validateToolsConfig(toolsConfig: ToolLevelConfig | ProviderLevelConfig): Promise<ConfigValidationResult> {
    try {
      const response = await apiClient.post('/tools/validate', toolsConfig);
      return response.data;
    } catch (error) {
      console.error('验证工具配置失败:', error);
      throw error;
    }
  }

  /**
   * 将提供商级别配置转换为工具级别配置
   */
  async convertProviderConfigToToolConfig(providerConfig: ProviderLevelConfig): Promise<{
    success: boolean;
    tool_config: ToolLevelConfig;
    original_config: ProviderLevelConfig;
  }> {
    try {
      const response = await apiClient.post('/tools/convert', providerConfig);
      return response.data;
    } catch (error) {
      console.error('转换配置格式失败:', error);
      throw error;
    }
  }

  /**
   * 获取默认工具配置
   */
  async getDefaultToolConfig(enabledTools?: string[]): Promise<ToolLevelConfig> {
    try {
      const params = enabledTools ? { enabled_tools: enabledTools.join(',') } : {};
      const response = await apiClient.get('/tools/default-config', { params });
      return response.data || {};
    } catch (error) {
      console.error('获取默认工具配置失败:', error);
      throw error;
    }
  }

  /**
   * 根据使用场景获取推荐工具
   */
  async getToolRecommendations(useCase: string): Promise<string[]> {
    try {
      const response = await apiClient.get('/tools/recommendations', {
        params: { use_case: useCase }
      });
      return response.data || [];
    } catch (error) {
      console.error('获取推荐工具失败:', error);
      throw error;
    }
  }

  /**
   * 搜索工具
   */
  async searchTools(query: string): Promise<ToolDetail[]> {
    try {
      const response = await apiClient.get('/tools/search', {
        params: { query }
      });
      return response.data || [];
    } catch (error) {
      console.error('搜索工具失败:', error);
      throw error;
    }
  }
}

export default new ToolsService(); 