<template>
  <div v-if="visible" class="agent-sidebar">
    <!-- 侧边栏头部 -->
    <div class="sidebar-header">
      <h3 class="sidebar-title">AI助手</h3>
      <button class="close-button" @click="close" title="关闭侧边栏">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <!-- 聊天消息区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        <div class="empty-icon">💬</div>
        <p>开始与AI助手对话吧</p>
      </div>
      
      <!-- 消息列表 -->
      <div 
        v-for="(message, index) in messages" 
        :key="message.id || index"
        class="message-wrapper"
        :class="message.type"
      >
        <!-- 用户消息 -->
        <div v-if="message.type === 'user'" class="message user-message">
          <div class="message-header">
            <span class="message-label">我</span>
            <div class="message-time">
              {{ formatTime(message.timestamp) }}
            </div>
          </div>
          <div class="message-content">
            {{ message.content }}
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
            {{ message.content }}
            <!-- 打字指示器 -->
            <span v-if="message.isTyping" class="typing-indicator">|</span>
          </div>
          
          <!-- 操作按钮 -->
          <div v-if="!message.isTyping && message.content" class="message-actions">
            <button @click="insertToEditor(message.content)" class="action-btn" title="插入文档">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 10L5 6M5 6L9 2M5 6h11a4 4 0 0 1 4 4v4"></path>
              </svg>
            </button>
            <button @click="copyMessage(message.content)" class="action-btn" title="复制">
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
    </div>

    <!-- 输入区域 -->
    <div class="input-section">
      <UnifiedInput 
        @send="handleSendMessage"
        @select-agent="handleSelectAgent"
        @upload-file="handleUploadFile"
        ref="unifiedInputRef"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import UnifiedInput from './unified-input/UnifiedInput.vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
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
  },
  conversationHistory: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history', 'adjust-tone']);

// 状态变量
const unifiedInputRef = ref(null);
const messagesContainer = ref(null);
const messages = ref([]);
const currentAgent = ref(null);

// 从会话历史初始化聊天记录
const initializeFromHistory = () => {
  console.log('初始化聊天记录，历史记录数量:', props.conversationHistory?.length || 0);
  
  // 如果当前正在响应，不要重新初始化，避免覆盖正在进行的对话
  if (props.isAgentResponding) {
    console.log('当前正在响应中，跳过历史记录初始化');
    return;
  }
  
  if (!props.conversationHistory || props.conversationHistory.length === 0) {
    // 只有在没有当前消息时才清空
    if (messages.value.length === 0 || !messages.value.some(msg => msg.type === 'agent' && msg.isTyping)) {
      messages.value = [];
    }
    return;
  }

  const newMessages = [];
  
  props.conversationHistory.forEach((conversation, index) => {
    // 添加用户消息
    if (conversation.user) {
      newMessages.push({
        id: `history_${index}_user`,
        type: 'user',
        content: conversation.user,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index) * 60000), // 模拟时间间隔
        agent: currentAgent.value
      });
    }
    
    // 添加AI消息
    if (conversation.agent) {
      newMessages.push({
        id: `history_${index}_agent`,
        type: 'agent',
        content: conversation.agent,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index - 0.5) * 60000), // 稍后的时间
        agent: currentAgent.value,
        isTyping: false
      });
    }
  });
  
  // 检查是否有正在进行的消息（正在输入但还没完成的）
  const activeMessages = messages.value.filter(msg => 
    msg.type === 'agent' && msg.isTyping && msg.content !== ''
  );
  
  // 如果有正在进行的消息，合并到历史消息后面；否则直接使用历史消息
  if (activeMessages.length > 0) {
    messages.value = [...newMessages, ...activeMessages];
    console.log('保留正在进行的消息，总消息数量:', messages.value.length);
  } else {
    // 没有正在进行的消息，直接使用历史消息（避免重复）
    messages.value = newMessages;
    console.log('使用历史消息，总消息数量:', messages.value.length);
  }
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

// 添加测试数据的功能（用于调试）
const addTestMessages = () => {
  const testMessages = [
    {
      id: 'test_1_user',
      type: 'user',
      content: '你好，请帮我写一篇关于人工智能的文章',
      timestamp: new Date(Date.now() - 300000), // 5分钟前
      agent: { name: '小助理', avatar_url: 'https://placehold.co/32x32?text=AI' }
    },
    {
      id: 'test_1_agent',
      type: 'agent',
      content: '您好！我很乐意帮您写一篇关于人工智能的文章。以下是一篇简洁而全面的人工智能介绍：\n\n# 人工智能：塑造未来的技术\n\n人工智能（AI）已经从科幻概念发展为现实中的强大技术。它正在改变我们的生活方式、工作方式以及与世界互动的方式。\n\n## 什么是人工智能？\n\n人工智能是指机器模拟人类智能的能力，包括学习、推理、感知和决策制定。',
      timestamp: new Date(Date.now() - 280000), // 4分40秒前  
      agent: { name: '小助理', avatar_url: 'https://placehold.co/32x32?text=AI' },
      isTyping: false
    },
    {
      id: 'test_2_user',
      type: 'user',
      content: '请继续完善这篇文章，添加更多关于机器学习的内容',
      timestamp: new Date(Date.now() - 120000), // 2分钟前
      agent: { name: '小助理', avatar_url: 'https://placehold.co/32x32?text=AI' }
    },
    {
      id: 'test_2_agent',
      type: 'agent',
      content: '当然！让我为您继续完善这篇文章，特别是机器学习部分：\n\n## 机器学习：AI的核心驱动力\n\n机器学习是人工智能的一个重要分支，它使计算机能够从数据中学习并做出预测或决策，而无需明确编程。\n\n### 主要类型：\n\n1. **监督学习**：使用标记数据训练模型\n2. **无监督学习**：从未标记数据中发现模式\n3. **强化学习**：通过与环境交互学习最优策略',
      timestamp: new Date(Date.now() - 60000), // 1分钟前
      agent: { name: '小助理', avatar_url: 'https://placehold.co/32x32?text=AI' },
      isTyping: false
    }
  ];
  
  messages.value = testMessages;
  console.log('添加了测试消息，数量:', messages.value.length);
  
  nextTick(() => {
    scrollToBottom();
  });
};

