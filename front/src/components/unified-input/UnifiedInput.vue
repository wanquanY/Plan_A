<template>
  <div class="unified-container">
    <!-- 输入框区域 -->
    <div class="input-area">
      <textarea
        ref="inputRef"
        class="unified-textarea"
        :placeholder="placeholder"
        v-model="inputValue"
        @keydown="handleKeydown"
        @input="autoResize"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
        @paste="handlePaste"
        @drop="handleDrop"
        @dragover="handleDragOver"
        @dragenter="handleDragEnter"
        @dragleave="handleDragLeave"
        rows="1"
      ></textarea>
      
      <!-- 图片预览区域 -->
      <div v-if="previewImages.length > 0" class="image-preview-container">
        <div v-for="(image, index) in previewImages" :key="index" class="image-preview-item">
          <img :src="image.url" :alt="image.name" class="preview-image" />
          <button class="remove-image-btn" @click="removeImage(index)" type="button">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- 上传进度提示 -->
      <div v-if="uploadingCount > 0" class="upload-progress">
        <div class="upload-spinner"></div>
        <span>正在上传 {{ uploadingCount }} 张图片...</span>
      </div>
    </div>
    
    <!-- 底部操作栏 -->
    <div class="controls-bar">
      <!-- 左侧控制 -->
      <div class="left-controls">
        <!-- Agent选择器 -->
        <div class="agent-tag" @click.stop="showAgentSelector = !showAgentSelector">
          <div class="agent-arrow">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
              <polyline :points="showAgentSelector ? '18,15 12,9 6,15' : '6,9 12,15 18,9'"></polyline>
            </svg>
          </div>
          <span class="agent-label">{{ selectedAgent?.name || '小助理' }}</span>
          
          <!-- Agent下拉菜单 -->
          <div v-if="showAgentSelector" class="agent-dropdown-unified">
            <div class="agent-dropdown-list">
              <div
                v-for="agent in agents"
                :key="agent.id"
                class="agent-dropdown-item"
                :class="{ selected: selectedAgent?.id === agent.id }"
                @click.stop="selectAgent(agent)"
              >
                  <img 
                  class="agent-dropdown-avatar"
                    :src="agent.avatar_url || 'https://placehold.co/24x24?text=AI'" 
                    :alt="agent.name" 
                    onerror="this.src='https://placehold.co/24x24?text=AI'"
                  />
                <span class="agent-dropdown-name">{{ agent.name }}</span>
              </div>
              <div v-if="loading" class="agent-dropdown-loading">
                <div class="loading-spinner"></div>
                加载中...
              </div>
              <div v-if="!loading && agents.length === 0" class="agent-dropdown-empty">暂无可用AI助手</div>
            </div>
          </div>
        </div>
        
        <!-- 调整按钮 -->
        <div class="adjust-button-container">
          <button 
            class="adjust-btn"
            @click="showAdjustMenu = !showAdjustMenu"
            title="调整"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path>
            </svg>
            <span>调整</span>
          </button>
          
          <!-- 调整下拉菜单 -->
          <div v-if="showAdjustMenu" class="adjust-dropdown">
            <div class="adjust-dropdown-list">
              <div
                v-for="option in adjustOptions"
                :key="option.key"
                class="adjust-dropdown-item"
                @click.stop="handleAdjust(option.key)"
              >
                <span class="adjust-dropdown-name">{{ option.label }}</span>
              </div>
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
          :disabled="!selectedAgent || (!inputValue.trim() && previewImages.length === 0 && !isAgentResponding)"
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
const inputValue = ref('');
const selectedAgent = ref(null);
const agents = ref([]);
const showAgentSelector = ref(false);
const showAdjustMenu = ref(false);
const isComposing = ref(false);
const adjustOptions = ref([
  { key: 'formal', label: '更正式' },
  { key: 'casual', label: '更随意' },
  { key: 'shorter', label: '更简短' },
  { key: 'longer', label: '更详细' }
]);
const loading = ref(false);

// 图片相关状态
const previewImages = ref([]);
const uploadingCount = ref(0);
const isDragOver = ref(false);

