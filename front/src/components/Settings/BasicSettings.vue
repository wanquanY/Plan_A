<template>
  <div class="basic-settings">
    <div class="settings-header">
      <h2>{{ pageTitle }}</h2>
      <p class="settings-description">配置您的AI助手基本信息和行为参数</p>
    </div>

    <div v-if="pageLoading" class="loading-container">
      <LoadingOutlined />
      <span>加载中...</span>
    </div>

    <div v-else class="settings-form">
      <Form
        ref="formRef"
        :model="formState"
        :rules="rules"
        layout="vertical"
        class="agent-form"
      >
        <!-- 基本信息 -->
        <div class="form-section">
          <h3>基本信息</h3>
          
          <Form.Item label="AI助手名称" name="name">
            <Input 
              v-model:value="formState.name" 
              placeholder="请输入AI助手名称"
              size="large"
            />
          </Form.Item>

          <Form.Item label="系统提示词" name="system_prompt">
            <Input.TextArea 
              v-model:value="formState.system_prompt" 
              placeholder="请输入系统提示词，这将决定AI助手的行为和回复风格"
              :rows="4"
              size="large"
            />
          </Form.Item>

          <Form.Item label="模型选择" name="model">
            <Select 
              v-model:value="formState.model" 
              size="large"
              placeholder="选择AI模型"
            >
              <Select.Option value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet</Select.Option>
              <Select.Option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</Select.Option>
              <Select.Option value="claude-3-haiku-20240307">Claude 3 Haiku</Select.Option>
            </Select>
          </Form.Item>
        </div>

        <!-- 高级设置 -->
        <div class="form-section">
          <h3>
            高级设置 
            <Tooltip title="这些设置会影响AI的回复风格和行为">
              <QuestionCircleOutlined class="help-icon" />
            </Tooltip>
          </h3>
          
          <Form.Item label="最大记忆轮数" name="max_memory">
            <div class="slider-container">
              <Slider 
                v-model:value="formState.max_memory" 
                :min="1" 
                :max="200" 
                :step="1"
                :tooltip-formatter="(value) => `${value} 轮`"
              />
              <div class="slider-value">{{ formState.max_memory }}</div>
            </div>
            <div class="slider-description">控制AI助手能记住的对话轮数</div>
          </Form.Item>
          
          <Form.Item label="Temperature" name="temperature">
            <div class="slider-container">
              <Slider 
                v-model:value="formState.model_settings.temperature" 
                :min="0" 
                :max="2" 
                :step="0.1"
                :tooltip-formatter="(value) => `${value}`"
              />
              <div class="slider-value">{{ formState.model_settings.temperature?.toFixed(1) || '0.7' }}</div>
            </div>
            <div class="slider-description">控制回复的随机性，值越高越有创意</div>
          </Form.Item>
          
          <Form.Item label="Max Tokens" name="max_tokens">
            <div class="slider-container">
              <Slider 
                v-model:value="formState.model_settings.max_tokens" 
                :min="500" 
                :max="32000" 
                :step="100"
                :tooltip-formatter="(value) => `${value} tokens`"
              />
              <div class="slider-value">{{ formState.model_settings.max_tokens || '6400' }}</div>
            </div>
            <div class="slider-description">控制单次回复的最大长度</div>
          </Form.Item>
        </div>

        <!-- 工具配置 -->
        <div class="form-section">
          <div class="tools-header">
            <h3>
              <ToolOutlined />
              工具能力
            </h3>
            <div class="tools-summary">
              <Tag color="blue">已启用 {{ enabledToolsCount }} 个工具</Tag>
            </div>
          </div>
          
          <div v-if="toolsLoading" class="tools-loading">
            <LoadingOutlined />
            <span>加载工具列表中...</span>
          </div>
          
          <div v-else class="tools-content">
            <p class="tools-description">
              为您的AI助手配置外部工具，让它能够搜索网络、处理文件等。
            </p>
            
            <Collapse v-model:activeKey="activeProviders" class="tools-collapse">
              <Collapse.Panel 
                v-for="(tools, providerName) in toolsGrouped" 
                :key="providerName" 
                :header="getProviderHeader(providerName, tools)"
              >
                <div class="provider-tools">
                  <div class="provider-actions">
                    <Button 
                      size="small" 
                      @click="toggleProvider(providerName, true)"
                    >
                      全部启用
                    </Button>
                    <Button 
                      size="small" 
                      @click="toggleProvider(providerName, false)"
                    >
                      全部禁用
                    </Button>
                  </div>
                  
                  <div class="tools-list">
                    <Card 
                      v-for="tool in tools" 
                      :key="tool.name" 
                      class="tool-card"
                      size="small"
                    >
                      <div class="tool-main">
                        <div class="tool-info">
                          <div class="tool-header-row">
                            <Checkbox 
                              :checked="(formState.tools_enabled as ToolLevelConfig)[tool.name]?.enabled"
                              @change="toggleTool(tool.name)"
                            >
                              <span class="tool-name">{{ tool.display_name }}</span>
                            </Checkbox>
                            <Tag 
                              v-if="(formState.tools_enabled as ToolLevelConfig)[tool.name]?.enabled" 
                              color="green" 
                              size="small"
                            >
                              已启用
                            </Tag>
                          </div>
                          <div class="tool-description">
                            {{ tool.description }}
                          </div>
                        </div>
                      </div>
                      
                      <div 
                        v-if="(formState.tools_enabled as ToolLevelConfig)[tool.name]?.enabled" 
                        class="tool-config"
                      >
                        <Divider />
                        <div class="tool-config-content">
                          <div v-if="tool.api_key_required" class="api-key-section">
                            <Form.Item 
                              :label="`${tool.display_name} API密钥`"
                              :name="`tool_${tool.name}_api_key`"
                            >
                              <Input 
                                :value="(formState.tools_enabled as ToolLevelConfig)[tool.name]?.api_key"
                                @input="(e) => updateToolApiKey(tool.name, e.target.value)"
                                placeholder="请输入API密钥"
                                type="password"
                                size="large"
                              />
                              <div class="api-key-hint">
                                前往 
                                <a 
                                  :href="tool.provider_info.website" 
                                  target="_blank"
                                >
                                  {{ tool.provider_info.name }}官网
                                </a> 
                                获取API密钥
                              </div>
                            </Form.Item>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </Collapse.Panel>
            </Collapse>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="form-actions">
          <Button 
            type="primary" 
            size="large"
            :loading="submitLoading"
            @click="submitForm"
          >
            {{ submitButtonText }}
          </Button>
        </div>
      </Form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { 
  Form, Input, Button, Slider, Switch, message, Collapse, 
  Checkbox, Tooltip, Select, Card, Tag, Divider 
} from 'ant-design-vue';
import { 
  LoadingOutlined, QuestionCircleOutlined, ToolOutlined 
} from '@ant-design/icons-vue';
import agentService from '@/services/agent';
import toolsService from '@/services/tools';
import type { ToolConfig, Agent } from '@/services/agent';
import type { ToolDetail, ToolLevelConfig, ProviderLevelConfig } from '@/services/tools';

