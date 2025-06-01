<template>
  <div class="unified-input" @dragover.prevent="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop">
    <!-- 图片预览区域 -->
    <div v-if="previewImages.length > 0" class="image-preview-container">
      <div v-for="(image, index) in previewImages" :key="index" class="preview-image-wrapper">
        <img :src="image.preview" :alt="image.file.name" class="preview-image" />
        <button @click="removeImage(index)" class="remove-image-btn">×</button>
      </div>
    </div>

    <!-- 上传进度提示 -->
    <div v-if="uploadingCount > 0" class="upload-progress">
      正在上传 {{ uploadingCount }} 张图片...
    </div>

    <!-- 拖拽覆盖层 -->
    <div v-if="isDragOver" class="drag-overlay">
      <div class="drag-hint">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21,15 16,10 5,21"></polyline>
        </svg>
        <p>释放以上传图片</p>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-container">
      <textarea 
        ref="inputRef"
        class="message-input" 
        :placeholder="placeholder"
        v-model="inputValue"
        @input="autoResize"
        @keydown="handleKeydown"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
        @paste="handlePaste"
        rows="1"
      ></textarea>
    </div>

    <!-- 控制栏 -->
    <div class="controls-bar">
      <!-- 左侧控制 -->
      <div class="left-controls">
        <!-- 模型选择器 -->
        <div class="model-tag" @click.stop="toggleModelSelector" ref="modelTagRef">
          <div class="model-arrow">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
              <polyline :points="showModelSelector ? '18,15 12,9 6,15' : '6,9 12,15 18,9'"></polyline>
            </svg>
          </div>
          <span class="model-label">{{ selectedModel || '选择模型' }}</span>
          
          <!-- 模型下拉菜单 -->
          <div v-if="showModelSelector" class="model-dropdown-unified" :style="dropdownStyle">
            <div class="model-dropdown-list">
              <div
                v-for="model in availableModels"
                :key="model"
                class="model-dropdown-item"
                :class="{ selected: selectedModel === model }"
                @click.stop="selectModel(model)"
              >
                <span class="model-dropdown-name">{{ model }}</span>
              </div>
              <div v-if="loading" class="model-dropdown-loading">
                <div class="loading-spinner"></div>
                加载中...
              </div>
              <div v-if="!loading && availableModels.length === 0" class="model-dropdown-empty">暂无可用模型</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧控制 -->
      <div class="right-controls">
        <button 
          class="control-btn"
          @click="triggerFileUpload"
          title="上传图片"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21,15 16,10 5,21"></polyline>
          </svg>
        </button>
        
        <button 
          class="send-btn" 
          @click="handleSendMessage"
          :disabled="!selectedModel || (!inputValue.trim() && previewImages.length === 0 && !isAgentResponding)"
          :title="isAgentResponding ? '停止响应' : '发送'"
          :class="{ 'stop-btn': isAgentResponding }"
        >
          <!-- 发送图标 -->
          <svg v-if="!isAgentResponding" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
          </svg>
          <!-- 停止图标 -->
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="1"></rect>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 隐藏的文件输入框 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      style="display: none"
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import agentService from '../../services/agent';
import uploadService from '../../services/uploadService';
import { uploadImage } from '../../services/uploadService';