// 加载Agent列表
const fetchAgents = async () => {
  loading.value = true;
  try {
    const agentList = await agentService.getAllAgents();
    agents.value = agentList;
    console.log(`已加载${agentList.length}个AI助手`);
    
    // 默认选择第一个Agent
    if (agentList.length > 0 && !selectedAgent.value) {
      selectAgent(agentList[0]);
    }
  } catch (error) {
    console.error('加载AI助手列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 选择Agent
const selectAgent = (agent) => {
  selectedAgent.value = agent;
  showAgentSelector.value = false;
  emit('select-agent', agent);
  
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
  const files = Array.from(event.target.files || []);
  await uploadImages(files);
  // 清空文件输入框，允许重复选择相同文件
  event.target.value = '';
};

// 处理拖拽相关事件
const handleDragOver = (event) => {
  event.preventDefault();
  event.stopPropagation();
};

const handleDragEnter = (event) => {
  event.preventDefault();
  event.stopPropagation();
  isDragOver.value = true;
};

const handleDragLeave = (event) => {
  event.preventDefault();
  event.stopPropagation();
  // 只有当离开整个输入区域时才取消拖拽状态
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false;
  }
};

const handleDrop = async (event) => {
  event.preventDefault();
  event.stopPropagation();
  isDragOver.value = false;
  
  const files = Array.from(event.dataTransfer?.files || []).filter(file => 
    file.type.startsWith('image/')
  );
  
  if (files.length > 0) {
    await uploadImages(files);
  }
};

// 处理粘贴事件
const handlePaste = async (event) => {
  const clipboardItems = event.clipboardData?.items;
  if (!clipboardItems) return;
  
  const imageFiles = [];
  
  for (let i = 0; i < clipboardItems.length; i++) {
    const item = clipboardItems[i];
    if (item.type.indexOf('image') !== -1) {
      const file = item.getAsFile();
      if (file) {
        imageFiles.push(file);
      }
    }
  }
  
  if (imageFiles.length > 0) {
    event.preventDefault(); // 阻止默认粘贴行为
    await uploadImages(imageFiles);
  }
};

// 上传图片
const uploadImages = async (files) => {
  const validFiles = files.filter(file => file.type.startsWith('image/'));
  
  if (validFiles.length === 0) {
    message.warning('请选择有效的图片文件');
    return;
  }
  
  uploadingCount.value = validFiles.length;
  
  try {
    const uploadPromises = validFiles.map(async (file) => {
      try {
        const url = await uploadService.uploadImage(file);
        return {
          file,
          url,
          name: file.name,
          size: file.size
        };
      } catch (error) {
        console.error(`上传图片 ${file.name} 失败:`, error);
        message.error(`上传图片 ${file.name} 失败`);
        return null;
      }
    });
    
    const results = await Promise.all(uploadPromises);
    const successfulUploads = results.filter(result => result !== null);
    
    // 添加到预览列表
    previewImages.value.push(...successfulUploads);
    
    if (successfulUploads.length > 0) {
      message.success(`成功上传 ${successfulUploads.length} 张图片`);
    }
    
  } catch (error) {
    console.error('批量上传图片失败:', error);
    message.error('上传图片失败');
  } finally {
    uploadingCount.value = 0;
  }
};

// 移除图片
const removeImage = (index) => {
  previewImages.value.splice(index, 1);
};

// 发送消息或停止响应
const handleSendMessage = () => {
  // 如果agent正在响应，则停止响应
  if (props.isAgentResponding) {
    emit('stop-response');
    return;
  }

  // 否则正常发送消息
  if (!selectedAgent.value) {
    message.warning('请先选择AI助手');
    return;
  }
  if (!selectedAgent.value.id) {
    message.error('选中的AI助手信息不完整');
    return;
  }
  if (!inputValue.value.trim() && previewImages.value.length === 0) {
    return;
  }

  const messageData = {
    agentId: selectedAgent.value.id,
    content: inputValue.value.trim(),
    images: previewImages.value,
    agent: selectedAgent.value
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
  fetchAgents();
  
  if (props.autoFocus) {
    nextTick(() => {
      inputRef.value?.focus();
      // 确保初始高度正确
      autoResize();
    });
  }
  
  // 点击外部关闭Agent选择器和调整菜单
  const handleClickOutside = (event) => {
    if (showAgentSelector.value && !event.target.closest('.agent-tag')) {
      showAgentSelector.value = false;
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
</script>

<style scoped>
.unified-container {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.unified-container:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08), 0 1px 3px rgba(0, 0, 0, 0.1);
}

.input-area {
  padding: 12px 16px 8px;
}

.unified-textarea {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  line-height: 1.4;
  color: #1f2937;
  resize: none;
  min-height: 20px;
  max-height: 120px;
  transition: border-color 0.2s ease;
}

.unified-textarea::placeholder {
  color: #9ca3af;
}

/* 拖拽状态样式 */
.unified-textarea.drag-over {
  background-color: rgba(99, 102, 241, 0.05);
  border-color: #6366f1;
}

/* 图片预览容器 */
.image-preview-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.image-preview-item {
  position: relative;
  display: inline-block;
}

.preview-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.remove-image-btn {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 18px;
  height: 18px;
  background: #ef4444;
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.remove-image-btn:hover {
  background: #dc2626;
}

/* 上传进度提示 */
.upload-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 12px;
  color: #6b7280;
}

.upload-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.agent-tag {
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

.agent-tag:hover {
  background: #e5e7eb;
}

.agent-arrow {
  width: 12px;
  height: 12px;
  color: #6b7280;
  transition: transform 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.agent-label {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
  line-height: 1;
}

.agent-dropdown-unified {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
  min-width: 100px;
  width: max-content;
}

.agent-dropdown-list {
  padding: 4px;
}

.agent-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s ease;
  min-width: 0;
}

.agent-dropdown-item:hover {
  background: #f3f4f6;
}

.agent-dropdown-item.selected {
  background: #e0e7ff;
  color: #3730a3;
}

.agent-dropdown-avatar {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.agent-dropdown-name {
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
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
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
.agent-dropdown-loading,
.agent-dropdown-empty {
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