// 状态管理
const isEditMode = ref(false);
const hasAgent = ref(false);
const currentAgent = ref<Agent | null>(null);
const submitLoading = ref(false);
const pageLoading = ref(true);
const formRef = ref();

// 工具相关状态
const availableTools = ref<ToolDetail[]>([]);
const toolsGrouped = ref<Record<string, ToolDetail[]>>({});
const toolsLoading = ref(false);
const activeProviders = ref<string[]>([]);

// 表单数据
const formState = reactive({
  name: '智能助手',
  system_prompt: '你是一个有用的助手',
  model: 'claude-3-7-sonnet-20250219',
  max_memory: 100,
  model_settings: {
    temperature: 0.7,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    max_tokens: 6400
  },
  tools_enabled: {} as ToolLevelConfig | ProviderLevelConfig,
  is_public: false
});

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入AI助手名称', trigger: 'blur' }
  ],
  system_prompt: [
    { required: true, message: '请输入系统提示词', trigger: 'blur' }
  ]
};

// 计算属性
const pageTitle = computed(() => {
  return hasAgent.value ? '设置我的AI助手' : '创建我的AI助手';
});

const submitButtonText = computed(() => {
  return hasAgent.value ? '保存设置' : '创建助手';
});

const enabledToolsCount = computed(() => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  return Object.values(toolConfig).filter(config => config.enabled).length;
});