const props = defineProps({
  placeholder: {
    type: String,
    default: '发消息、拖拽图片或复制粘贴图片上传'
  },
  autoFocus: {
    type: Boolean,
    default: true
  },
  // 新增：agent是否正在响应的状态
  isAgentResponding: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['send', 'select-agent', 'upload-file', 'adjust-tone', 'stop-response']);

// 状态变量
const inputRef = ref(null);
const fileInputRef = ref(null);
const modelTagRef = ref(null);
const adjustButtonRef = ref(null);
const inputValue = ref('');
const defaultAgent = ref(null); // 默认使用id为1的agent
const selectedModel = ref(''); // 当前选择的模型
const availableModels = ref([]);
const showModelSelector = ref(false);
const showAdjustMenu = ref(false);
const isComposing = ref(false);
const adjustOptions = ref([
  { key: 'formal', label: '更正式' },
  { key: 'casual', label: '更随意' },
  { key: 'shorter', label: '更简短' },
  { key: 'longer', label: '更详细' }
]);
const loading = ref(false);
const dropdownStyle = ref({});
const adjustDropdownStyle = ref({});

// 图片相关状态
const previewImages = ref([]);
const uploadingCount = ref(0);
const isDragOver = ref(false);

// 加载可用模型列表
const fetchAvailableModels = async () => {
  loading.value = true;
  try {
    const models = await agentService.getAvailableModels();
    availableModels.value = models;
    console.log(`已加载${models.length}个可用模型`);
    
    // 如果还没有选择模型且有可用模型，选择第一个
    if (!selectedModel.value && models.length > 0) {
      selectedModel.value = models[0];
    }
  } catch (error) {
    console.error('加载模型列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 获取默认Agent（优先使用id为1，否则使用第一个可用Agent）
const fetchDefaultAgent = async () => {
  try {
    // 首先尝试获取ID为1的Agent
    let agent = await agentService.getAgentDetail(1);
    
    if (!agent) {
      console.log('未找到ID为1的Agent，尝试获取用户的第一个可用Agent');
      // 如果没有ID为1的Agent，获取用户能看到的所有Agent
      const allAgents = await agentService.getAllAgents();
      if (allAgents && allAgents.length > 0) {
        agent = allAgents[0]; // 使用第一个可用的Agent
        console.log('使用第一个可用Agent作为默认:', agent.name, '模型:', agent.model);
      }
    }
    
    if (agent) {
      defaultAgent.value = agent;
      // 如果还没有选择模型，使用默认agent的模型
      if (!selectedModel.value && agent.model) {
        selectedModel.value = agent.model;
      }
      console.log('默认Agent加载成功:', agent.name, '模型:', agent.model);
      
      // 通知父组件默认agent已选择
      emit('select-agent', agent);
    } else {
      console.warn('没有找到任何可用的Agent，将尝试创建默认Agent');
      await createDefaultAgent();
    }
  } catch (error) {
    console.error('加载默认Agent失败:', error);
    // 尝试创建默认Agent
    await createDefaultAgent();
  }
};

// 创建默认Agent
const createDefaultAgent = async () => {
  try {
    console.log('尝试创建默认Agent');
    
    // 获取可用模型列表
    const models = await agentService.getAvailableModels();
    const defaultModel = models.length > 0 ? models[0] : 'gpt-3.5-turbo';
    
    const defaultAgentData = {
      name: '默认助手',
      avatar_url: 'https://placehold.co/40x40?text=AI',
      system_prompt: '你是一个有用的AI助手，能够帮助用户解答问题和完成各种任务。',
      model: defaultModel,
      max_memory: 50,
      model_settings: {
        temperature: 0.7,
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0,
        max_tokens: 4000
      },
      tools_enabled: {},
      is_public: false
    };
    
    const newAgent = await agentService.createAgent(defaultAgentData);
    if (newAgent) {
      defaultAgent.value = newAgent;
      selectedModel.value = newAgent.model;
      console.log('默认Agent创建成功:', newAgent.name, '模型:', newAgent.model);
      emit('select-agent', newAgent);
    } else {
      console.error('创建默认Agent失败');
      // 提示用户需要手动创建Agent
      message.error('没有可用的AI助手，请先创建一个Agent');
    }
  } catch (error) {
    console.error('创建默认Agent时出错:', error);
    message.error('无法初始化AI助手，请手动创建一个Agent');
  }
};

// 选择模型
const selectModel = (model) => {
  selectedModel.value = model;
  showModelSelector.value = false;
  
  // 创建一个临时的agent对象，包含新选择的模型
  if (defaultAgent.value) {
    const agentWithNewModel = {
      ...defaultAgent.value,
      model: model
    };
    emit('select-agent', agentWithNewModel);
  }
  
  // 聚焦到输入框
  nextTick(() => {
    inputRef.value?.focus();
  });
};

// 触发文件选择
const triggerFileUpload = () => {
  fileInputRef.value?.click();
};

// 处理文件选择
const handleFileSelect = async (event) => {
  const files = Array.from(event.target.files);
  if (files.length === 0) return;

  // 添加到上传队列
  uploadingCount.value += files.length;

  try {
    for (const file of files) {
      // 检查文件类型
      if (!file.type.startsWith('image/')) {
        message.warning(`文件 ${file.name} 不是有效的图片格式`);
        uploadingCount.value--;
        continue;
      }

      // 检查文件大小（限制为5MB）
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        message.warning(`文件 ${file.name} 超过5MB大小限制`);
        uploadingCount.value--;
        continue;
      }

      try {
        // 创建预览URL
        const preview = URL.createObjectURL(file);
        
        // 立即上传图片获取真实URL
        console.log(`开始上传图片: ${file.name}`);
        const uploadedUrl = await uploadImage(file, 'chat-images');
        console.log(`图片上传成功: ${file.name} -> ${uploadedUrl}`);

        // 添加到预览列表，使用真实URL
        previewImages.value.push({
          file,
          preview,  // 用于本地预览
          url: uploadedUrl,  // 用于发送给后端的真实URL
          name: file.name,
          size: file.size
        });

        uploadingCount.value--;
      } catch (uploadError) {
        console.error(`上传图片失败: ${file.name}`, uploadError);
        message.error(`上传图片失败: ${file.name}`);
        uploadingCount.value--;
      }
    }
  } catch (error) {
    console.error('处理图片选择失败:', error);
    message.error('处理图片失败');
    uploadingCount.value = 0;
  }

  // 清空文件输入框
  event.target.value = '';
};

// 移除图片
const removeImage = (index) => {
  const image = previewImages.value[index];
  URL.revokeObjectURL(image.preview);
  previewImages.value.splice(index, 1);
};

// 处理拖拽
const handleDragOver = (event) => {
  event.preventDefault();
  isDragOver.value = true;
};

const handleDragLeave = (event) => {
  // 检查是否真的离开了拖拽区域
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false;
  }
};

const handleDrop = async (event) => {
  event.preventDefault();
  isDragOver.value = false;
  
  const files = Array.from(event.dataTransfer.files).filter(file => 
    file.type.startsWith('image/')
  );
  
  if (files.length === 0) {
    message.warning('请拖拽图片文件');
    return;
  }

  // 模拟文件选择事件
  const mockEvent = {
    target: {
      files: files,
      value: ''
    }
  };
  
  await handleFileSelect(mockEvent);
};

// 处理粘贴
const handlePaste = async (event) => {
  const items = Array.from(event.clipboardData.items);
  const imageItems = items.filter(item => item.type.startsWith('image/'));
  
  if (imageItems.length === 0) return;
  
  event.preventDefault();
  
  const files = imageItems.map(item => item.getAsFile()).filter(Boolean);
  
  if (files.length > 0) {
    const mockEvent = {
      target: {
        files: files,
        value: ''
      }
    };
    
    await handleFileSelect(mockEvent);
  }
};

// 发送消息
const handleSendMessage = () => {
  // 如果agent正在响应，则停止响应
  if (props.isAgentResponding) {
    emit('stop-response');
    return;
  }

  // 否则正常发送消息
  if (!selectedModel.value) {
    message.warning('请先选择模型');
    return;
  }
  if (!defaultAgent.value) {
    message.error('默认Agent未加载完成');
    return;
  }
  if (!inputValue.value.trim() && previewImages.value.length === 0) {
    return;
  }

  // 检查是否还有图片正在上传
  if (uploadingCount.value > 0) {
    message.warning('图片还在上传中，请稍等...');
    return;
  }

  // 创建带有选择模型的agent对象
  const agentWithSelectedModel = {
    ...defaultAgent.value,
    model: selectedModel.value
  };

  // 使用已上传的真实URL
  const imagesForSend = previewImages.value.map(image => ({
    url: image.url,  // 使用上传后的真实URL
    name: image.name || image.file.name,
    size: image.size || image.file.size
  }));

  const messageData = {
    agentId: defaultAgent.value.id,
    content: inputValue.value.trim(),
    images: imagesForSend,  // 使用包含真实URL的图片数据
    agent: agentWithSelectedModel,
    model: selectedModel.value
  };
  
  // 清空输入框和图片
  inputValue.value = ''; 
  previewImages.value = [];
  
  // 重置输入框高度
  nextTick(() => {
    autoResize();
    emit('send', messageData); 
  });
};

// 处理键盘按键事件
const handleKeydown = (event) => {
  // 处理Enter键
  if (event.key === 'Enter') {
    // 如果正在使用输入法组合，不处理Enter键
    if (isComposing.value) {
      return;
    }
    
    // 如果按下Shift+Enter，不阻止默认行为（允许换行）
    if (event.shiftKey) {
      return;
    }
    
    // 如果是单独的Enter键，阻止默认行为并发送消息
    event.preventDefault();
    handleSendMessage();
  }
};

// 处理输入法组合开始
const handleCompositionStart = () => {
  isComposing.value = true;
};

// 处理输入法组合结束
const handleCompositionEnd = () => {
  isComposing.value = false;
};

// 自动调整输入框高度
const autoResize = () => {
  const textarea = inputRef.value;
  if (textarea) {
    // 重置高度以获取正确的scrollHeight
    textarea.style.height = 'auto';
    
    // 计算新的高度，限制在20px到120px之间
    const minHeight = 20;
    const maxHeight = 120;
    const newHeight = Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight));
    
    textarea.style.height = `${newHeight}px`;
    
    // 根据内容高度决定是否显示滚动条
    if (textarea.scrollHeight > maxHeight) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
  }
};

