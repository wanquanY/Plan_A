<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { Form, Input, Upload, Button, Slider, Switch, message, Collapse, Checkbox, Tooltip } from 'ant-design-vue';
import { PlusOutlined, LoadingOutlined, QuestionCircleOutlined } from '@ant-design/icons-vue';
import type { UploadChangeParam } from 'ant-design-vue';
import agentService from '@/services/agent';
import type { ToolConfig } from '@/services/agent';

const props = defineProps({
  editMode: {
    type: Boolean,
    default: false
  },
  agentData: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['success', 'cancel']);

// 表单引用
const formRef = ref();

// 头像上传相关
const uploadLoading = ref(false);
const imageUrl = ref('');
const fileList = ref([]);

// 表单数据
const formState = reactive({
  name: '',
  avatar_url: '',
  system_prompt: '你是一个有用的助手',
  model: 'claude-3-7-sonnet-20250219',
  max_memory: 100,
  is_public: true,
  model_settings: {
    temperature: 0.7,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
    max_tokens: 6400
  },
  tools_enabled: {
    tavily: {
      enabled: false,
      name: 'tavily',
      api_key: '',
    }
  }
});

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入Agent名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度应在2-50字符之间', trigger: 'blur' }
  ],
  system_prompt: [
    { required: true, message: '请输入系统提示词', trigger: 'blur' }
  ]
};

// 上传前验证
const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/');
  if (!isImage) {
    message.error('只能上传图片文件!');
  }
  const isLt2M = file.size / 1024 / 1024 < 2;
  if (!isLt2M) {
    message.error('图片大小不能超过2MB!');
  }
  return isImage && isLt2M;
};

// 处理上传变化
const handleChange = (info: UploadChangeParam) => {
  if (info.file.status === 'uploading') {
    uploadLoading.value = true;
    return;
  }
  
  if (info.file.status === 'done') {
    uploadLoading.value = false;
    if (info.file.response && info.file.response.success) {
      const fileInfo = info.file.response.file_info;
      imageUrl.value = fileInfo.url;
      formState.avatar_url = fileInfo.url;
      message.success('头像上传成功!');
    } else {
      message.error('上传失败: ' + (info.file.response?.message || '未知错误'));
    }
  } else if (info.file.status === 'error') {
    uploadLoading.value = false;
    message.error('上传失败: ' + info.file.response?.message || '未知错误');
  }
};

// 提交表单
const submitForm = () => {
  formRef.value.validate().then(async () => {
    try {
      let result;
      if (props.editMode && props.agentData.id) {
        result = await agentService.updateAgent(props.agentData.id, formState);
        if (result) {
          message.success('Agent更新成功');
          emit('success');
        } else {
          message.error('Agent更新失败');
        }
      } else {
        result = await agentService.createAgent(formState);
        if (result) {
          message.success('Agent创建成功');
          emit('success');
        } else {
          message.error('Agent创建失败');
        }
      }
    } catch (error) {
      console.error(props.editMode ? '更新Agent失败:' : '创建Agent失败:', error);
      message.error(props.editMode ? '更新Agent失败' : '创建Agent失败');
    }
  }).catch(error => {
    console.log('表单验证失败:', error);
  });
};

// 取消提交
const cancelForm = () => {
  emit('cancel');
};

// 编辑模式下加载现有数据
onMounted(() => {
  if (props.editMode && props.agentData) {
    const agent = props.agentData;
    formState.name = agent.name || '';
    formState.avatar_url = agent.avatar_url || '';
    formState.system_prompt = agent.system_prompt || '你是一个有用的助手';
    formState.model = agent.model || 'claude-3-7-sonnet-20250219';
    formState.max_memory = agent.max_memory || 100;
    formState.is_public = agent.is_public !== undefined ? agent.is_public : true;
    
    if (agent.model_settings) {
      formState.model_settings = {
        temperature: agent.model_settings.temperature || 0.7,
        top_p: agent.model_settings.top_p || 1,
        frequency_penalty: agent.model_settings.frequency_penalty || 0,
        presence_penalty: agent.model_settings.presence_penalty || 0,
        max_tokens: agent.model_settings.max_tokens || 6400
      };
    }
    
    if (agent.tools_enabled) {
      formState.tools_enabled = agent.tools_enabled;
    }
    
    if (agent.avatar_url) {
      imageUrl.value = agent.avatar_url;
    }
  }
});
</script>

