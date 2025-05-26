<template>
  <div class="message-wrapper" :class="message.type">
    <!-- 用户消息 -->
    <div v-if="message.type === 'user'" class="message user-message">
      <div class="message-header">
        <span class="message-label">我</span>
        <div class="message-time">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
      
      <!-- 编辑状态 -->
      <div v-if="message.isEditing" class="message-content editing">
        <textarea 
          v-model="message.editContent"
          class="edit-textarea"
          :placeholder="message.content"
          @keydown.ctrl.enter="$emit('save-edit', message)"
          @keydown.esc="$emit('cancel-edit', message)"
          ref="editTextarea"
        ></textarea>
        <div class="edit-actions">
          <button @click="$emit('save-edit', message)" class="save-btn" :disabled="!message.editContent?.trim()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"></polyline>
            </svg>
            保存并重新执行
          </button>
          <button @click="$emit('save-edit-only', message)" class="save-only-btn" :disabled="!message.editContent?.trim()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17,21 17,13 7,13 7,21"></polyline>
              <polyline points="7,3 7,8 15,8"></polyline>
            </svg>
            仅保存
          </button>
          <button @click="$emit('cancel-edit', message)" class="cancel-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
            取消
          </button>
        </div>
      </div>
      
      <!-- 正常显示状态 -->
      <div v-else class="message-content">
        {{ message.content }}
        
        <!-- 用户消息操作按钮 -->
        <div class="message-actions">
          <button @click="$emit('start-edit', message)" class="action-btn" title="编辑消息">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
          <button @click="$emit('copy-message', message.content)" class="action-btn" title="复制">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- AI消息 -->
    <div v-else-if="message.type === 'agent'" class="message agent-message">
      <div class="message-header">
        <span class="message-label">{{ message.agent?.name || 'AI助手' }}</span>
        <div class="message-time">
          {{ formatTime(message.timestamp) }}
        </div>
      </div>
      
      <div class="message-content">
        <!-- 渲染混合内容（文本 + 工具状态按流式顺序） -->
        <div v-if="message.isTyping" class="typing-content">
          <!-- 如果有contentChunks，使用新的块结构 -->
          <div v-if="message.contentChunks && message.contentChunks.length > 0">
            <!-- 按时间顺序渲染所有内容块 -->
            <div v-for="(chunk, index) in getSortedContentChunks(message.contentChunks)" :key="`chunk-${chunk.type}-${chunk.tool_call_id || index}`" class="content-chunk">
              <!-- 文本块 -->
              <span v-if="chunk.type === 'text'" v-html="formatTextWithBreaks(chunk.content)"></span>
              <!-- 工具状态块 -->
              <AgentToolCall 
                v-else-if="chunk.type === 'tool_status'"
                :tool-name="chunk.tool_name || ''"
                :status="chunk.status || ''"
                :tool-call-id="chunk.tool_call_id || ''"
                :result="chunk.result"
                :error="chunk.error"
              />
            </div>
          </div>
          <!-- 兼容旧的消息格式 -->
          <div v-else>
            <span v-html="formatTextWithBreaks(message.content)"></span>
          </div>
          <span v-if="message.isTyping" class="typing-indicator">|</span>
        </div>
        
        <!-- 完成后显示最终内容 -->
        <div v-else class="markdown-content">
          <!-- 如果有contentChunks，使用新的块结构 -->
          <div v-if="message.contentChunks && message.contentChunks.length > 0">
            <!-- 按时间顺序渲染所有内容块 -->
            <div v-for="(chunk, index) in getSortedContentChunks(message.contentChunks)" :key="`chunk-${chunk.type}-${chunk.tool_call_id || index}`" class="content-chunk">
              <!-- 文本块 -->
              <div v-if="chunk.type === 'text'" v-html="renderMarkdown(chunk.content)"></div>
              <!-- 工具状态块 -->
              <AgentToolCall 
                v-else-if="chunk.type === 'tool_status'"
                :tool-name="chunk.tool_name || ''"
                :status="'completed'"
                :tool-call-id="chunk.tool_call_id || ''"
                :result="chunk.result"
                :error="chunk.error"
              />
            </div>
          </div>
          <!-- 兼容旧的消息格式（历史消息） -->
          <div v-else v-html="renderMarkdown(message.content)"></div>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div v-if="!message.isTyping && message.content" class="message-actions">
        <button @click="$emit('insert-to-editor', message.content)" class="action-btn" title="插入文档">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 10L5 6M5 6L9 2M5 6h11a4 4 0 0 1 4 4v4"></path>
          </svg>
        </button>
        <button @click="$emit('copy-message', message.content)" class="action-btn" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 加载消息 -->
    <div v-else-if="message.type === 'loading'" class="message loading-message">
      <div class="loading-indicator">
        <div class="loading-spinner"></div>
        <span>正在思考中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue';
import AgentToolCall from './AgentToolCall.vue';
import { markdownToHtml } from '../../services/markdownService';
import { useStreamingResponse } from '../../composables/useStreamingResponse';
import type { ChatMessage } from '../../composables/useAgentChat';

