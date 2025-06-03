<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { Form, Input, Button, Slider, Switch, message, Collapse, Checkbox, Tooltip, Select, Card, Tag, Divider } from 'ant-design-vue';
import { PlusOutlined, LoadingOutlined, QuestionCircleOutlined, ArrowLeftOutlined, ToolOutlined, LinkOutlined } from '@ant-design/icons-vue';
import { useRouter, useRoute } from 'vue-router';
import agentService from '@/services/agent';
import toolsService from '@/services/tools';
import type { ToolConfig, Agent } from '@/services/agent';
import type { ToolDetail, ToolLevelConfig, ProviderLevelConfig } from '@/services/tools';

const router = useRouter();
const route = useRoute();
const isEditMode = ref(false);
const agentId = ref<number | null>(null);
const submitLoading = ref(false);

// 表单引用
const formRef = ref();

// 工具相关状态
const availableTools = ref<ToolDetail[]>([]);
const toolsGrouped = ref<Record<string, ToolDetail[]>>({});
const toolsLoading = ref(false);
const configMode = ref<'provider' | 'tool'>('tool');
const activeProviders = ref<string[]>([]);

// 表单数据
const formState = reactive({
  system_prompt: '你是一个有用的助手',
  model: 'claude-3-7-sonnet-20250219',
  max_memory: 100,
  model_settings: {
    temperature: 0.7,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
    max_tokens: 6400
  },
  tools_enabled: {} as ToolLevelConfig | ProviderLevelConfig
});

// 表单验证规则
const rules = {
  system_prompt: [
    { required: true, message: '请输入系统提示词', trigger: 'blur' }
  ]
};

// 计算属性：获取启用的工具数量
const enabledToolsCount = computed(() => {
  if (configMode.value === 'tool') {
    const toolConfig = formState.tools_enabled as ToolLevelConfig;
    return Object.values(toolConfig).filter(config => config.enabled).length;
  } else {
    const providerConfig = formState.tools_enabled as ProviderLevelConfig;
    return Object.values(providerConfig).filter(config => config.enabled).length;
  }
});

// 加载工具列表
const loadToolsList = async () => {
  try {
    toolsLoading.value = true;
    const [tools, grouped] = await Promise.all([
      toolsService.getToolsList(),
      toolsService.getToolsGroupedByProvider()
    ]);
    
    console.log('loaded tools:', tools);
    console.log('loaded grouped tools:', grouped);
    
    availableTools.value = tools;
    toolsGrouped.value = grouped;
    
    // 折叠框默认关闭，不自动展开
    // activeProviders.value = Object.keys(grouped);
    
    // 如果是新建模式，初始化工具配置
    if (!isEditMode.value) {
      initializeToolsConfig();
    }
  } catch (error) {
    console.error('加载工具列表失败:', error);
    message.error('加载工具列表失败');
  } finally {
    toolsLoading.value = false;
  }
};

// 初始化工具配置
const initializeToolsConfig = () => {
  console.log('initializeToolsConfig called');
  console.log('availableTools:', availableTools.value);
  
  const toolConfig: ToolLevelConfig = {};
  availableTools.value.forEach(tool => {
    console.log('initializing tool:', tool.name, 'provider:', tool.provider);
    toolConfig[tool.name] = {
      enabled: false,
      name: tool.name,
      api_key: '',
      provider: tool.provider
    };
  });
  
  console.log('initialized toolConfig:', toolConfig);
  formState.tools_enabled = toolConfig;
};

// 检测配置格式并转换
const detectAndConvertConfig = async (config: any) => {
  try {
    console.log('detectAndConvertConfig called with:', config);
    
    // 验证配置格式
    const validation = await toolsService.validateToolsConfig(config);
    console.log('validation result:', validation);
    
    let finalConfig: any = {};
    
    if (validation.config_type === 'provider_level') {
      // 如果是提供商级别配置，转换为工具级别配置
      const converted = await toolsService.convertProviderConfigToToolConfig(config);
      console.log('converted to tool config:', converted.tool_config);
      finalConfig = converted.tool_config;
    } else if (validation.config_type === 'tool_level') {
      // 如果已经是工具级别配置，直接使用
      console.log('already tool level config');
      finalConfig = config;
    } else {
      // 未知格式，使用默认配置
      console.log('unknown format, getting default config');
      const defaultConfig = await toolsService.getDefaultToolConfig();
      console.log('default config:', defaultConfig);
      finalConfig = defaultConfig;
    }
    
    // 确保所有当前可用的工具都在配置中
    const mergedConfig = { ...finalConfig };
    availableTools.value.forEach(tool => {
      if (!mergedConfig[tool.name]) {
        console.log('adding missing tool to config:', tool.name);
        mergedConfig[tool.name] = {
          enabled: false,
          name: tool.name,
          api_key: '',
          provider: tool.provider
        };
      }
    });
    
    console.log('final merged config:', mergedConfig);
    return mergedConfig;
    
  } catch (error) {
    console.error('配置格式检测失败:', error);
    // 出错时使用默认配置
    console.log('error occurred, getting default config');
    const defaultConfig = await toolsService.getDefaultToolConfig();
    console.log('default config on error:', defaultConfig);
    return defaultConfig;
  }
};

