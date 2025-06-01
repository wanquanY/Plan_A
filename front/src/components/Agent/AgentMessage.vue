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
          :placeholder="getEditPlaceholder()"
          @keydown.ctrl.enter="$emit('save-edit', message, editImages)"
          @keydown.esc="$emit('cancel-edit', message)"
          ref="editTextarea"
        ></textarea>
        
        <!-- 编辑时的图片管理 -->
        <div v-if="editImages && editImages.length > 0" class="edit-images-section">
          <div class="edit-images-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21,15 16,10 5,21"/>
            </svg>
            <span>消息中的图片 ({{ editImages.length }})</span>
          </div>
          <div class="edit-images-list">
            <div v-for="(image, index) in editImages" :key="index" class="edit-image-item">
              <img :src="image.url" :alt="image.name || '图片'" class="edit-image-preview" />
              <div class="edit-image-info">
                <span class="edit-image-name">{{ image.name || `图片 ${index + 1}` }}</span>
                <span class="edit-image-size">{{ formatFileSize(image.size) }}</span>
              </div>
              <button @click="removeEditImage(index)" class="edit-image-remove" title="移除图片">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="edit-actions">
          <button @click="$emit('save-edit', message, editImages)" class="save-btn" :disabled="!message.editContent?.trim()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"></polyline>
            </svg>
            保存并重新执行
          </button>
          <button @click="$emit('save-edit-only', message, editImages)" class="save-only-btn" :disabled="!message.editContent?.trim()">
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
        
        <!-- 更新后的图片提示信息 -->
        <div v-if="editImages && editImages.length > 0" class="edit-image-notice">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
          <span>编辑后消息将包含 {{ editImages.length }} 张图片</span>
        </div>
      </div>
      
      <!-- 正常显示状态 -->
      <div v-else class="message-content">
        <!-- 解析用户消息内容，支持图片显示 -->
        <div v-if="parsedUserContent">
          <!-- 显示文本内容 -->
          <div v-if="parsedUserContent.text_content" class="user-text-content">
            {{ parsedUserContent.text_content }}
          </div>
          
          <!-- 显示图片内容 -->
          <div v-if="parsedUserContent.images && parsedUserContent.images.length > 0" class="user-images-content">
            <div v-for="(image, index) in parsedUserContent.images" :key="index" class="user-image-item">
              <img :src="image.url" :alt="image.name || '用户上传的图片'" class="user-image" />
            </div>
          </div>
        </div>
        
        <!-- 兼容原始文本格式 -->
        <div v-else class="user-text-content">
          {{ message.content }}
        </div>
        
        <!-- 用户消息操作按钮 -->
        <div class="message-actions">
          <button @click="$emit('start-edit', message)" class="action-btn" title="编辑消息">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
          <button @click="$emit('copy-message', getMessageTextContent())" class="action-btn" title="复制">
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
        <!-- 统一的内容容器，减少状态切换时的布局变化 -->
        <div class="content-container" :class="{ typing: message.isTyping, completed: !message.isTyping }">
          <!-- 如果有contentChunks，使用新的块结构 -->
          <div v-if="message.contentChunks && message.contentChunks.length > 0">
            <!-- 调试信息 -->
            <div v-if="false" style="font-size: 10px; color: #999; margin-bottom: 8px; border: 1px solid #ddd; padding: 4px;">
              调试(打字中): 内容块数量: {{ message.contentChunks.length }}, 
              类型: {{ message.contentChunks.map(c => `${c.type}(${c.tool_name || 'text'})`).join(', ') }}
            </div>
            <!-- 按时间顺序渲染所有内容块 -->
            <template v-for="(chunk, index) in getSortedContentChunks(message.contentChunks)" :key="`chunk-${chunk.type}-${chunk.tool_call_id || index}`">
              <!-- 文本块 - 内联显示，优化流式渲染的markdown处理 -->
              <span 
                v-if="chunk.type === 'text'" 
                v-html="renderTextContent(chunk.content, message.isTyping)" 
                class="text-chunk"
              ></span>
              <!-- 思考内容块 - 统一结构，根据状态显示不同内容 -->
              <div v-else-if="chunk.type === 'reasoning'" class="reasoning-chunk" :class="{ completed: !message.isTyping }">
                <div 
                  class="reasoning-header" 
                  :class="{ clickable: !message.isTyping }"
                  @click="!message.isTyping && toggleReasoningExpanded(index)"
                >
                  <svg class="thinking-icon" viewBox="0 0 24 24" width="14" height="14">
                    <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.58L19 8l-9 9z"/>
                  </svg>
                  <span>{{ message.isTyping ? '思考中...' : '深度思考过程' }}</span>
                  <!-- 只在完成状态显示展开图标 -->
                  <svg 
                    v-if="!message.isTyping"
                    class="expand-icon" 
                    :class="{ expanded: expandedChunks[getReasoningChunkId(chunk, index)] }" 
                    width="14" height="14" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    stroke-width="2"
                  >
                    <polyline points="6,9 12,15 18,9"></polyline>
                  </svg>
                </div>
                <!-- 思考内容：流式输出时直接显示，完成后根据展开状态显示 -->
                <div 
                  v-if="message.isTyping || expandedChunks[getReasoningChunkId(chunk, index)]" 
                  class="reasoning-content-inline"
                >
                  {{ chunk.content }}
                </div>
              </div>
              <!-- 工具状态块 - 独立成行，只在有有效工具名称时显示 -->
              <div v-else-if="chunk.type === 'tool_status' && chunk.tool_name" class="tool-chunk">
                <AgentToolCall 
                  :tool-name="chunk.tool_name || ''"
                  :status="chunk.status || (message.isTyping ? '' : 'completed')"
                  :tool-call-id="chunk.tool_call_id || ''"
                  :result="chunk.result"
                  :error="chunk.error"
                  :key="`tool-${chunk.tool_call_id || index}`"
                />
              </div>
            </template>
            <!-- 打字指示器 -->
            <span v-if="message.isTyping" class="typing-indicator">|</span>
          </div>
          <!-- 兼容旧的消息格式 -->
          <div v-else>
            <span v-html="renderTextContent(message.content, message.isTyping)"></span>
            <span v-if="message.isTyping" class="typing-indicator">|</span>
          </div>
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
import { nextTick, ref, computed, watch, reactive } from 'vue';
import AgentToolCall from './AgentToolCall.vue';
import { markdownToHtml, renderRealtimeMarkdown } from '../../services/markdownService';
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