// 暴露方法给父组件
const focus = () => {
  nextTick(() => {
    inputRef.value?.focus();
  });
};

const clearInput = () => {
  inputValue.value = '';
  previewImages.value = [];
  // 重置输入框高度
  nextTick(() => {
    autoResize();
  });
};

defineExpose({
  focus,
  clearInput
});

// 组件挂载时初始化
onMounted(() => {
  // 先加载模型列表
  fetchAvailableModels();
  // 再加载默认Agent
  fetchDefaultAgent();
  
  if (props.autoFocus) {
    nextTick(() => {
      inputRef.value?.focus();
      // 确保初始高度正确
      autoResize();
    });
  }
  
  // 点击外部关闭模型选择器和调整菜单
  const handleClickOutside = (event) => {
    if (showModelSelector.value && !event.target.closest('.model-tag')) {
      showModelSelector.value = false;
    }
    if (showAdjustMenu.value && !event.target.closest('.adjust-button-container')) {
      showAdjustMenu.value = false;
    }
  };
  
  document.addEventListener('mousedown', handleClickOutside);
  
  onUnmounted(() => {
    document.removeEventListener('mousedown', handleClickOutside);
  });
});

// 处理调整选项
const handleAdjust = (adjustType) => {
  console.log(`调整语气为: ${adjustType}`);
  showAdjustMenu.value = false;
  emit('adjust-tone', { tone: adjustType });
};