// 加载Agent详情
const loadAgentDetails = async (id: number) => {
  try {
    const agent = await agentService.getAgentDetail(id);
    if (agent) {
      formState.system_prompt = agent.system_prompt;
      formState.model = agent.model;
      formState.max_memory = agent.max_memory;
      
      if (agent.model_settings) {
        formState.model_settings = {
          temperature: agent.model_settings.temperature,
          top_p: agent.model_settings.top_p,
          frequency_penalty: agent.model_settings.frequency_penalty,
          presence_penalty: agent.model_settings.presence_penalty,
          max_tokens: agent.model_settings.max_tokens
        };
      }
      
      if (agent.tools_enabled) {
        formState.tools_enabled = await detectAndConvertConfig(agent.tools_enabled);
      } else {
        initializeToolsConfig();
      }
      
      agentId.value = agent.id;
      isEditMode.value = true;
    } else {
      message.error('获取Agent详情失败');
      router.push('/');
    }
  } catch (error) {
    console.error('加载Agent详情失败:', error);
    message.error('加载Agent详情失败');
    router.push('/');
  }
};

// 切换工具启用状态
const toggleTool = (toolName: string) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  if (toolConfig[toolName]) {
    toolConfig[toolName].enabled = !toolConfig[toolName].enabled;
  }
};

// 更新工具API密钥
const updateToolApiKey = (toolName: string, apiKey: string) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  if (toolConfig[toolName]) {
    toolConfig[toolName].api_key = apiKey;
  }
};

// 批量启用提供商的所有工具
const toggleProvider = (providerName: string, enabled: boolean) => {
  console.log('toggleProvider called:', { providerName, enabled });
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  const providerTools = toolsGrouped.value[providerName] || [];
  
  console.log('providerTools:', providerTools);
  console.log('current toolConfig:', toolConfig);
  
  providerTools.forEach(tool => {
    console.log('processing tool:', tool.name, 'exists in config:', !!toolConfig[tool.name]);
    if (toolConfig[tool.name]) {
      toolConfig[tool.name].enabled = enabled;
      console.log('updated tool:', tool.name, 'to enabled:', enabled);
    }
  });
  
  console.log('updated toolConfig:', toolConfig);
};

// 获取提供商的启用状态
const getProviderStatus = (providerName: string) => {
  const toolConfig = formState.tools_enabled as ToolLevelConfig;
  const providerTools = toolsGrouped.value[providerName] || [];
  
  if (providerTools.length === 0) return { enabled: false, partial: false };
  
  const enabledCount = providerTools.filter(tool => 
    toolConfig[tool.name]?.enabled
  ).length;
  
  return {
    enabled: enabledCount === providerTools.length,
    partial: enabledCount > 0 && enabledCount < providerTools.length
  };
};

// 提交表单
const submitForm = async (values: any) => {
  submitLoading.value = true;
  try {
    let result;
    if (isEditMode.value && agentId.value) {
      // 编辑已有Agent
      const dataToUpdate = { ...formState };
      result = await agentService.updateAgent(agentId.value, dataToUpdate);
      if (result && result.id) {
        message.success('Agent更新成功');
      } else {
        message.error(result?.message || 'Agent更新失败');
      }
    } else {
      // 这个分支理论上不会进入，因为我们总是编辑 agent 1
      message.error('无效的操作');
      router.push('/');
    }
  } catch (error: any) {
    console.error('更新Agent失败:', error);
    message.error(error.message || '更新Agent失败');
  } finally {
    submitLoading.value = false;
  }
};

const goBackIfApplicable = () => {
  router.push('/');
};

// 可用模型列表
const availableModels = ref([
  'anthropic/claude-sonnet-4',
  'claude-3-7-sonnet-20250219',
  'claude-3-5-sonnet-20240620',
  'claude-3-opus-20240229',
  'gpt-4-1106-preview',
  'gpt-4-turbo',
  'gpt-4-vision-preview',
  'gpt-4',
  'gpt-3.5-turbo'
]);

// 获取可用模型列表
const fetchAvailableModels = async () => {
  try {
    const models = await agentService.getAvailableModels();
    if (models && models.length > 0) {
      availableModels.value = models;
    }
  } catch (error) {
    console.error('获取可用模型列表失败:', error);
  }
};

