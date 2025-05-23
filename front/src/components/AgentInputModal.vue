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
        </div>
        
        <!-- 初始加载指示器（仅在没有任何响应内容时显示） -->
        <div v-else-if="isAgentResponding && historyIndex === -1" class="loading-indicator">
          <div class="loading-spinner"></div>
          <span>AI正在思考中...</span>
        </div>
        
        <!-- 操作按钮栏 - 仿照截图的布局 -->
        <div v-if="agentResponse && !isAgentResponding" class="response-actions">
          <div class="action-buttons-left">
            <button @click="handleInsertToEditor" class="action-button primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14,2 14,8 20,8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10,9 9,9 8,9"></polyline>
              </svg>
              插入文档
            </button>
            
            <button @click="copyResponse" class="action-button secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              复制
            </button>
            
            <div class="action-button-dropdown">
              <button @click="toggleAdjustMenu" class="action-button secondary dropdown-trigger">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path>
                </svg>
                调整
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="dropdown-arrow">
                  <polyline points="6,9 12,15 18,9"></polyline>
                </svg>
              </button>
              
              <div v-if="showAdjustMenu" class="adjust-dropdown">
                <button @click="adjustTone('formal')" class="adjust-option">更正式</button>
                <button @click="adjustTone('casual')" class="adjust-option">更随意</button>
                <button @click="adjustTone('shorter')" class="adjust-option">更简短</button>
                <button @click="adjustTone('longer')" class="adjust-option">更详细</button>
              </div>
            </div>
          </div>
          
          <div class="action-buttons-right">
            <!-- 历史导航 -->
            <div class="history-controls" v-if="historyLength > 0">
              <button 
                @click="emit('navigate-history', { direction: 'prev' })" 
                :disabled="historyIndex <= 0"
                class="nav-button"
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
                class="nav-button"
                title="下一条回复"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="9,18 15,12 9,6"></polyline>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="unified-input-container">
          <!-- Agent选择器 -->
          <div class="model-selector-container">
            <div 
              class="model-selector"
              @click.stop="showAgentSelector = !showAgentSelector"
            >
              <span class="model-name">{{ selectedAgent ? selectedAgent.name : 'AI助手' }}</span>
              <svg class="dropdown-icon" viewBox="0 0 24 24" width="12" height="12">
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
                <div v-if="loading" class="model-loading">
                  <div class="loading-spinner small"></div>
                  加载中...
                </div>
                <div v-if="!loading && agents.length === 0" class="model-empty">暂无可用AI助手</div>
              </div>
            </div>
          </div>

          <!-- 输入框 -->
          <textarea
            ref="inputRef"
            class="agent-input"
            placeholder="问个问题，或者告诉我你想写点什么"
            v-model="inputValue"
            @keydown="handleKeydown"
            @click.stop
            @input="autoResize"
            rows="1"
          ></textarea>
          
          <!-- 右侧操作按钮 -->
          <div class="input-actions">
            <button 
              class="attach-button"
              @click.stop
              title="附件"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"></path>
              </svg>
            </button>
            
            <button 
              class="send-button" 
              @click.stop="handleSendMessage"
              :disabled="!selectedAgent || !inputValue.trim()"
              title="发送"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

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

.unified-input-container {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: #f1f3f4;
  border-radius: 24px;
  padding: 12px 16px;
  border: 1px solid rgba(229, 231, 235, 0.6);
  transition: all 0.2s ease;
}

.unified-input-container:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.model-selector-container {
  position: relative;
  flex-shrink: 0;
}

.model-selector {
  display: flex;
  align-items: center;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  padding: 4px 8px;
  border-radius: 12px;
}

.model-selector:hover {
  background: rgba(255, 255, 255, 0.6);
}

.model-name {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
  margin-right: 4px;
}

.dropdown-icon {
  color: #6b7280;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.agent-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 16px;
  line-height: 1.5;
  color: #1f2937;
  resize: none;
  overflow-y: hidden;
  min-height: 24px;
  max-height: 120px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  padding: 0;
  margin: 0;
  word-wrap: break-word;
}

.agent-input::placeholder {
  color: #9ca3af;
  font-weight: 400;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.attach-button,
.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
  position: relative;
}

.attach-button {
  background: transparent;
  color: #6b7280;
}

.attach-button:hover {
  background: rgba(255, 255, 255, 0.6);
  color: #374151;
}

.send-button {
  background: #6366f1;
  color: white;
}

.send-button:hover:not(:disabled) {
  background: #5b5ce6;
  transform: scale(1.05);
}

.send-button:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
}

.model-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  background: #ffffff;
  border: 1px solid rgba(229, 231, 235, 0.6);
  border-radius: 12px;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.12),
    0 10px 10px -5px rgba(0, 0, 0, 0.06);
  z-index: 10000;
  max-height: 240px;
  overflow-y: auto;
  min-width: 200px;
}

.model-list {
  padding: 8px;
}

.model-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 8px;
  margin-bottom: 2px;
}

.model-item:hover {
  background: #f8fafc;
}

.model-item:last-child {
  margin-bottom: 0;
}

.model-item-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  flex-shrink: 0;
  border: 1px solid rgba(229, 231, 235, 0.6);
}

