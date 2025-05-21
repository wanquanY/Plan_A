<template>
  <div v-if="visible" class="agent-input-modal-wrapper" :style="modalStyle">
    <div class="agent-input-modal" ref="modalRef">
      <!-- Agent Response Display Area -->
      <div v-if="isAgentResponding || agentResponse || historyLength > 0" class="agent-response-area">
        <div class="history-navigation" v-if="historyLength > 0 && !isAgentResponding">
          <button 
            @click="emit('navigate-history', { direction: 'prev' })" 
            :disabled="historyIndex <= 0"
            class="history-nav-button prev-button"
          >
            &lt; Prev
          </button>
          <span class="history-indicator" v-if="historyLength > 0">
            {{ historyIndex + 1 }} / {{ historyLength }}
          </span>
          <button 
            @click="emit('navigate-history', { direction: 'next' })" 
            :disabled="historyIndex >= historyLength - 1"
            class="history-nav-button next-button"
          >
            Next &gt;
          </button>
        </div>

        <div v-if="isAgentResponding && !agentResponse && historyIndex === -1" class="loading-indicator">
          AI正在思考中...
        </div>
        <pre v-if="agentResponse" class="response-content">{{ agentResponse }}</pre>
        <div v-if="agentResponse && !isAgentResponding" class="response-actions">
          <button @click="handleInsertToEditor" class="insert-button">插入到编辑器</button>
        </div>
      </div>

      <div class="input-area">
        <textarea
          ref="inputRef"
          class="agent-input"
          placeholder="告诉我你想写点什么"
          v-model="inputValue"
          @keydown="handleKeydown"
          @click.stop
          @input="autoResize"
          rows="1"
        ></textarea>
      </div>
      
      <div class="bottom-controls">
        <div class="model-selector-container">
          <div 
            class="model-selector"
            @click.stop="showAgentSelector = !showAgentSelector"
          >
            <div class="model-avatar" v-if="selectedAgent">
              <img 
                :src="selectedAgent.avatar_url || 'https://placehold.co/40x40?text=AI'" 
                :alt="selectedAgent.name" 
                onerror="this.src='https://placehold.co/40x40?text=AI'"
              />
            </div>
            <span class="model-name">{{ selectedAgent ? selectedAgent.name : 'claude3.7 (我的副本)' }}</span>
            <svg class="dropdown-icon" viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M7 10l5 5 5-5z"></path>
            </svg>
          </div>
          
          <div v-if="showAgentSelector" class="model-dropdown">
            <div class="model-list">
              <div
                v-for="agent in agents"
                :key="agent.id"
                class="model-item"
                @click.stop="selectAgent(agent)"
              >
                <div class="model-item-avatar">
                  <img 
                    :src="agent.avatar_url || 'https://placehold.co/40x40?text=AI'" 
                    :alt="agent.name" 
                    onerror="this.src='https://placehold.co/40x40?text=AI'"
                  />
                </div>
                <span class="model-item-name">{{ agent.name }}</span>
              </div>
              <div v-if="loading" class="model-loading">加载中...</div>
              <div v-if="!loading && agents.length === 0" class="model-empty">暂无可用AI助手</div>
            </div>
          </div>
        </div>
        
        <div class="right-buttons">
          <button 
            class="attach-button"
            @click.stop
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"></path>
            </svg>
          </button>
          
          <button 
            class="send-button" 
            @click.stop="handleSendMessage"
            :disabled="!selectedAgent || !inputValue.trim()"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-input-modal-wrapper {
  position: fixed;
  z-index: 9999;
}

.agent-input-modal {
  width: 100%;
  background-color: white;
  border-radius: 14px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-sizing: border-box;
}

.input-area {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  max-height: 250px;
  overflow: hidden;
  position: relative;
}

.agent-input {
  width: 100%;
  box-sizing: border-box;
  border: none;
  outline: none;
  font-size: 16px;
  line-height: 1.5;
  color: #333;
  background: transparent;
  resize: none;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 24px;
  max-height: 220px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  padding: 0;
  margin: 0;
  word-wrap: break-word;
  display: block;
}

.agent-input::placeholder {
  color: #929292;
  font-weight: 400;
}

.bottom-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background-color: #fafafa;
  position: relative;
  box-sizing: border-box;
  max-width: 100%;
}

.model-selector-container {
  display: flex;
  align-items: center;
  position: static;
  box-sizing: border-box;
  max-width: 100%;
}

.model-selector {
  display: flex;
  align-items: center;
  background-color: #f1f1f1;
  border-radius: 20px;
  padding: 4px 12px 4px 4px;
  cursor: pointer;
  transition: background-color 0.15s;
  user-select: none;
  box-sizing: border-box;
  max-width: 100%;
  min-width: 0;
}

.model-selector:hover {
  background-color: #e9e9e9;
}

.model-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 8px;
  flex-shrink: 0;
}

.model-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  padding-right: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.dropdown-icon {
  opacity: 0.5;
}

