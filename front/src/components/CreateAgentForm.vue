<script setup lang="ts">
import { ref, reactive } from 'vue';
import { Form, Input, Upload, Button, Slider, Switch, message } from 'ant-design-vue';
import { PlusOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import type { UploadChangeParam } from 'ant-design-vue';
import agentService from '@/services/agent';

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
      const result = await agentService.createAgent(formState);
      if (result) {
        message.success('Agent创建成功');
        emit('success');
      } else {
        message.error('Agent创建失败');
      }
    } catch (error) {
      console.error('创建Agent失败:', error);
      message.error('创建Agent失败');
    }
  }).catch(error => {
    console.log('表单验证失败:', error);
  });
};

// 取消提交
const cancelForm = () => {
  emit('cancel');
};
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
    
    <div class="form-actions">
      <Button @click="cancelForm">取消</Button>
      <Button type="primary" @click="submitForm">确认</Button>
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
</style> 