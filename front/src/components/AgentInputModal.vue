<template>
  <div v-if="visible" class="agent-input-modal-wrapper" :style="modalStyle">
    <div class="agent-input-modal" ref="modalRef">
      <!-- Mac风格关闭按钮 -->
      <div class="mac-close-button" @click="close" title="关闭">
        <div class="close-x">×</div>
      </div>
      
      <!-- Agent Response Display Area -->
      <div v-if="isAgentResponding || agentResponse || historyLength > 0" class="agent-response-area">
        <!-- 显示流式响应内容 -->
        <div v-if="agentResponse" class="response-content">
          {{ agentResponse }}
          <!-- 在流式响应过程中显示打字指示器 -->
          <span v-if="isAgentResponding" class="typing-indicator">|</span>
          
          <!-- 操作按钮（仅图标，与侧边栏样式一致） -->
          <div v-if="!isAgentResponding" class="message-actions">
            <!-- 历史导航按钮 -->
            <template v-if="historyLength > 0">
              <button 
                @click="emit('navigate-history', { direction: 'prev' })" 
                :disabled="historyIndex <= 0"
                class="action-btn"
                title="上一条回复"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="15,18 9,12 15,6"></polyline>
                </svg>
              </button>
              
              <span class="page-indicator">{{ historyIndex + 1 }}/{{ historyLength }}</span>
              
              <button 
                @click="emit('navigate-history', { direction: 'next' })" 
                :disabled="historyIndex >= historyLength - 1"
                class="action-btn"
                title="下一条回复"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="9,18 15,12 9,6"></polyline>
                </svg>
              </button>
              
              <!-- 分隔符 -->
              <div class="action-separator"></div>
            </template>
            
            <button @click="handleInsertToEditor" class="action-btn" title="插入文档">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 10L5 6M5 6L9 2M5 6h11a4 4 0 0 1 4 4v4"></path>
              </svg>
            </button>
            <button @click="copyResponse" class="action-btn" title="复制">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
          </div>
        </div>
        
        <!-- 加载指示器（当正在响应但还没有内容时显示） -->
        <div v-else-if="isAgentResponding" class="loading-indicator">
          <div class="loading-spinner"></div>
          <span>AI正在思考中...</span>
        </div>
      </div>

      <div class="input-area">
        <UnifiedInput 
          placeholder="问个问题，或者告诉我你想写点什么"
          @send="handleSendMessage"
          @select-agent="handleSelectAgent"
          @upload-file="handleUploadFile"
          @adjust-tone="handleAdjustTone"
          ref="unifiedInputRef"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import UnifiedInput from './unified-input/UnifiedInput.vue';

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

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history', 'adjust-tone']);

// 状态变量
const modalRef = ref(null);
const unifiedInputRef = ref(null);

watch(() => props.agentResponse, (newValue) => {
  console.log('[AgentInputModal] prop agentResponse updated:', newValue);
});

watch(() => props.isAgentResponding, (newValue) => {
  console.log('[AgentInputModal] prop isAgentResponding updated:', newValue);
});

// 计算弹窗位置样式
const modalStyle = computed(() => {
  let calculatedLeft = '50%';
  let calculatedTransform = 'translateX(-50%)';

  if (props.editorInfo && props.editorInfo.left !== undefined && props.editorInfo.width !== undefined) {
    const textAreaLeft = props.editorInfo.left + PROSEMIRROR_PADDING;
    const textAreaWidth = props.editorInfo.width - (2 * PROSEMIRROR_PADDING);
    calculatedLeft = `${textAreaLeft + (textAreaWidth / 2) - (FIXED_MODAL_WIDTH / 2)}px`;
    calculatedTransform = 'none';
  }
  
  return {
    position: 'fixed',
    left: calculatedLeft,
    bottom: VIEWPORT_BOTTOM_MARGIN,
    width: `${FIXED_MODAL_WIDTH}px`,
    maxWidth: '95vw',
    transform: calculatedTransform,
    zIndex: 9999
  };
});

// 发送消息
const handleSendMessage = (messageData) => {
  console.log('[AgentInputModal] handleSendMessage called.');
  console.log('[AgentInputModal] Prepared messageData:', messageData);
  
  nextTick(() => {
    console.log('[AgentInputModal] Emitting send event with data:', messageData);
    emit('send', messageData); 
  });
};

// 选择Agent
const handleSelectAgent = (agent) => {
  emit('select-agent', agent);
};