// 计算下拉菜单位置
const calculateDropdownPosition = () => {
  if (!modelTagRef.value) return;
  
  nextTick(() => {
    const rect = modelTagRef.value.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    const dropdownHeight = 300; // 增加最大高度
    
    // 计算是否有足够的下方空间
    const spaceBelow = windowHeight - rect.bottom;
    const showBelow = spaceBelow >= Math.min(dropdownHeight, 200);
    
    dropdownStyle.value = {
      position: 'fixed',
      left: `${rect.left}px`,
      minWidth: `${Math.max(rect.width, 180)}px`,
      maxHeight: `${dropdownHeight}px`
    };
    
    if (showBelow) {
      // 在下方显示
      dropdownStyle.value.top = `${rect.bottom + 4}px`;
    } else {
      // 在上方显示
      dropdownStyle.value.bottom = `${windowHeight - rect.top + 4}px`;
    }
  });
};

const toggleModelSelector = () => {
  showModelSelector.value = !showModelSelector.value;
  if (showModelSelector.value) {
    nextTick(() => {
      calculateDropdownPosition();
    });
  }
};

const toggleAdjustMenu = () => {
  showAdjustMenu.value = !showAdjustMenu.value;
  if (showAdjustMenu.value) {
    nextTick(() => {
      calculateAdjustDropdownPosition();
    });
  }
};