// 编辑时的图片管理
const editImages = ref<any[]>([]);

// 监听消息编辑状态，初始化编辑图片
watch(() => props.message.isEditing, (isEditing) => {
  if (isEditing && props.message.type === 'user') {
    // 初始化编辑图片列表
    if (parsedUserContent.value && parsedUserContent.value.images) {
      editImages.value = [...parsedUserContent.value.images];
    } else {
      editImages.value = [];
    }
    console.log('初始化编辑图片列表:', editImages.value);
  } else {
    // 清空编辑图片列表
    editImages.value = [];
  }
});

// 移除编辑中的图片
const removeEditImage = (index: number) => {
  if (index >= 0 && index < editImages.value.length) {
    const removedImage = editImages.value.splice(index, 1)[0];
    console.log('移除图片:', removedImage.name || `图片 ${index + 1}`);
  }
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (!bytes) return '未知大小';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

// 解析用户消息内容
const parsedUserContent = computed(() => {
  if (props.message.type !== 'user') return null;
  
  try {
    const parsed = JSON.parse(props.message.content);
    if (parsed.type === 'user_message') {
      return parsed;
    }
  } catch (error) {
    // 如果解析失败，返回null，使用兼容模式
  }
  
  return null;
});

// 获取消息的文本内容（用于复制）
const getMessageTextContent = () => {
  if (props.message.type === 'user') {
    if (parsedUserContent.value) {
      return parsedUserContent.value.text_content || '';
    }
    return props.message.content;
  }
  return props.message.content;
};

// 全局展开状态管理 - 使用单例模式
const globalExpandedState = (() => {
  if (!window.__reasoningExpandedState) {
    window.__reasoningExpandedState = reactive({});
  }
  return window.__reasoningExpandedState;
})();

// 生成消息的唯一键值
const getMessageKey = () => {
  if (props.message.id) {
    return props.message.id;
  }
  // 对于当前消息，使用更唯一的键值，包含时间戳避免冲突
  const timestamp = props.message.timestamp?.getTime() || Date.now();
  return `current_${timestamp}`;
};

// 思考内容展开状态 - 使用全局状态
const expandedChunks = computed({
  get: () => {
    const messageKey = getMessageKey();
    return globalExpandedState[messageKey] || {};
  },
  set: (value) => {
    const messageKey = getMessageKey();
    globalExpandedState[messageKey] = value;
  }
});

// 判断是否是历史记录
const isHistoryMessage = computed(() => {
  return props.message.id && props.message.id.startsWith('history_');
});

// 生成思考内容的唯一标识
const getReasoningChunkId = (chunk: any, index: number) => {
  // 使用内容的哈希值+索引作为更稳定的标识
  // 这样即使消息对象重新创建，只要内容相同，ID就相同
  const contentHash = chunk.content ? 
    chunk.content.substring(0, 50).replace(/\s/g, '').substring(0, 20) : 
    '';
  return `reasoning_${index}_${contentHash}`;
};

// 防抖器
let initializationTimeout: number | null = null;

// 清理过时的状态
const cleanupOldStates = () => {
  const now = Date.now();
  const oneHourAgo = now - 60 * 60 * 1000; // 1小时前
  
  Object.keys(globalExpandedState).forEach(key => {
    // 清理1小时前的临时状态（current_开头的）
    if (key.startsWith('current_')) {
      const timestamp = parseInt(key.split('_')[1]);
      if (timestamp && timestamp < oneHourAgo) {
        delete globalExpandedState[key];
        console.log('[AgentMessage] 清理过时状态:', key);
      }
    }
  });
};

// 初始化思考内容的展开状态
const initializeExpandedState = () => {
  // 使用防抖，避免频繁调用
  if (initializationTimeout) {
    clearTimeout(initializationTimeout);
  }
  
  initializationTimeout = setTimeout(() => {
    const messageKey = getMessageKey();
    console.log('[AgentMessage] initializeExpandedState 被调用', {
      messageId: props.message.id,
      messageKey,
      isTyping: props.message.isTyping,
      chunksLength: props.message.contentChunks?.length || 0,
      existingExpandedState: Object.keys(expandedChunks.value),
      globalStateKeys: Object.keys(globalExpandedState)
    });
    
    // 清理过时的状态
    cleanupOldStates();
    
    if (!props.message.contentChunks) return;
    
    const sortedChunks = getSortedContentChunks(props.message.contentChunks);
    const currentExpandedState = { ...expandedChunks.value };
    const newExpandedState: Record<string, boolean> = { ...currentExpandedState };
    
    // 收集当前所有思考内容的ID，用于判断哪些是新增的
    const existingReasoningIds = new Set(Object.keys(currentExpandedState));
    
    let hasNewReasoning = false;
    
    sortedChunks.forEach((chunk, index) => {
      if (chunk.type === 'reasoning') {
        const chunkId = getReasoningChunkId(chunk, index);
        
        // 如果这个思考内容还没有展开状态，设置默认状态
        if (!existingReasoningIds.has(chunkId)) {
          // 新增的思考内容设置默认状态
          // 历史记录中的思考内容默认展开，当前对话中的默认折叠
          newExpandedState[chunkId] = isHistoryMessage.value;
          hasNewReasoning = true;
          console.log('[AgentMessage] 新增思考内容块', { 
            chunkId, 
            defaultExpanded: isHistoryMessage.value,
            messageKey 
          });
        }
        // 如果已经存在，保持原有状态不变
      }
    });
    
    // 只有在有新增思考内容时才更新状态
    if (hasNewReasoning || Object.keys(currentExpandedState).length === 0) {
      console.log('[AgentMessage] 更新展开状态', { 
        messageKey,
        old: Object.keys(currentExpandedState), 
        new: Object.keys(newExpandedState) 
      });
      expandedChunks.value = newExpandedState;
    } else {
      console.log('[AgentMessage] 无新增思考内容，保持现有状态', { messageKey });
    }
  }, 50); // 50ms防抖
};

// 监听message的contentChunks变化，重新初始化展开状态
watch(() => props.message.contentChunks, (newChunks, oldChunks) => {
  const messageKey = getMessageKey();
  console.log('[AgentMessage] contentChunks changed', {
    messageId: props.message.id,
    messageKey,
    isTyping: props.message.isTyping,
    newLength: newChunks?.length || 0,
    oldLength: oldChunks?.length || 0
  });
  
  // 避免在流式输出完成后的状态变化时重新初始化
  // 只有在真正有新内容时才初始化
  const reasoningChunksCount = newChunks?.filter(c => c.type === 'reasoning').length || 0;
  const oldReasoningChunksCount = oldChunks?.filter(c => c.type === 'reasoning').length || 0;
  
  // 获取当前消息的展开状态数量
  const currentExpandedStateCount = Object.keys(globalExpandedState[messageKey] || {}).length;
  
  // 满足以下条件之一才初始化：
  // 1. 有新的思考内容块
  // 2. 首次加载且没有展开状态
  // 3. 思考内容数量与展开状态数量不匹配（可能是状态丢失）
  if (reasoningChunksCount > oldReasoningChunksCount || 
      (currentExpandedStateCount === 0 && reasoningChunksCount > 0) ||
      (reasoningChunksCount > 0 && currentExpandedStateCount !== reasoningChunksCount)) {
    console.log('[AgentMessage] 检测到需要初始化的情况，触发初始化', {
      messageKey,
      reasoningChunksCount,
      oldReasoningChunksCount,
      currentExpandedStateCount
    });
    initializeExpandedState();
  } else {
    console.log('[AgentMessage] 无需初始化，跳过', {
      messageKey,
      reasoningChunksCount,
      oldReasoningChunksCount,
      currentExpandedStateCount
    });
  }
}, { immediate: true, deep: true });

// 监听message.id变化（切换消息时），重新初始化展开状态
watch(() => props.message.id, (newId, oldId) => {
  console.log('[AgentMessage] message.id changed', { newId, oldId });
  
  // 只有在ID真正变化时才初始化（避免初始化时的触发）
  if (oldId && newId !== oldId) {
    console.log('[AgentMessage] ID变化，触发初始化');
    initializeExpandedState();
  }
}, { immediate: false }); // 移除immediate，避免初始化时触发

// 切换思考内容展开状态
const toggleReasoningExpanded = (index: number) => {
  const sortedChunks = getSortedContentChunks(props.message.contentChunks || []);
  const chunk = sortedChunks[index];
  if (chunk && chunk.type === 'reasoning') {
    const chunkId = getReasoningChunkId(chunk, index);
    expandedChunks.value[chunkId] = !expandedChunks.value[chunkId];
  }
};

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
      console.log('完整Markdown渲染完成');
    });
    
    return htmlContent;
  } catch (error) {
    console.error('渲染markdown失败:', error);
    // 如果渲染失败，回退到纯文本显示
    return content.replace(/\n/g, '<br>');
  }
};

