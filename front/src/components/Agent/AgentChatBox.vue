<template>
  <div class="agent-chat-box">
    <div class="message-container">
        <div 
          class="message-content" 
          contenteditable="true" 
          ref="messageInput"
          @input="handleInput"
          @keydown.enter.prevent="sendMessage"
          placeholder="发送消息给Agent..."
        ></div>
      <button 
        v-if="messageText.trim().length > 0" 
        class="send-button" 
        @click="sendMessage"
      >
        <span>发送</span>
      </button>
    </div>
    
    <!-- 工具调用状态显示 -->
    <ToolCallsStatus :tool-calls="toolCallsStatus" />
    
    <div v-if="chatState.loading" class="agent-response loading">
      <div class="avatar">
        <img :src="agent.avatar_url" alt="Agent Avatar" />
      </div>
      <div class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
    <div v-if="chatState.response" class="agent-response">
      <div class="avatar">
        <img :src="agent.avatar_url" alt="Agent Avatar" />
      </div>
      <div class="response-text" v-html="formatResponseText(chatState.response)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue';
import type { Agent } from '../../services/agent';
import chatService from '../../services/chat';
import ToolCallsStatus from './ToolCallsStatus.vue';
import { useToolCallsStatus } from '../../composables/useToolCallsStatus';

const props = defineProps({
  agent: {
    type: Object as () => Agent,
    required: true
  },
  initialPrompt: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['chat-complete', 'chat-start']);

const messageInput = ref<HTMLElement | null>(null);
const messageText = ref('');
const chatController = ref<AbortController | null>(null);

// 使用工具调用状态管理
const {
  toolCalls: toolCallsStatus,
  handleToolStatus,
  clearToolCalls
} = useToolCallsStatus();

const chatState = reactive({
  loading: false,
  response: '',
  conversationId: 0
});

// 处理输入
const handleInput = (e: Event) => {
  if (messageInput.value) {
    messageText.value = messageInput.value.innerText || '';
  }
};

// 发送消息
const sendMessage = async () => {
  if (!messageText.value.trim() || chatState.loading) return;
  
  try {
    emit('chat-start');
    chatState.loading = true;
    
    // 清空之前的工具调用状态
    clearToolCalls();
    
    // 保存用户输入的文本并清空输入框
    const userMessage = messageText.value.trim();
    messageText.value = '';
    if (messageInput.value) {
      messageInput.value.innerText = '';
    }
    
    // 启动与Agent的聊天
    chatController.value = chatService.chatWithAgent(
      {
        content: userMessage,
        agent_id: props.agent.id,
        conversation_id: chatState.conversationId || undefined
      },
      (content, done, conversationId, toolStatus) => {
        // 处理工具状态更新
        if (toolStatus) {
          handleToolStatus(toolStatus);
        }
        
        // 更新聊天状态
        chatState.response = content;
        chatState.conversationId = conversationId;
        
        if (done) {
          chatState.loading = false;
          chatController.value = null;
          emit('chat-complete', {
            response: content,
            conversationId: conversationId
          });
        }
      }
    );
  } catch (error) {
    console.error('发送消息失败:', error);
    chatState.loading = false;
    clearToolCalls();
  }
};

// 格式化响应文本，处理换行和特殊字符
const formatResponseText = (text: string) => {
  // 将换行符转换为<br>标签
  return text.replace(/\n/g, '<br>')
    // 保留连续空格
    .replace(/ {2}/g, '&nbsp;&nbsp;')
    // 将emoji转换为安全的HTML实体
    .replace(/[\u{1F300}-\u{1F6FF}]/gu, (match) => {
      return match;
    });
};

// 取消聊天请求
const cancelChat = () => {
  if (chatController.value) {
    chatController.value.abort();
    chatController.value = null;
    chatState.loading = false;
  }
};

// 组件挂载后设置初始提示文本
onMounted(() => {
  if (messageInput.value && props.initialPrompt) {
    messageInput.value.innerText = props.initialPrompt;
    messageText.value = props.initialPrompt;
  }
});

// 组件卸载前取消可能存在的聊天请求
onBeforeUnmount(() => {
  cancelChat();
});

// 暴露方法供父组件调用
defineExpose({
  sendMessage,
  cancelChat
});
</script>

<style scoped>
.agent-chat-box {
  margin: 8px 0;
  width: 100%;
}

.message-container {
  display: flex;
  align-items: flex-end;
  margin-bottom: 8px;
  background-color: #f5f5f7;
  border-radius: 12px;
  padding: 8px 12px;
  position: relative;
}

.message-content {
  flex: 1;
  min-height: 24px;
  outline: none;
  line-height: 1.5;
  word-break: break-word;
}

.message-content:empty:before {
  content: attr(placeholder);
  color: #999;
  pointer-events: none;
  position: absolute;
}

.send-button {
  margin-left: 8px;
  background-color: #1677ff;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 14px;
}

.send-button:hover {
  background-color: #0958d9;
}

.agent-response {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 8px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.response-text {
  flex: 1;
  line-height: 1.6;
  color: #333;
  font-size: 14px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background-color: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% { 
    transform: scale(0);
    opacity: 0.5;
  }
  40% { 
    transform: scale(1);
    opacity: 1;
  }
}
</style> 