interface Props {
  message: ChatMessage;
}

const props = defineProps<Props>();

const emit = defineEmits([
  'start-edit',
  'save-edit', 
  'save-edit-only',
  'cancel-edit',
  'copy-message',
  'insert-to-editor'
]);

const { getSortedContentChunks } = useStreamingResponse();

// 格式化时间
const formatTime = (timestamp: Date) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
  
  if (diffInHours < 24) {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  } else {
    return date.toLocaleDateString('zh-CN', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

// 格式化文本，保持换行
const formatTextWithBreaks = (text?: string) => {
  if (!text) return '';
  return text.replace(/\n/g, '<br>');
};

// 渲染markdown内容
const renderMarkdown = (content?: string) => {
  if (!content) return '';
  
  try {
    const htmlContent = markdownToHtml(content);
    
    // 延迟渲染特殊组件（在DOM更新后）
    nextTick(() => {
      // 这里可以添加特殊组件的渲染逻辑
      console.log('Markdown渲染完成');
    });
    
    return htmlContent;
  } catch (error) {
    console.error('渲染markdown失败:', error);
    // 如果渲染失败，回退到纯文本显示
    return content.replace(/\n/g, '<br>');
  }
};
</script>

<style scoped>
/* 消息之间的时间分隔 */
.message-wrapper + .message-wrapper {
  margin-top: 2px;
}

.message-wrapper.user + .message-wrapper.agent,
.message-wrapper.agent + .message-wrapper.user {
  margin-top: 16px;
}

/* 消息包装器 */
.message-wrapper {
  display: flex;
  width: 100%;
}

.message-wrapper.user {
  justify-content: flex-start;
  width: 100%;
}

.message-wrapper.agent,
.message-wrapper.loading {
  justify-content: flex-start;
  width: 100%;
}

.message-wrapper.agent .agent-message,
.message-wrapper.loading .loading-message,
.message-wrapper.user .user-message {
  width: 100%;
}

/* 用户消息 */
.user-message {
  max-width: 100%;
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 16px;
  position: relative;
}

.user-message .message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.user-message .message-label {
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
}

.user-message .message-content {
  font-size: 14px;
  line-height: 1.4;
  word-wrap: break-word;
  margin-bottom: 4px;
  font-weight: 500;
}

.user-message .message-time {
  font-size: 11px;
  opacity: 0.7;
  text-align: left;
  color: #6b7280;
}

/* AI消息 */
.agent-message,
.loading-message {
  max-width: 100%;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  position: relative;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.agent-message .message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.agent-message .message-label {
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
}

.agent-message .message-content {
  font-size: 14px;
  line-height: 1.5;
  color: #1f2937;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  margin-bottom: 8px;
  max-width: 100%;
  overflow: hidden;
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

.agent-message .message-time {
  font-size: 11px;
  color: #9ca3af;
}

/* 打字指示器 */
.typing-indicator {
  color: #6366f1;
  font-weight: bold;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 加载指示器 */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
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

/* 消息操作按钮 */
.message-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
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

.action-btn:hover {
  background: #e5e7eb;
  color: #374151;
  opacity: 1;
}

/* 编辑消息样式 */
.message-content.editing {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
  margin-bottom: 8px;
}

.edit-textarea {
  width: 100%;
  min-height: 60px;
  max-height: 150px;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.4;
  resize: vertical;
  outline: none;
  background: #ffffff;
  transition: border-color 0.2s ease;
}

.edit-textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.save-btn,
.save-only-btn,
.cancel-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.save-btn {
  background: #3b82f6;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #2563eb;
}

.save-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.save-only-btn {
  background: #10b981;
  color: white;
}

.save-only-btn:hover:not(:disabled) {
  background: #059669;
}

.save-only-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.cancel-btn {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.cancel-btn:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

/* 内容块样式 */
.content-chunk {
  display: block;
  margin: 0;
}

.content-chunk:not(:last-child) {
  margin-bottom: 4px;
}

/* 文本内容块样式 */
.content-chunk span {
  display: inline;
  line-height: 1.5;
}

/* Markdown内容样式 */
.markdown-content {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #1f2937;
  white-space: normal;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
  overflow: hidden;
}

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
}

.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.3em; }
.markdown-content h3 { font-size: 1.1em; }
.markdown-content h4 { font-size: 1em; }

.markdown-content p {
  margin: 0.8em 0;
  line-height: 1.6;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

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

.markdown-content a {
  color: #3b82f6;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s ease;
}

.markdown-content a:hover {
  border-bottom-color: #3b82f6;
}

.markdown-content strong {
  font-weight: 600;
  color: #111827;
}

.markdown-content em {
  font-style: italic;
  color: #374151;
}

.markdown-content code:not(pre code) {
  background-color: #f3f4f6;
  color: #e11d48;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.875em;
  border: 1px solid #e5e7eb;
}

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
</style> 