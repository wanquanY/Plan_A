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
            <!-- 正在打字时显示简单文本和打字指示器 -->
            <div v-if="message.isTyping" class="typing-content">
              <span>{{ message.content }}</span>
              <span class="typing-indicator">|</span>
            </div>
            <!-- 打字完成后显示渲染的markdown内容 -->
            <div v-else class="markdown-content" v-html="renderMarkdown(message.content)"></div>
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

    <!-- 渲染组件（隐藏） -->
    <div style="display: none;">
      <MermaidRenderer ref="mermaidRenderer" />
      <CodeBlock ref="codeBlockRenderer" :code="''" :language="'text'" />
      <MarkMap ref="markMapRenderer" :content="''" />
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
const mermaidRenderer = ref(null);
const codeBlockRenderer = ref(null);
const markMapRenderer = ref(null);

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
    if (!messagesContainer.value) return;
    
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
    
    console.log('AgentSidebar: 特殊组件渲染完成');
  } catch (error) {
    console.error('渲染特殊组件失败:', error);
  }
};

// 从会话历史初始化聊天记录
const initializeFromHistory = (forceUpdate = false) => {
  console.log('=== AgentSidebar: 初始化聊天记录 ===');
  console.log('历史记录数量:', props.conversationHistory?.length || 0);
  console.log('历史记录内容:', props.conversationHistory);
  console.log('forceUpdate:', forceUpdate);
  console.log('当前isAgentResponding:', props.isAgentResponding);
  console.log('当前messages数量:', messages.value.length);
  
  // 如果当前正在响应且不是强制更新，不要重新初始化，避免覆盖正在进行的对话
  if (props.isAgentResponding && !forceUpdate) {
    console.log('当前正在响应中，跳过历史记录初始化');
    return;
  }
  
  if (!props.conversationHistory || props.conversationHistory.length === 0) {
    console.log('历史记录为空，清空messages');
    // 只有在没有当前消息时才清空，或者是强制更新
    if (messages.value.length === 0 || !messages.value.some(msg => msg.type === 'agent' && msg.isTyping) || forceUpdate) {
      messages.value = [];
      console.log('已清空messages');
    }
    return;
  }

  console.log('开始处理历史记录，条数:', props.conversationHistory.length);
  const newMessages = [];
  
  props.conversationHistory.forEach((conversation, index) => {
    console.log(`处理第${index}条历史记录:`, conversation);
    
    // 添加用户消息
    if (conversation.user) {
      const userMsg = {
        id: `history_${index}_user`,
        type: 'user',
        content: conversation.user,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index) * 60000), // 模拟时间间隔
        agent: currentAgent.value
      };
      newMessages.push(userMsg);
      console.log('添加用户消息:', userMsg);
    }
    
    // 添加AI消息
    if (conversation.agent) {
      const agentMsg = {
        id: `history_${index}_agent`,
        type: 'agent',
        content: conversation.agent,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index - 0.5) * 60000), // 稍后的时间
        agent: currentAgent.value,
        isTyping: false
      };
      newMessages.push(agentMsg);
      console.log('添加AI消息:', agentMsg);
    }
  });
  
  console.log('生成的新消息数组，长度:', newMessages.length);
  console.log('新消息详情:', newMessages);
  
  // 如果是强制更新，直接使用历史消息；否则检查是否有正在进行的消息
  if (forceUpdate) {
    messages.value = newMessages;
    console.log('强制更新使用历史消息，总消息数量:', messages.value.length);
  } else {
    // 检查是否有正在进行的消息（正在输入但还没完成的）
    const activeMessages = messages.value.filter(msg => 
      msg.type === 'agent' && msg.isTyping && msg.content !== ''
    );
    
    console.log('正在进行的消息数量:', activeMessages.length);
    
    // 如果有正在进行的消息，合并到历史消息后面；否则直接使用历史消息
    if (activeMessages.length > 0) {
      messages.value = [...newMessages, ...activeMessages];
      console.log('保留正在进行的消息，总消息数量:', messages.value.length);
    } else {
      // 没有正在进行的消息，直接使用历史消息（避免重复）
      messages.value = newMessages;
      console.log('使用历史消息，总消息数量:', messages.value.length);
    }
  }
  
  console.log('最终messages状态:', messages.value);
  
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
      // 如果响应完成，触发特殊组件渲染
      if (!props.isAgentResponding) {
        setTimeout(() => {
          renderSpecialComponents();
        }, 100);
      }
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
    
    // 响应完成后，延迟触发特殊组件渲染
    nextTick(() => {
      setTimeout(() => {
        renderSpecialComponents();
      }, 200);
    });
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
watch(() => props.conversationHistory, (newHistory, oldHistory) => {
  console.log('=== AgentSidebar: 会话历史发生变化 ===');
  console.log('新历史记录数量:', newHistory?.length || 0);
  console.log('新历史记录内容:', newHistory);
  console.log('旧历史记录数量:', oldHistory?.length || 0);
  console.log('旧历史记录内容:', oldHistory);
  
  // 检测是否是笔记切换：历史记录完全不同或从有记录变为无记录
  const isNoteSwitching = (
    (!oldHistory || oldHistory.length === 0) && newHistory && newHistory.length > 0
  ) || (
    oldHistory && oldHistory.length > 0 && (!newHistory || newHistory.length === 0)
  ) || (
    oldHistory && newHistory && 
    oldHistory.length !== newHistory.length &&
    // 检查内容是否完全不同（至少有一个对话的内容不同）
    (oldHistory.length === 0 || newHistory.length === 0 || 
     oldHistory[0]?.user !== newHistory[0]?.user ||
     oldHistory[0]?.agent !== newHistory[0]?.agent)
  );
  
  console.log('是否检测到笔记切换:', isNoteSwitching);
  
  if (isNoteSwitching) {
    console.log('检测到笔记切换，强制更新历史记录');
    initializeFromHistory(true); // 强制更新
  } else {
    console.log('正常历史记录变化，常规更新');
    initializeFromHistory(); // 正常更新
  }
}, { deep: true, immediate: true });

// 组件挂载时初始化
onMounted(() => {
  // 初始化历史记录（如果有的话）
  if (props.conversationHistory && props.conversationHistory.length > 0) {
    console.log('组件挂载时初始化历史记录');
    initializeFromHistory();
  } else {
    console.log('组件挂载时无历史记录，保持空状态');
    messages.value = [];
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

/* 确保在打字时不影响markdown渲染 */
.markdown-content .typing-indicator {
  display: inline;
  margin-left: 0.5em;
}
</style> 