// 获取提供商头部信息
const getProviderHeader = (providerName: string, tools: ToolDetail[]) => {
  const enabledCount = tools.filter(tool => 
    (formState.tools_enabled as ToolLevelConfig)[tool.name]?.enabled
  ).length;
  
  return `${providerName} (${enabledCount}/${tools.length} 已启用)`;
};

// 方法实现
const checkUserAgent = async () => {
  try {
    pageLoading.value = true;
    const agent = await agentService.getMyAgent();
    
    if (agent) {
      hasAgent.value = true;
      isEditMode.value = true;
      currentAgent.value = agent;
      await loadAgentData(agent);
    } else {
      hasAgent.value = false;
      isEditMode.value = false;
      currentAgent.value = null;
      initializeDefaultData();
    }
  } catch (error) {
    console.error('检查用户AI助手状态失败:', error);
    hasAgent.value = false;
    isEditMode.value = false;
    initializeDefaultData();
  } finally {
    pageLoading.value = false;
  }
};

const initializeDefaultData = () => {
  formState.system_prompt = '你是一个有用的助手';
  formState.model = 'claude-3-7-sonnet-20250219';
  formState.max_memory = 100;
  formState.model_settings = {
    temperature: 0.7,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    max_tokens: 6400
  };
  
  if (availableTools.value.length > 0) {
    initializeToolsConfig();
  }
};

const loadAgentData = async (agent: Agent) => {
  try {
    formState.system_prompt = agent.system_prompt;
    formState.model = agent.model;
    formState.max_memory = agent.max_memory;
    
    if (agent.model_settings) {
      formState.model_settings = {
        temperature: agent.model_settings.temperature ?? 0.7,
        top_p: agent.model_settings.top_p ?? 1.0,
        frequency_penalty: agent.model_settings.frequency_penalty ?? 0.0,
        presence_penalty: agent.model_settings.presence_penalty ?? 0.0,
        max_tokens: agent.model_settings.max_tokens ?? 6400
      };
    } else {
      formState.model_settings = {
        temperature: 0.7,
        top_p: 1.0,
        frequency_penalty: 0.0,
        presence_penalty: 0.0,
        max_tokens: 6400
      };
    }
    
    if (agent.tools_enabled) {
      formState.tools_enabled = await detectAndConvertConfig(agent.tools_enabled);
    } else {
      initializeToolsConfig();
    }
  } catch (error) {
    console.error('加载AI助手数据失败:', error);
    message.error('加载AI助手数据失败');
  }
};

const loadToolsList = async () => {
  try {
    toolsLoading.value = true;
    const [tools, grouped] = await Promise.all([
      toolsService.getToolsList(),
      toolsService.getToolsGroupedByProvider()
    ]);
    
    availableTools.value = tools;
    toolsGrouped.value = grouped;
    
    if (!hasAgent.value) {
      initializeToolsConfig();
    }
  } catch (error) {
    console.error('加载工具列表失败:', error);
    message.error('加载工具列表失败');
  } finally {
    toolsLoading.value = false;
  }
};

const initializeToolsConfig = () => {
  const toolConfig: ToolLevelConfig = {};
  availableTools.value.forEach(tool => {
    toolConfig[tool.name] = {
      enabled: false,
      name: tool.name,
      api_key: '',
      provider: tool.provider
    };
  });
  formState.tools_enabled = toolConfig;
};