onMounted(async () => {
  await loadToolsList();
  
  if (route.params.id) {
    const id = Number(route.params.id);
    if (!isNaN(id)) {
      agentId.value = id;
      isEditMode.value = true;
      await loadAgentDetails(id);
    } else {
      message.error('无效的Agent ID');
      router.push('/');
    }
  } else {
    console.log('非编辑模式，但路由中没有ID。当前路由:', route.fullPath);
    router.push('/');
  }
});
</script>

<template>
  <div class="create-agent-page">
    <div class="page-content">
      <Form 
        ref="formRef"
        :model="formState"
        :rules="rules"
        layout="vertical"
        class="create-agent-form"
        @finish="submitForm"
      >
        <div class="form-left">
          <Form.Item label="系统提示词" name="system_prompt">
            <Input.TextArea 
              v-model:value="formState.system_prompt" 
              placeholder="请输入系统提示词" 
              :rows="8"
              :autoSize="{ minRows: 8, maxRows: 15 }"
            />
          </Form.Item>
        </div>
        
        <div class="form-right">
          <Form.Item label="模型" name="model">
            <Select
              v-model:value="formState.model"
              placeholder="请选择模型"
              style="width: 100%"
              :options="availableModels.map(model => ({ label: model, value: model }))"
            />
          </Form.Item>
          
          <div class="advanced-settings">
            <h3>高级设置 <Tooltip title="这些设置会影响AI的回复风格和行为"><QuestionCircleOutlined /></Tooltip></h3>
            
            <Form.Item label="最大记忆轮数" name="max_memory">
              <Slider 
                v-model:value="formState.max_memory" 
                :min="1" 
                :max="200" 
                :step="1"
              />
              <div class="slider-value">{{ formState.max_memory }}</div>
            </Form.Item>
            
            <Form.Item label="Temperature" name="temperature">
              <Slider 
                v-model:value="formState.model_settings.temperature" 
                :min="0" 
                :max="2" 
                :step="0.1"
              />
              <div class="slider-value">{{ formState.model_settings.temperature }}</div>
            </Form.Item>
            
            <Form.Item label="Max Tokens" name="max_tokens">
              <Slider 
                v-model:value="formState.model_settings.max_tokens" 
                :min="500" 
                :max="8000" 
                :step="100"
              />
              <div class="slider-value">{{ formState.model_settings.max_tokens }}</div>
            </Form.Item>
            
            <Form.Item label="工具能力">
              <a-form-item-rest>
              <div class="tools-section">
                <div class="tools-header">
                  <h4>
                    <ToolOutlined />
                    工具配置
                    <Tag v-if="enabledToolsCount > 0" color="blue">
                      已启用 {{ enabledToolsCount }} 个工具
                    </Tag>
                  </h4>
                  <div class="tools-description">
                    为您的Agent配置外部工具，让它能够搜索信息、解析网页等
                  </div>
                </div>
                
                <div v-if="toolsLoading" class="tools-loading">
                  <LoadingOutlined />
                  <span>加载工具列表中...</span>
                </div>
                
                <div v-else class="tools-config">
                  <Collapse v-model:activeKey="activeProviders" class="tools-collapse">
                    <Collapse.Panel 
                      v-for="(tools, providerName) in toolsGrouped" 
                      :key="providerName"
                      class="provider-panel"
                    >
                      <template #header>
                        <div class="provider-header">
                          <div class="provider-info">
                            <span class="provider-name">{{ tools[0]?.provider_info?.name || providerName }}</span>
                            <Tag 
                              :color="getProviderStatus(providerName).enabled ? 'green' : 
                                     getProviderStatus(providerName).partial ? 'orange' : 'default'"
                            >
                              {{ tools.length }} 个工具
                              <span v-if="getProviderStatus(providerName).enabled"> - 全部启用</span>
                              <span v-else-if="getProviderStatus(providerName).partial"> - 部分启用</span>
                            </Tag>
                          </div>
                          <div class="provider-actions" @click.stop>
                            <Button 
                              size="small"
                              :type="getProviderStatus(providerName).enabled ? 'default' : 'primary'"
                              @click="toggleProvider(providerName, !getProviderStatus(providerName).enabled)"
                            >
                              {{ getProviderStatus(providerName).enabled ? '全部禁用' : '全部启用' }}
                            </Button>
                          </div>
                        </div>
                        <div v-if="tools[0]?.provider_info?.description" class="provider-description">
                          {{ tools[0].provider_info.description }}
                          <a 
                            v-if="tools[0]?.provider_info?.website" 
                            :href="tools[0].provider_info.website" 
                            target="_blank"
                            class="provider-link"
                            @click.stop
                          >
                            <LinkOutlined />
                            官网
                          </a>
                        </div>
                      </template>
                      
                      <div class="tools-list">
                        <div 
                          v-for="tool in tools" 
                          :key="tool.name"
                          class="tool-item"
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
                              
                              <div v-if="tool.parameters && Object.keys(tool.parameters).length > 0" class="tool-params">
                                <div class="params-title">支持的参数：</div>
                                <div class="params-list">
                                  <Tag 
                                    v-for="(param, paramName) in tool.parameters" 
                                    :key="paramName"
                                    :color="tool.required_params.includes(paramName) ? 'red' : 'blue'"
                                    size="small"
                                  >
                                    {{ paramName }}
                                    <span v-if="tool.required_params.includes(paramName)">*</span>
                                  </Tag>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Collapse.Panel>
                  </Collapse>
                  
                  <div v-if="Object.keys(toolsGrouped).length === 0" class="no-tools">
                    <div class="no-tools-content">
                      <ToolOutlined />
                      <div>暂无可用工具</div>
                    </div>
                  </div>
                </div>
              </div>
              </a-form-item-rest>
            </Form.Item>
          </div>
        </div>
        
        <div class="form-actions">
          <Button type="primary" html-type="submit" :loading="submitLoading" class="submit-button">
            保存更新
          </Button>
        </div>
      </Form>
    </div>
  </div>
