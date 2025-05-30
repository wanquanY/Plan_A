<template>
  <div class="chat-messages" ref="messagesContainer">
    <div v-if="messages.length === 0" class="empty-chat">
      <div class="empty-icon">💬</div>
      <p>开始与AI助手对话吧</p>
    </div>
    
    <!-- 消息列表 -->
    <AgentMessage
      v-for="(message, index) in messages"
      :key="message.id || index"
      :message="message"
      @start-edit="$emit('start-edit', $event)"
      @save-edit="(message, editImages) => $emit('save-edit', message, editImages)"
      @save-edit-only="(message, editImages) => $emit('save-edit-only', message, editImages)"
      @cancel-edit="$emit('cancel-edit', $event)"
      @copy-message="$emit('copy-message', $event)"
      @insert-to-editor="$emit('insert-to-editor', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import AgentMessage from './AgentMessage.vue';
import type { ChatMessage } from '../../composables/useAgentChat';

interface Props {
  messages: ChatMessage[];
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

const messagesContainer = ref<HTMLElement | null>(null);

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动到底部
watch(() => props.messages.length, () => {
  nextTick(() => {
    scrollToBottom();
  });
});

// 监听消息内容变化（用于流式更新时的滚动）
watch(() => props.messages.map(m => m.content).join(''), () => {
  nextTick(() => {
    scrollToBottom();
  });
});

// 暴露滚动方法
defineExpose({
  scrollToBottom
});
</script>

<style scoped>
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