const detectAndConvertConfig = async (config: any) => {
  try {
    const validation = await toolsService.validateToolsConfig(config);
    let mergedConfig: ToolLevelConfig;
    
    if (validation.config_type === 'tool_level') {
      mergedConfig = { ...config };
    } else {
      const converted = await toolsService.convertProviderConfigToToolConfig(config);
      mergedConfig = converted.tool_config;
    }
    
    availableTools.value.forEach(tool => {
      if (!mergedConfig[tool.name]) {
        mergedConfig[tool.name] = {
          enabled: false,
          name: tool.name,
          api_key: '',
          provider: tool.provider
        };
      }
    });
    
    return mergedConfig;
  } catch (error) {
    console.error('配置格式检测失败:', error);
    const defaultConfig = await toolsService.getDefaultToolConfig();
    return defaultConfig;
  }
};

const toggleTool = (toolName: string) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  if (toolConfig[toolName]) {
    toolConfig[toolName].enabled = !toolConfig[toolName].enabled;
  }
};

const updateToolApiKey = (toolName: string, apiKey: string) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  if (toolConfig[toolName]) {
    toolConfig[toolName].api_key = apiKey;
  }
};

const toggleProvider = (providerName: string, enabled: boolean) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  const providerTools = toolsGrouped.value[providerName] || [];
  
  providerTools.forEach(tool => {
    if (toolConfig[tool.name]) {
      toolConfig[tool.name].enabled = enabled;
    }
  });
};

const submitForm = async () => {
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const agentData = {
      name: formState.name,
      system_prompt: formState.system_prompt,
      model: formState.model,
      max_memory: formState.max_memory,
      model_settings: formState.model_settings,
      tools_enabled: formState.tools_enabled,
      is_public: formState.is_public
    };
    
    if (hasAgent.value && currentAgent.value) {
      await agentService.updateMyAgent(agentData);
      message.success('AI助手设置已更新');
    } else {
      await agentService.createMyAgent(agentData);
      message.success('AI助手创建成功');
      hasAgent.value = true;
      isEditMode.value = true;
    }
  } catch (error) {
    console.error('保存失败:', error);
    message.error('保存失败，请重试');
  } finally {
    submitLoading.value = false;
  }
};

// 生命周期
onMounted(async () => {
  await Promise.all([
    checkUserAgent(),
    loadToolsList()
  ]);
});
</script>

<style scoped>
.basic-settings {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.settings-header {
  margin-bottom: 32px;
}

.settings-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.settings-description {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px;
  color: #666;
}

.settings-form {
  max-width: 800px;
}

.form-section {
  margin-bottom: 40px;
  padding: 24px;
  background: #fafafa;
  border-radius: 8px;
}

.form-section h3 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.help-icon {
  color: #999;
  cursor: pointer;
}

.help-icon:hover {
  color: #1890ff;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.slider-container .ant-slider {
  flex: 1;
  margin: 0;
}

.slider-value {
  min-width: 80px;
  text-align: center;
  color: #666;
  font-weight: 500;
  background: #f0f0f0;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid #e8e8e8;
}

.slider-description {
  margin-top: 8px;
  color: #666;
  font-size: 12px;
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tools-summary {
  display: flex;
  gap: 8px;
}

.tools-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: #666;
}

.tools-description {
  margin-bottom: 20px;
  color: #666;
  font-size: 14px;
}

.tools-collapse {
  background: white;
  border-radius: 6px;
}

.provider-tools {
  padding: 16px 0;
}

.provider-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tools-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
}

.tool-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.tool-info {
  flex: 1;
}

.tool-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tool-name {
  font-weight: 500;
  color: #333;
}

.tool-description {
  color: #666;
  font-size: 13px;
  line-height: 1.4;
}

.tool-config-content {
  padding-top: 8px;
}

.api-key-section {
  margin-bottom: 16px;
}

.api-key-hint {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.api-key-hint a {
  color: #1890ff;
  text-decoration: none;
}

.api-key-hint a:hover {
  text-decoration: underline;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 24px;
  border-top: 1px solid #e8e8e8;
  margin-top: 32px;
}
</style> 