<template>
  <Form 
    ref="formRef"
    :model="formState"
    :rules="rules"
    layout="vertical"
  >
    <Form.Item label="名称" name="name">
      <Input v-model:value="formState.name" placeholder="请输入Agent名称" />
    </Form.Item>
    
    <Form.Item label="头像" name="avatar_url">
      <div class="avatar-uploader">
        <Upload
          v-model:file-list="fileList"
          :show-upload-list="false"
          :action="'http://101.42.168.191:18000/api/upload'"
          :before-upload="beforeUpload"
          :headers="{}"
          @change="handleChange"
          list-type="picture-card"
        >
          <div v-if="imageUrl" class="avatar-preview">
            <img :src="imageUrl" alt="avatar" />
          </div>
          <div v-else class="upload-button">
            <div v-if="uploadLoading">
              <LoadingOutlined />
            </div>
            <div v-else>
              <PlusOutlined />
              <div style="margin-top: 8px">上传头像</div>
            </div>
          </div>
        </Upload>
      </div>
    </Form.Item>
    
    <Form.Item label="系统提示词" name="system_prompt">
      <Input.TextArea 
        v-model:value="formState.system_prompt" 
        placeholder="请输入系统提示词" 
        :rows="4" 
      />
    </Form.Item>
    
    <Form.Item label="模型" name="model">
      <Input v-model:value="formState.model" placeholder="请输入模型名称" />
    </Form.Item>
    
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
    
    <Form.Item label="是否公开" name="is_public">
      <Switch v-model:checked="formState.is_public" />
    </Form.Item>
    
    <!-- 工具配置部分 -->
    <Collapse class="tool-settings-collapse">
      <Collapse.Panel key="tools" header="工具配置">
        <div class="tool-section">
          <div class="tool-header">
            <Checkbox v-model:checked="formState.tools_enabled.tavily.enabled">
              启用Tavily搜索工具
            </Checkbox>
            <Tooltip title="Tavily是一个能够进行搜索和网页内容解析的工具，让AI可以获取最新的网络信息">
              <QuestionCircleOutlined class="help-icon" />
            </Tooltip>
          </div>
          
          <div class="tool-config" v-if="formState.tools_enabled.tavily.enabled">
            <Form.Item label="API密钥" name="tavily_api_key">
              <Input 
                v-model:value="formState.tools_enabled.tavily.api_key" 
                placeholder="请输入Tavily API密钥"
                type="password"
              />
              <div class="api-key-hint">前往 <a href="https://tavily.com" target="_blank">Tavily官网</a> 获取API密钥</div>
            </Form.Item>
          </div>
        </div>
      </Collapse.Panel>
    </Collapse>
    
    <div class="form-actions">
      <Button @click="cancelForm">取消</Button>
      <Button type="primary" @click="submitForm">{{ props.editMode ? '更新' : '创建' }}</Button>
    </div>
  </Form>
</template>

<style scoped>
.avatar-uploader {
  display: inline-block;
}

.avatar-preview {
  width: 100px;
  height: 100px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-preview img {
  max-width: 100%;
  max-height: 100%;
}

.upload-button {
  width: 100px;
  height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #fafafa;
  border: 1px dashed #d9d9d9;
  border-radius: 2px;
  cursor: pointer;
}

.upload-button:hover {
  border-color: #007bff;
  color: #007bff;
}

.slider-value {
  text-align: right;
  color: #666;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.tool-settings-collapse {
  margin-bottom: 20px;
}

.tool-section {
  padding: 10px 0;
}

.tool-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.help-icon {
  margin-left: 8px;
  color: #999;
  cursor: pointer;
}

.help-icon:hover {
  color: #1890ff;
}

.tool-config {
  padding-left: 20px;
}

.api-key-hint {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style> 