.model-item-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-item-name {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.model-loading,
.model-empty {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* Agent Response Area Styles */
.agent-response-area {
  border-bottom: 1px solid rgba(229, 231, 235, 0.5);
  padding: 24px;
  background: #fafbfc;
  overflow: visible; /* 完全移除滚动，让下拉菜单可以正常显示 */
  position: relative; /* 确保下拉菜单正确定位 */
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

.loading-spinner.small {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.response-content {
  background: #ffffff;
  border: 1px solid rgba(229, 231, 235, 0.5);
  border-radius: 12px;
  padding: 20px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0 0 16px 0;
  max-height: 320px;
  overflow-y: auto;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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

.history-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #6366f1 0%, #5b5ce6 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(99, 102, 241, 0.2);
}

.nav-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #5b5ce6 0%, #4f46e5 100%);
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.3);
  transform: translateY(-1px);
}

.nav-button:disabled {
  background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
  color: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.page-indicator {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin: 0 6px;
}

.response-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  position: relative; /* 确保下拉菜单正确定位 */
  z-index: 10; /* 提高层级 */
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
  z-index: 1; /* 确保dropdown容器有合适的层级 */
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

.adjust-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  background: #ffffff;
  border: 1px solid rgba(234, 236, 240, 0.8);
  border-radius: 16px;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.15),
    0 10px 10px -5px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  z-index: 999999; /* 进一步提高z-index */
  max-height: 240px;
  overflow-y: auto;
  backdrop-filter: blur(8px);
  min-width: 120px;
  /* 确保下拉菜单不被父容器裁剪 */
  transform: translateZ(0);
  will-change: transform;
}

.adjust-option {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 12px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.adjust-option:hover {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f3f5 100%);
}

/* 滚动条美化 */
.response-content::-webkit-scrollbar,
.model-dropdown::-webkit-scrollbar {
  width: 6px;
}

.response-content::-webkit-scrollbar-track,
.model-dropdown::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.response-content::-webkit-scrollbar-thumb,
.model-dropdown::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.response-content::-webkit-scrollbar-thumb:hover,
.model-dropdown::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.bottom-controls {
  padding: 16px 24px;
  background: #fafbfc;
  position: relative;
  box-sizing: border-box;
  border-top: 1px solid rgba(229, 231, 235, 0.5);
}

.model-selector-container {
  display: flex;
  align-items: center;
  position: relative;
}

.model-selector {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(229, 231, 235, 0.6);
  border-radius: 20px;
  padding: 6px 14px 6px 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  box-sizing: border-box;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.model-selector:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.model-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  flex-shrink: 0;
  border: 2px solid rgba(229, 231, 235, 0.6);
}

.model-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-name {
  font-size: 14px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  font-weight: 500;
}

.dropdown-icon {
  margin-left: 8px;
  color: #6b7280;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.model-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: #ffffff;
  border: 1px solid rgba(229, 231, 235, 0.6);
  border-radius: 12px;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.12),
    0 10px 10px -5px rgba(0, 0, 0, 0.06);
  z-index: 10000;
  max-height: 240px;
  overflow-y: auto;
}

.model-list {
  padding: 8px;
}

.model-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 8px;
  margin-bottom: 2px;
}

.model-item:hover {
  background: #f8fafc;
}

.model-item:last-child {
  margin-bottom: 0;
}

.model-item-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  flex-shrink: 0;
  border: 1px solid rgba(229, 231, 235, 0.6);
}

.model-item-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-item-name {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.model-loading,
.model-empty {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.model-dropdown::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
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

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history', 'adjust-tone']);

// 状态变量
const modalRef = ref(null);
const inputRef = ref(null);
const inputValue = ref('');
const showAgentSelector = ref(false);
const agents = ref([]);
const loading = ref(false);
const selectedAgent = ref(null);
const showAdjustMenu = ref(false);

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

// 自动调整输入框高度
const autoResize = () => {
  const textarea = inputRef.value;
  if (textarea) {
    // 重置高度以获取正确的 scrollHeight
    textarea.style.height = 'auto';
    
    // 计算新高度，在新设计中使用更小的最大高度
    const newHeight = Math.min(textarea.scrollHeight, 120); // 最大高度120px
    textarea.style.height = `${newHeight}px`;
    
    // 显示滚动条如果内容超出最大高度
    if (textarea.scrollHeight > 120) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
    
    console.log('[AgentInputModal] Textarea auto-resized to:', newHeight);
  }
};

// 组件挂载时初始化
onMounted(() => {
  fetchAgents();
  
  // 获得焦点
  nextTick(() => {
    inputRef.value?.focus();
  });
  
  // 只处理点击外部关闭调整菜单
  const handleClickOutside = (event) => {
    // 点击外部关闭调整菜单
    if (showAdjustMenu.value && !event.target.closest('.action-button-dropdown')) {
      showAdjustMenu.value = false;
    }
  };
  
  document.addEventListener('mousedown', handleClickOutside);
  
  onUnmounted(() => {
    document.removeEventListener('mousedown', handleClickOutside);
  });
});

// Watch 弹窗显示状态，自动聚焦
watch(() => props.visible, (visible) => {
  if (visible) {
    nextTick(() => {
      inputRef.value?.focus();
    });
  }
});

// 新增：处理调整语气
const adjustTone = (tone) => {
  console.log(`调整语气为: ${tone}`);
  showAdjustMenu.value = false;
  // 可以发送事件给父组件处理
  emit('adjust-tone', { tone, originalResponse: props.agentResponse });
};

// 新增：处理复制响应
const copyResponse = async () => {
  if (props.agentResponse) {
    try {
      await navigator.clipboard.writeText(props.agentResponse);
      console.log('响应已复制到剪贴板');
      // 可以显示一个简短的成功提示
    } catch (err) {
      console.error('复制失败:', err);
    }
  }
};

// 新增：处理调整菜单显示
const toggleAdjustMenu = () => {
  showAdjustMenu.value = !showAdjustMenu.value;
};
</script> 