.model-dropdown {
  position: absolute;
  top: 100%;
  left: 20px;
  min-width: 200px;
  max-width: 300px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 10000;
  overflow: hidden;
  margin-top: 5px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  animation: fadeIn 0.2s ease;
}

.model-list {
  max-height: 280px;
  overflow-y: auto;
}

.model-item {
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
  display: flex;
  align-items: center;
}

.model-item:hover {
  background-color: #f5f8ff;
}

.model-item-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  flex-shrink: 0;
}

.model-item-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-item-name {
  color: #333;
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-loading,
.model-empty {
  padding: 12px 16px;
  font-size: 13px;
  color: #888;
  text-align: center;
}

.right-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  box-sizing: border-box;
  max-width: 100%;
}

.attach-button, 
.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  cursor: pointer;
  transition: all 0.2s;
  outline: none;
  padding: 0;
}

.attach-button {
  width: 24px;
  height: 24px;
  color: rgba(0, 0, 0, 0.55);
}

.attach-button:hover {
  color: rgba(0, 0, 0, 0.8);
}

.send-button {
  width: 36px;
  height: 36px;
  background-color: #d6e5ff;
  border-radius: 50%;
  color: #0066ff;
}

.send-button:hover:not(:disabled) {
  background-color: #c5dcff;
  transform: scale(1.05);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.agent-response-area {
  padding: 12px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  max-height: 300px; /* Or as needed */
  overflow-y: auto;
  background-color: #f8f8f8; /* Slightly different background for distinction */
}

.loading-indicator {
  text-align: center;
  color: #666;
  padding: 20px;
}

.response-content-wrapper {
  display: flex;
  flex-direction: column;
}

.response-content {
  white-space: pre-wrap; /* Allows text to wrap */
  word-wrap: break-word;
  font-family: inherit; /* Inherit from modal */
  font-size: 15px;     /* Slightly smaller than input potentially */
  color: #333;
  background-color: #fff;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  margin-bottom: 10px;
  min-height: 50px; /* Ensure it has some height even with short content */
}

.response-actions {
  display: flex;
  justify-content: flex-end; /* Aligns button to the right */
  /* padding-top: 5px; Optional: space above the button if content is short */
}

.insert-button {
  align-self: flex-end; /* This is fine, or can be removed if parent handles alignment */
  padding: 6px 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.insert-button:hover {
  background-color: #0056b3;
}

.history-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.history-nav-button {
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.history-nav-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.history-indicator {
  font-size: 12px;
  color: #555;
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import agentService from '../services/agent';

const PROSEMIRROR_PADDING = 16; // 编辑器内边距 (px)
const FIXED_MODAL_WIDTH = 650; // 弹窗固定宽度 (px)
const VIEWPORT_BOTTOM_MARGIN = '20px'; // 弹窗距离视口底部距离

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  position: {
    type: Object,
    default: () => ({ y: 0, x: 0 })
  },
  editorInfo: {
    type: Object,
    default: () => ({ left: 0, right: 0, width: 0, editorOffsetLeft: 0 })
  },
  agentResponse: {
    type: String,
    default: ''
  },
  isAgentResponding: {
    type: Boolean,
    default: false
  },
  historyIndex: {
    type: Number,
    default: -1
  },
  historyLength: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history']);

// 状态变量
const modalRef = ref(null);
const inputRef = ref(null);
const inputValue = ref('');
const showAgentSelector = ref(false);
const agents = ref([]);
const loading = ref(false);
const selectedAgent = ref(null);

watch(() => props.agentResponse, (newValue) => {
  console.log('[AgentInputModal] prop agentResponse updated:', newValue);
});

watch(() => props.isAgentResponding, (newValue) => {
  console.log('[AgentInputModal] prop isAgentResponding updated:', newValue);
});

// 计算弹窗位置样式
const modalStyle = computed(() => {
  let calculatedLeft = '50%'; // 默认视口居中
  let calculatedTransform = 'translateX(-50%)'; // 配合默认视口居中

  if (props.editorInfo && props.editorInfo.left !== undefined && props.editorInfo.width !== undefined) {
    // 编辑器文本区域的左侧实际位置
    const textAreaLeft = props.editorInfo.left + PROSEMIRROR_PADDING;
    // 编辑器文本区域的实际宽度
    const textAreaWidth = props.editorInfo.width - (2 * PROSEMIRROR_PADDING);

    // 计算弹窗左侧位置，使其在文本区域内居中
    calculatedLeft = `${textAreaLeft + (textAreaWidth / 2) - (FIXED_MODAL_WIDTH / 2)}px`;
    calculatedTransform = 'none'; // 已经通过计算精确定位，不再需要 transform
  }
  
  return {
    position: 'fixed',
    left: calculatedLeft,
    bottom: VIEWPORT_BOTTOM_MARGIN, // 固定在视口底部
    width: `${FIXED_MODAL_WIDTH}px`, // 应用固定宽度
    maxWidth: '95vw', // 增加一个最大宽度限制，防止在极小屏幕溢出
    transform: calculatedTransform,
    zIndex: 9999
  };
});

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

// 发送消息 - 修改为处理selection问题的安全版本
const handleSendMessage = () => {
  console.log('[AgentInputModal] handleSendMessage called.');
  console.log('[AgentInputModal] inputValue:', inputValue.value);
  console.log('[AgentInputModal] selectedAgent.value before checks:', JSON.parse(JSON.stringify(selectedAgent.value || null)));

  if (!selectedAgent.value) {
    console.error('[AgentInputModal] Send failed: selectedAgent is null or undefined.');
    alert('发送失败：未选择AI助手。');
    return;
  }
  if (!selectedAgent.value.id) {
    console.error('[AgentInputModal] Send failed: selectedAgent.id is null or undefined. Agent object:', JSON.parse(JSON.stringify(selectedAgent.value)));
    alert('发送失败：选中的AI助手信息不完整 (缺少ID)。');
    return;
  }
  if (!inputValue.value.trim()) {
    console.warn('[AgentInputModal] Send attempt with empty input.');
    return;
  }

  const messageData = {
    agentId: selectedAgent.value.id,
    content: inputValue.value.trim(),
    agent: selectedAgent.value
  };
  console.log('[AgentInputModal] Prepared messageData:', messageData);
  
  // 清空输入框，但**不关闭弹窗**，等待父组件传递响应
  inputValue.value = ''; 
  // close(); // 移除 close() 调用

  nextTick(() => {
    console.log('[AgentInputModal] Emitting send event with data:', messageData);
    emit('send', messageData); 
    // 用户发送后，可以不清空输入框，或者由父组件决定何时清空
    // inputValue.value = ''; // 移到父组件成功处理'send'事件后，或者用户点击'insert'或'close'后
  });
};

// 新增：处理插入到编辑器
const handleInsertToEditor = () => {
  if (props.agentResponse) {
    emit('request-insert', props.agentResponse);
    // 可以在这里决定插入后是否关闭弹窗，或由父组件处理
    // close(); 
  }
};

// 处理键盘按键事件
const handleKeydown = (event) => {
  // 处理Escape键
  if (event.key === 'Escape') {
    close();
    return;
  }
  
  // 处理Enter键
  if (event.key === 'Enter') {
    // 如果按下Shift+Enter，不阻止默认行为（允许换行）
    if (event.shiftKey) {
      console.log('按下Shift+Enter, 插入换行');
      return;
    }
    
    // 如果是单独的Enter键，阻止默认行为并发送消息
    event.preventDefault();
    handleSendMessage();
  }
};

// 关闭弹窗
const close = () => {
  emit('close');
};

// 添加自动调整输入框高度的方法
const autoResize = () => {
  if (!inputRef.value) return;
  
  // 首先重置高度，以便正确计算新高度
  inputRef.value.style.height = 'auto';
  
  // 计算新高度，但不超过最大高度
  const scrollHeight = inputRef.value.scrollHeight;
  const maxHeight = 220; // 最大高度220px，与CSS中定义一致
  
  if (scrollHeight <= maxHeight) {
    // 如果内容高度未超过最大高度，设置为实际高度并隐藏滚动条
    inputRef.value.style.height = `${scrollHeight}px`;
    inputRef.value.style.overflowY = 'hidden';
  } else {
    // 如果内容高度超过最大高度，设置为最大高度并显示滚动条
    inputRef.value.style.height = `${maxHeight}px`;
    inputRef.value.style.overflowY = 'auto';
  }
  
  console.log(`输入框高度: ${inputRef.value.style.height}, 内容高度: ${scrollHeight}px, 是否显示滚动条: ${scrollHeight > maxHeight}`);
};

// 当弹窗显示时，加载Agent列表并聚焦输入框，同时调整输入框高度
watch(() => props.visible, async (newValue) => {
  if (newValue) {
    // 加载Agent列表
    if (agents.value.length === 0) {
      await fetchAgents();
    } else if (agents.value.length > 0 && !selectedAgent.value) {
      // 如果已有Agent列表但尚未选择，默认选择第一个
      selectAgent(agents.value[0]);
    }
    
    // 重置并聚焦到输入框
    nextTick(() => {
      if (inputRef.value) {
        // 重置文本框高度
        inputRef.value.style.height = 'auto';
        inputRef.value.style.overflowY = 'hidden'; // 初始状态隐藏滚动条
        
        // 应用自动调整高度
        autoResize();
        
        // 聚焦到输入框
        inputRef.value.focus();
      }
    });
  } else {
    // 重置一些状态
    showAgentSelector.value = false;
  }
}, { immediate: true });

// 监听inputValue变化，自动调整输入框高度
watch(() => inputValue.value, () => {
  nextTick(() => {
    autoResize();
  });
});

// 组件挂载时添加键盘事件监听
onMounted(() => {
  // document.addEventListener('keydown', handleKeyDown); // The one in setup for keydown on textarea is different
  // document.addEventListener('click', handleClickOutside, true); // REMOVING
});

// 组件卸载时移除事件监听
onUnmounted(() => {
  // document.removeEventListener('keydown', handleKeyDown); // REMOVING
  // document.removeEventListener('click', handleClickOutside, true); // REMOVING
});
</script> 