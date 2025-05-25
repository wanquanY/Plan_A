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
        rows="1"
      ></textarea>
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
                @click.stop="selectAgent(agent)"
              >
                <div class="agent-dropdown-avatar">
                  <img 
                    :src="agent.avatar_url || 'https://placehold.co/24x24?text=AI'" 
                    :alt="agent.name" 
                    onerror="this.src='https://placehold.co/24x24?text=AI'"
                  />
                </div>
                <span class="agent-dropdown-name">{{ agent.name }}</span>
              </div>
              <div v-if="loading" class="agent-dropdown-loading">
                <div class="loading-spinner small"></div>
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
          @click="$emit('upload-file')"
          title="上传文件"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"></path>
          </svg>
        </button>
        
        <button 
          class="send-btn" 
          @click="handleSendMessage"
          :disabled="!selectedAgent || !inputValue.trim()"
          title="发送"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import agentService from '../../services/agent';

const props = defineProps({
  placeholder: {
    type: String,
    default: '发消息、输入 @ 选择技能或 / 选择文件'
  },
  autoFocus: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['send', 'select-agent', 'upload-file', 'adjust-tone']);

// 状态变量
const inputRef = ref(null);
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

// 发送消息
const handleSendMessage = () => {
  if (!selectedAgent.value) {
    alert('发送失败：未选择AI助手。');
    return;
  }
  if (!selectedAgent.value.id) {
    alert('发送失败：选中的AI助手信息不完整。');
    return;
  }
  if (!inputValue.value.trim()) {
    return;
  }

  const messageData = {
    agentId: selectedAgent.value.id,
    content: inputValue.value.trim(),
    agent: selectedAgent.value
  };
  
  // 清空输入框
  inputValue.value = ''; 

  nextTick(() => {
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
}

.unified-textarea::placeholder {
  color: #9ca3af;
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
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  gap: 8px;
}

.agent-dropdown-item:hover {
  background: #f3f4f6;
}

.agent-dropdown-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.agent-dropdown-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.agent-dropdown-name {
  font-size: 13px;
  color: #374151;
}

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

@keyframes spin {
  to { transform: rotate(360deg); }
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
  background: #5b5ce6;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

/* 滚动条美化 */
.agent-dropdown-unified::-webkit-scrollbar {
  width: 4px;
}

.agent-dropdown-unified::-webkit-scrollbar-track {
  background: transparent;
}

.agent-dropdown-unified::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 2px;
  transition: background-color 0.2s ease;
}

.agent-dropdown-unified::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.25);
}

.adjust-button-container {
  position: relative;
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
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
  min-width: 100px;
  width: max-content;
}

.adjust-dropdown-list {
  padding: 4px;
}

.adjust-dropdown-item {
  display: flex;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  gap: 8px;
}

.adjust-dropdown-item:hover {
  background: #f3f4f6;
}

.adjust-dropdown-name {
  font-size: 13px;
  color: #374151;
}

.adjust-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
}

.adjust-btn:hover {
  background: #e5e7eb;
  color: #374151;
}
</style> 