</template>

<style scoped>
.create-agent-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  position: relative;
}

.back-button {
  display: flex;
  align-items: center;
  margin-right: 16px;
  font-size: 14px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-content {
  background: white;
  border-radius: 12px;
  padding: 32px 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.create-agent-form {
  width: 100%;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0px;
}

.form-left, .form-right {
  width: 100%;
  margin-bottom: 24px;
}

.form-right {
  margin-bottom: 0;
}

.avatar-uploader {
  display: flex;
  justify-content: center;
}

.avatar-preview {
  width: 104px;
  height: 104px;
  overflow: hidden;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-button {
  width: 104px;
  height: 104px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed #d9d9d9;
  border-radius: 50%;
  background: #fafafa;
  cursor: pointer;
}

.advanced-settings {
  margin-top: 16px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.advanced-settings h3 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.slider-value {
  text-align: right;
  color: #666;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 32px;
}

.public-switch {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tools-section {
  margin-top: 16px;
}

.tools-header {
  margin-bottom: 20px;
}

.tools-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tools-description {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.tools-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: #666;
}

.tools-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tools-collapse {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fff;
}

.tools-collapse .ant-collapse-item {
  border-bottom: 1px solid #f0f0f0;
}

.tools-collapse .ant-collapse-item:last-child {
  border-bottom: none;
}

.tools-collapse .ant-collapse-header {
  padding: 16px 20px !important;
  background: #fafafa;
  border-radius: 0;
}

.tools-collapse .ant-collapse-content {
  border-top: 1px solid #f0f0f0;
}

.tools-collapse .ant-collapse-content-box {
  padding: 20px;
}

.provider-panel {
  margin-bottom: 0;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.provider-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.provider-name {
  font-weight: 600;
  font-size: 16px;
  color: #333;
}

.provider-actions {
  margin-left: 16px;
}

.provider-description {
  font-size: 14px;
  color: #666;
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  line-height: 1.5;
}

.provider-link {
  color: #1890ff;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  margin-left: 8px;
}

.provider-link:hover {
  text-decoration: underline;
}

.tools-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.tool-item {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.tool-item:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
  font-size: 15px;
  color: #333;
}

.tool-description {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.tool-config {
  margin-top: 16px;
  background: white;
  border-radius: 6px;
  padding: 16px;
  border: 1px solid #e8e8e8;
}

.tool-config-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.api-key-section {
  margin-bottom: 0;
}

.api-key-hint {
  font-size: 12px;
  color: #666;
  margin-top: 6px;
}

.api-key-hint a {
  color: #1890ff;
  text-decoration: none;
}

.api-key-hint a:hover {
  text-decoration: underline;
}

.tool-params {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.params-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
}

.params-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.no-tools {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 20px;
  color: #999;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #d9d9d9;
}

.no-tools-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.no-tools-content .anticon {
  font-size: 24px;
  color: #ccc;
}

.agent-preview {
  margin-top: 40px;
}

.agent-preview h3 {
  margin-bottom: 16px;
  font-size: 16px;
}

.preview-card {
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 320px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preview-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
}

.preview-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-name {
  font-weight: 600;
  font-size: 16px;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-model {
  font-size: 12px;
  color: #666;
}

.preview-prompt {
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

.preview-badge {
  font-size: 12px;
  padding: 2px 8px;
  background-color: #1890ff;
  color: white;
  border-radius: 10px;
  margin-left: 8px;
}

.preview-id {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .preview-card {
    max-width: 100%;
  }
  
  .create-agent-page {
    padding: 16px;
  }
  
  .page-content {
    padding: 24px 20px;
  }
}
</style> 