// 获取编辑时的占位符
const getEditPlaceholder = () => {
  if (parsedUserContent.value) {
    return parsedUserContent.value.text_content || '';
  }
  return '';
};

// 优化流式渲染的markdown处理
const renderTextContent = (content?: string, isTyping?: boolean) => {
  if (!content) return '';
  
  try {
    // 使用优化的实时markdown渲染器
    const htmlContent = renderRealtimeMarkdown(content, isTyping);
    
    // 延迟渲染特殊组件（在DOM更新后）
    nextTick(() => {
      // 这里可以添加特殊组件的渲染逻辑
      console.log('实时Markdown渲染完成, 内容长度:', content.length, '是否正在输入:', isTyping);
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

.user-message .user-text-content {
  margin-bottom: 8px;
}

.user-message .user-images-content {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.user-message .user-image-item {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-message .user-image {
  max-width: 200px;
  max-height: 200px;
  width: auto;
  height: auto;
  display: block;
  border-radius: 6px;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.user-message .user-image:hover {
  transform: scale(1.02);
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
  margin-left: 2px;
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

.edit-image-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  font-size: 12px;
  color: #0369a1;
}

.edit-image-notice svg {
  color: #0ea5e9;
  flex-shrink: 0;
}

.edit-images-section {
  margin-top: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
}

.edit-images-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  border-radius: 6px 6px 0 0;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

.edit-images-header svg {
  color: #6b7280;
  flex-shrink: 0;
}

.edit-images-list {
  padding: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.edit-image-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  margin-bottom: 4px;
  transition: all 0.2s ease;
}

.edit-image-item:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.edit-image-item:last-child {
  margin-bottom: 0;
}

.edit-image-preview {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.edit-image-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.edit-image-name {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edit-image-size {
  font-size: 11px;
  color: #6b7280;
}

.edit-image-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: #fee2e2;
  color: #dc2626;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.edit-image-remove:hover {
  background: #fecaca;
  color: #b91c1c;
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

/* 文本块样式 - 内联显示 */
.text-chunk {
  display: inline;
  line-height: 1.5;
}

/* 工具状态块样式 - 独立成行 */
.tool-chunk {
  display: block;
  margin: 8px 0;
}

/* 统一的内容容器样式 */
.content-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #1f2937;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  max-width: 100%;
  /* 添加平滑过渡 */
  transition: none;
}

.content-container.typing {
  /* 流式输出时的样式 */
  overflow: hidden;
}

.content-container.completed {
  /* 完成后的样式 - 应用markdown样式 */
  white-space: normal;
  overflow: visible;
}

/* Markdown样式应用到completed状态 */
.content-container.completed h1,
.content-container.completed h2,
.content-container.completed h3,
.content-container.completed h4,
.content-container.completed h5,
.content-container.completed h6 {
  margin: 1em 0 0.5em 0;
  font-weight: 600;
  line-height: 1.25;
  color: #111827;
}

.content-container.completed h1 { font-size: 1.5em; }
.content-container.completed h2 { font-size: 1.3em; }
.content-container.completed h3 { font-size: 1.1em; }
.content-container.completed h4 { font-size: 1em; }

.content-container.completed p {
  margin: 0.8em 0;
  line-height: 1.6;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container.completed ul,
.content-container.completed ol {
  margin: 0.8em 0;
  padding-left: 1.5em;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container.completed li {
  margin: 0.2em 0;
  line-height: 1.5;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container.completed a {
  color: #3b82f6;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s ease;
}

.content-container.completed a:hover {
  border-bottom-color: #3b82f6;
}

.content-container.completed strong {
  font-weight: 600;
  color: #111827;
}

.content-container.completed em {
  font-style: italic;
  color: #374151;
}

.content-container.completed code:not(pre code) {
  background-color: #f3f4f6;
  color: #e11d48;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.875em;
  border: 1px solid #e5e7eb;
}

.content-container.completed pre {
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

.content-container.completed pre code {
  background: transparent;
  border: none;
  padding: 0;
  color: #1f2937;
  font-size: inherit;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* 思考内容块样式 - 时序渲染版本 */
.reasoning-chunk {
  display: block;
  margin: 8px 0;
  background: #f8f9ff;
  border: 1px solid #e0e4ff;
  border-radius: 6px;
  overflow: hidden;
}

.reasoning-chunk .reasoning-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #f1f3ff;
  font-size: 12px;
  font-weight: 500;
  color: #4f46e5;
}

.reasoning-chunk.completed .reasoning-header {
  cursor: pointer;
  transition: background-color 0.2s ease;
  user-select: none;
  justify-content: space-between;
}

.reasoning-chunk.completed .reasoning-header:hover {
  background: #e8ecff;
}

.reasoning-chunk .thinking-icon {
  color: #4f46e5;
  flex-shrink: 0;
}

.reasoning-chunk.completed .expand-icon {
  color: #6b7280;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.reasoning-chunk.completed .expand-icon.expanded {
  transform: rotate(180deg);
}

.reasoning-content-inline {
  padding: 8px 10px;
  background: #ffffff;
  border-top: 1px solid #e0e4ff;
  font-size: 13px;
  line-height: 1.4;
  color: #374151;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

/* 实时markdown渲染样式优化 */
.content-container h1,
.content-container h2,
.content-container h3,
.content-container h4,
.content-container h5,
.content-container h6 {
  margin: 0.8em 0 0.4em 0;
  font-weight: 600;
  line-height: 1.25;
  color: #111827;
}

.content-container h1 { font-size: 1.5em; }
.content-container h2 { font-size: 1.3em; }
.content-container h3 { font-size: 1.1em; }
.content-container h4 { font-size: 1em; }

.content-container p {
  margin: 0.5em 0;
  line-height: 1.6;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container ul,
.content-container ol {
  margin: 0.5em 0;
  padding-left: 1.5em;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container li {
  margin: 0.1em 0;
  line-height: 1.5;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.content-container strong {
  font-weight: 600;
  color: #1f2937;
}

.content-container em {
  font-style: italic;
  color: #374151;
}

.content-container code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  font-size: 0.875em;
  background-color: #f3f4f6;
  color: #e53e3e;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  border: 1px solid #e5e7eb;
}

.content-container a {
  color: #3b82f6;
  text-decoration: none;
}

.content-container a:hover {
  text-decoration: underline;
}

/* 流式渲染时的平滑过渡 */
.content-container.typing {
  transition: none;
}

.content-container.typing h1,
.content-container.typing h2,
.content-container.typing h3,
.content-container.typing h4,
.content-container.typing h5,
.content-container.typing h6,
.content-container.typing p,
.content-container.typing ul,
.content-container.typing ol,
.content-container.typing li {
  transition: none;
}
</style> 