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
          <!-- 正在打字时显示简单文本和打字指示器 -->
          <div v-if="isAgentResponding" class="typing-content">
            <span>{{ agentResponse }}</span>
            <span class="typing-indicator">|</span>
          </div>
          <!-- 打字完成后显示渲染的markdown内容 -->
          <div v-else class="markdown-content" v-html="renderMarkdown(agentResponse)"></div>
          
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
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2 2v1"></path>
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

      <!-- 渲染组件（隐藏） -->
      <div style="display: none;">
        <MermaidRenderer ref="mermaidRenderer" />
        <CodeBlock ref="codeBlockRenderer" :code="''" :language="'text'" />
        <MarkMap ref="markMapRenderer" :content="''" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import UnifiedInput from '../unified-input/UnifiedInput.vue';
import MermaidRenderer from '../rendering/MermaidRenderer.vue';
import CodeBlock from '../rendering/CodeBlock.vue';
import MarkMap from '../rendering/MarkMap.vue';
import { markdownToHtml } from '../../services/markdownService';
import { renderMermaidDynamically, renderCodeBlocks, renderMarkMaps } from '../../services/renderService';

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
const mermaidRenderer = ref(null);
const codeBlockRenderer = ref(null);
const markMapRenderer = ref(null);

watch(() => props.agentResponse, (newValue) => {
  console.log('[AgentInputModal] prop agentResponse updated:', newValue);
  // 如果响应完成，触发特殊组件渲染
  if (newValue && !props.isAgentResponding) {
    nextTick(() => {
      setTimeout(() => {
        renderSpecialComponents();
      }, 100);
    });
  }
});

watch(() => props.isAgentResponding, (newValue) => {
  console.log('[AgentInputModal] prop isAgentResponding updated:', newValue);
  // 响应完成后，延迟触发特殊组件渲染
  if (!newValue && props.agentResponse) {
    nextTick(() => {
      setTimeout(() => {
        renderSpecialComponents();
      }, 200);
    });
  }
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

// 渲染markdown内容
const renderMarkdown = (content) => {
  if (!content) return '';
  
  try {
    // 使用markdownService将markdown转换为HTML
    const htmlContent = markdownToHtml(content);
    
    // 延迟渲染特殊组件（在DOM更新后）
    nextTick(() => {
      renderSpecialComponents();
    });
    
    return htmlContent;
  } catch (error) {
    console.error('渲染markdown失败:', error);
    // 如果渲染失败，回退到纯文本显示
    return content.replace(/\n/g, '<br>');
  }
};

// 渲染特殊组件（Mermaid图表、代码块、思维导图）
const renderSpecialComponents = async () => {
  try {
    if (!modalRef.value) return;
    
    // 渲染代码块
    await renderCodeBlocks(true);
    
    // 渲染Mermaid图表
    setTimeout(() => {
      renderMermaidDynamically();
    }, 100);
    
    // 渲染思维导图
    setTimeout(() => {
      renderMarkMaps();
    }, 200);
    
    console.log('AgentInputModal: 特殊组件渲染完成');
  } catch (error) {
    console.error('渲染特殊组件失败:', error);
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
  max-width: 100%;
  overflow-wrap: break-word;
}

/* 打字内容样式 */
.typing-content {
  font-size: 14px;
  line-height: 1.5;
  color: #1f2937;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  max-width: 100%;
}

/* Markdown内容样式 */
.markdown-content {
  /* 基础文本样式 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #1f2937;
  white-space: normal;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
  overflow: hidden;
}

/* Markdown标题样式 */
.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin: 1em 0 0.5em 0;
  font-weight: 600;
  line-height: 1.25;
  color: #111827;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.3em; }
.markdown-content h3 { font-size: 1.1em; }
.markdown-content h4 { font-size: 1em; }

/* Markdown段落样式 */
.markdown-content p {
  margin: 0.8em 0;
  line-height: 1.6;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* Markdown列表样式 */
.markdown-content ul,
.markdown-content ol {
  margin: 0.8em 0;
  padding-left: 1.5em;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content li {
  margin: 0.2em 0;
  line-height: 1.5;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* Markdown链接样式 */
.markdown-content a {
  color: #3b82f6;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s ease;
}

.markdown-content a:hover {
  border-bottom-color: #3b82f6;
}

/* Markdown强调样式 */
.markdown-content strong {
  font-weight: 600;
  color: #111827;
}

.markdown-content em {
  font-style: italic;
  color: #374151;
}

/* Markdown引用样式 */
.markdown-content blockquote {
  margin: 1em 0;
  padding: 0 1em;
  color: #6b7280;
  border-left: 3px solid #d1d5db;
  background-color: #f9fafb;
  border-radius: 0 4px 4px 0;
}

/* Markdown内联代码样式 */
.markdown-content code:not(pre code) {
  background-color: #f3f4f6;
  color: #e11d48;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.875em;
  border: 1px solid #e5e7eb;
}

/* Markdown代码块样式 */
.markdown-content pre {
  background-color: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  margin: 1em 0;
  overflow-x: auto;
  font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.875em;
  line-height: 1.45;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content pre code {
  background: transparent;
  border: none;
  padding: 0;
  color: #1f2937;
  font-size: inherit;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* Markdown表格样式 */
.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  max-width: 100%;
  margin: 1em 0;
  font-size: 0.875em;
  overflow-x: auto;
  display: block;
  white-space: nowrap;
}

.markdown-content th,
.markdown-content td {
  border: 1px solid #d1d5db;
  padding: 0.5em 0.75em;
  text-align: left;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content tbody,
.markdown-content thead,
.markdown-content tr {
  display: table;
  width: 100%;
  table-layout: fixed;
}

.markdown-content th {
  background-color: #f9fafb;
  font-weight: 600;
  color: #374151;
}

.markdown-content tr:nth-child(even) {
  background-color: #f9fafb;
}

/* Mermaid图表容器样式 */
.markdown-content :deep(.mermaid-container) {
  margin: 1em 0;
  background-color: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
  overflow: auto;
}

.markdown-content :deep(.mermaid) {
  max-width: 100%;
  overflow: visible;
}

.markdown-content :deep(.mermaid svg) {
  max-width: 100%;
  height: auto;
}

/* 思维导图容器样式 */
.markdown-content :deep(.markmap-component-wrapper) {
  margin: 1em 0;
  background-color: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  min-height: 300px;
  overflow: hidden;
}

.markdown-content :deep(.markmap-svg) {
  width: 100%;
  min-height: 300px;
}

/* 代码块组件样式适配 */
.markdown-content :deep(.code-block-wrapper) {
  margin: 1em 0;
  position: relative;
}

.markdown-content :deep(.code-copy-button) {
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.markdown-content :deep(.code-block-wrapper:hover .code-copy-button) {
  opacity: 1;
}

/* 水平分割线样式 */
.markdown-content hr {
  border: none;
  height: 1px;
  background-color: #e5e7eb;
  margin: 1.5em 0;
}

/* 图片样式 */
.markdown-content img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 0.5em 0;
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