const calculateAdjustDropdownPosition = () => {
  if (!adjustButtonRef.value) return;
  
  const rect = adjustButtonRef.value.getBoundingClientRect();
  
  adjustDropdownStyle.value = {
    position: 'fixed',
    top: `${rect.top - 8}px`, // 向上偏移8px，显示在按钮上方
    left: `${rect.left}px`,
    transform: 'translateY(-100%)', // 完全显示在按钮上方
    minWidth: `${Math.max(rect.width, 120)}px`
  };
};
</script>

<style scoped>
.unified-input {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.unified-input:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.input-container {
  padding: 12px 12px 0;
}

.message-input {
  width: 100%;
  min-height: 20px;
  max-height: 120px;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  font-family: inherit;
  color: #1f2937;
  background: transparent;
  overflow-y: hidden;
}

.message-input::placeholder {
  color: #9ca3af;
}

.image-preview-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 12px 0;
  max-height: 200px;
  overflow-y: auto;
}

.preview-image-wrapper {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.preview-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  display: block;
}

.remove-image-btn {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  border: 2px solid white;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.remove-image-btn:hover {
  background: #dc2626;
}

.upload-progress {
  padding: 8px 12px;
  color: #6b7280;
  font-size: 12px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(99, 102, 241, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border: 2px dashed #6366f1;
  border-radius: 12px;
}

.drag-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #6366f1;
  font-weight: 500;
}

.drag-hint p {
  margin: 8px 0 0 0;
  font-size: 14px;
}

.controls-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 12px;
  gap: 8px;
}

.left-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.right-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  color: #6b7280;
}

.control-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #6366f1;
  color: white;
}

.send-btn:hover:not(:disabled) {
  background: #5856eb;
}

.send-btn:disabled {
  background: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
}

/* 停止按钮样式 */
.send-btn.stop-btn {
  background: #ef4444;
  color: white;
}

.send-btn.stop-btn:hover:not(:disabled) {
  background: #dc2626;
}

.model-tag {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
  background: #f3f4f6;
  color: #374151;
}

.model-tag:hover {
  background: #e5e7eb;
}

.model-arrow {
  width: 12px;
  height: 12px;
  color: #6b7280;
  transition: transform 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-label {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
  line-height: 1;
}

.model-dropdown-unified {
  position: fixed;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 999999;
  max-height: 300px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
  min-width: 180px;
  width: max-content;
}

.model-dropdown-list {
  padding: 4px;
}

.model-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s ease;
  min-width: 0;
}

.model-dropdown-item:hover {
  background: #f3f4f6;
}

.model-dropdown-item.selected {
  background: #e0e7ff;
  color: #3730a3;
}

.model-dropdown-name {
  font-size: 12px;
  font-weight: 500;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 调整按钮样式 */
.adjust-button-container {
  position: relative;
}

.adjust-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  border-radius: 8px;
  background: #f3f4f6;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.adjust-btn:hover {
  background: #e5e7eb;
}

.adjust-dropdown {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 99999;
  min-width: 120px;
}

.adjust-dropdown-list {
  padding: 4px;
}

.adjust-dropdown-item {
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.adjust-dropdown-item:hover {
  background: #f3f4f6;
}

.adjust-dropdown-name {
  font-size: 12px;
  color: #374151;
}

/* 加载和空状态样式 */
.model-dropdown-loading,
.model-dropdown-empty {
  padding: 12px;
  text-align: center;
  color: #6b7280;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .image-preview-container {
    gap: 6px;
  }

  .preview-image {
    width: 50px;
    height: 50px;
  }

  .controls-bar {
    padding: 6px 8px 8px;
  }
}
</style> 