// 发送消息
const handleSendMessage = (messageData) => {
  // 添加用户消息到聊天记录
  const userMessage = {
    id: Date.now() + '_user',
    type: 'user',
    content: messageData.content,
    timestamp: new Date(),
    agent: messageData.agent
  };
  messages.value.push(userMessage);

  // 添加加载消息
  const loadingMessage = {
    id: Date.now() + '_loading',
    type: 'loading',
    agent: messageData.agent,
    timestamp: new Date()
  };
  messages.value.push(loadingMessage);

  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });

  // 发送给父组件
  emit('send', messageData); 
};

// 选择Agent
const handleSelectAgent = (agent) => {
  currentAgent.value = agent;
  emit('select-agent', agent);
};

// 上传文件
const handleUploadFile = () => {
  console.log('上传文件功能待实现');
};

// 插入到编辑器
const insertToEditor = (content) => {
  emit('request-insert', content);
};

// 复制消息
const copyMessage = async (content) => {
  try {
    await navigator.clipboard.writeText(content);
    console.log('消息已复制到剪贴板');
  } catch (err) {
    console.error('复制失败:', err);
  }
};

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInHours = (now - date) / (1000 * 60 * 60);
  
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

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 关闭侧边栏
const close = () => {
  emit('close');
};

// 监听AI响应变化
watch(() => props.agentResponse, (newResponse) => {
  if (newResponse) {
    // 移除加载消息
    const loadingIndex = messages.value.findIndex(msg => msg.type === 'loading');
    if (loadingIndex !== -1) {
      messages.value.splice(loadingIndex, 1);
    }

    // 添加或更新AI响应消息
    const existingAgentMsgIndex = messages.value.findIndex(msg => 
      msg.type === 'agent' && msg.isTyping
    );

    if (existingAgentMsgIndex !== -1) {
      // 更新现有消息
      messages.value[existingAgentMsgIndex].content = newResponse;
      messages.value[existingAgentMsgIndex].isTyping = props.isAgentResponding;
    } else {
      // 添加新的AI消息
      const agentMessage = {
        id: Date.now() + '_agent',
        type: 'agent',
        content: newResponse,
        timestamp: new Date(),
        agent: currentAgent.value,
        isTyping: props.isAgentResponding
      };
      messages.value.push(agentMessage);
    }

    // 滚动到底部
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 监听响应状态变化
watch(() => props.isAgentResponding, (isResponding) => {
  if (!isResponding) {
    // 响应完成，移除打字指示器
    const typingMsgIndex = messages.value.findIndex(msg => 
      msg.type === 'agent' && msg.isTyping
    );
    if (typingMsgIndex !== -1) {
      messages.value[typingMsgIndex].isTyping = false;
    }
  }
});

// Watch 侧边栏显示状态，自动聚焦
watch(() => props.visible, (visible) => {
  if (visible) {
    nextTick(() => {
      unifiedInputRef.value?.focus();
      scrollToBottom();
    });
  }
});

// 监听会话历史变化
watch(() => props.conversationHistory, (newHistory) => {
  console.log('会话历史发生变化:', newHistory?.length || 0);
  initializeFromHistory();
}, { deep: true, immediate: true });

// 组件挂载时初始化
onMounted(() => {
  // 如果没有历史记录，添加一些测试数据（仅用于开发调试）
  if (!props.conversationHistory || props.conversationHistory.length === 0) {
    console.log('没有会话历史，添加测试聊天记录');
    addTestMessages();
  } else {
    initializeFromHistory();
  }
  
  nextTick(() => {
    unifiedInputRef.value?.focus();
  });
});
</script>

<style scoped>
.agent-sidebar {
  width: 400px;
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e5e7eb;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.close-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: #e5e7eb;
  color: #374151;
}

.input-section {
  padding: 20px;
  background: #ffffff;
}

/* 聊天消息区域 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-chat p {
  font-size: 14px;
  margin: 0;
}

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
  white-space: pre-wrap;
  margin-bottom: 8px;
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

/* 滚动条美化 */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.25);
}
</style> 