// 上传文件
const handleUploadFile = () => {
  console.log('上传文件功能待实现');
};

// 处理插入到编辑器
const handleInsertToEditor = () => {
  if (props.agentResponse) {
    emit('request-insert', props.agentResponse);
  }
};

// 关闭弹窗
const close = () => {
  emit('close');
};

// Watch 弹窗显示状态，自动聚焦
watch(() => props.visible, (visible) => {
  if (visible) {
    nextTick(() => {
      unifiedInputRef.value?.focus();
    });
  }
});

// 处理调整语气
const handleAdjustTone = (tone) => {
  console.log(`调整语气为: ${tone}`);
  emit('adjust-tone', { tone, originalResponse: props.agentResponse });
};

// 处理复制响应
const copyResponse = async () => {
  if (props.agentResponse) {
    try {
      await navigator.clipboard.writeText(props.agentResponse);
      console.log('响应已复制到剪贴板');
    } catch (err) {
      console.error('复制失败:', err);
    }
  }
};

// 组件挂载时初始化
onMounted(() => {
  nextTick(() => {
    unifiedInputRef.value?.focus();
  });
  
  const handleClickOutside = (event) => {
    // 可以在这里处理特定的点击外部逻辑，比如关闭下拉菜单等
    // 但不要自动关闭整个弹框
  };
  
  document.addEventListener('mousedown', handleClickOutside);
  
  onUnmounted(() => {
    document.removeEventListener('mousedown', handleClickOutside);
  });
});
</script>

<style scoped>
.agent-input-modal-wrapper {
  position: fixed;
  z-index: 9999;
  pointer-events: all;
}

.agent-input-modal {
  width: 100%;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 
    0 24px 48px rgba(0, 0, 0, 0.12),
    0 12px 24px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: visible;
  border: 1px solid rgba(229, 231, 235, 0.8);
  box-sizing: border-box;
  position: relative;
}

/* Mac风格关闭按钮 */
.mac-close-button {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #ff5f57;
  border: 1px solid #e0443e;
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.mac-close-button:hover {
  background: #ff4136;
  border-color: #d73027;
  transform: scale(1.1);
}

.mac-close-button:active {
  transform: scale(0.95);
}

.close-x {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  font-weight: 500;
}

.input-area {
  padding: 24px;
  position: relative;
  background: #ffffff;
}

/* 与侧边栏一致的操作按钮样式 */
.message-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0.7;
}

.action-btn:hover:not(:disabled) {
  background: #e5e7eb;
  color: #374151;
  opacity: 1;
}

.action-btn:disabled {
  color: #d1d5db;
  cursor: not-allowed;
  opacity: 0.4;
}

.action-btn:disabled:hover {
  background: transparent;
}

.action-separator {
  width: 1px;
  height: 16px;
  background: #e5e7eb;
  margin: 0 4px;
}

.page-indicator {
  font-size: 10px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 2px;
  white-space: nowrap;
}

/* Agent Response Area Styles */
.agent-response-area {
  border-bottom: 1px solid rgba(229, 231, 235, 0.5);
  padding: 24px;
  background: #fafbfc;
  overflow: visible;
  position: relative;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
}

.loading-spinner {
  width: 20px;
  height: 20px;
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

.response-content {
  padding: 16px 0;
  font-size: 14px;
  line-height: 1.5;
  color: #1f2937;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0 0 16px 0;
  max-height: 320px;
  overflow-y: auto;
  position: relative;
}

.typing-indicator {
  color: #6366f1;
  font-weight: bold;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

.response-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  position: relative;
  z-index: 10;
}

.action-buttons-left,
.action-buttons-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
}

.action-button:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
  transform: translateY(-1px);
}

.action-button.primary {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.action-button.secondary {
  background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
  color: #6b7280;
}

.action-button.secondary:hover {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f3f5 100%);
}

.action-button-dropdown {
  position: relative;
  z-index: 1;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
  color: #6b7280;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropdown-trigger:hover {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f3f5 100%);
}

.dropdown-arrow {
  margin-left: 4px;
  color: #6b7280;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

/* 滚动条美化 */
.response-content::-webkit-scrollbar {
  width: 2px;
}

.response-content::-webkit-scrollbar-track {
  background: transparent;
}

.response-content::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.1);
  border-radius: 1px;
  transition: background-color 0.2s ease;
}

.response-content::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.2);
}
</style> 