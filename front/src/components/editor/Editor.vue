<template>
  <EditorContainer
    :modelValue="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :conversationId="conversationId"
    :noteId="noteId"
    @word-count="$emit('word-count', $event)"
    @update:conversationId="$emit('update:conversationId', $event)"
    @toggle-sidebar-mode="$emit('toggle-sidebar-mode', $event)"
    @sidebar-send="$emit('sidebar-send', $event)"
    @sidebar-insert="$emit('sidebar-insert', $event)"
    @sidebar-navigate-history="$emit('sidebar-navigate-history', $event)"
    @conversation-history-loaded="handleConversationHistoryLoaded"
    @title-updated="$emit('title-updated', $event)"
    @agent-response-chunk="onAgentResponseChunk"
    @agent-response-complete="onAgentResponseComplete"
    @agent-response-error="onAgentResponseError"
    @agent-tool-status="onAgentToolStatus"
    @note-content-updated="onNoteContentUpdated"
    ref="editorContainerRef"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import EditorContainer from './EditorContainer.vue';
import { useConversationManager } from '../../composables/useConversationManager';

// Props
const props = defineProps({
  modelValue: {
    type: String,
    default: '<p>开始写作...</p>'
  },
  conversationId: {
    type: [Number, String, null],
    default: null
  },
  noteId: {
    type: [Number, String, null],
    default: null
  }
});

// Emits
const emit = defineEmits([
  'update:modelValue', 
  'word-count', 
  'update:conversationId', 
  'toggle-sidebar-mode', 
  'sidebar-send', 
  'sidebar-insert', 
  'sidebar-navigate-history', 
  'conversation-history-loaded', 
  'title-updated'
]);

// 使用composables
const conversationManager = useConversationManager();

// 组件引用
const editorContainerRef = ref(null);

// Agent事件处理
const onAgentResponseChunk = (chunk: string) => {
  console.log('[EditorNew] Received chunk:', chunk);
  // EditorContainer会处理这些事件，这里只是传递
};

const onAgentToolStatus = (toolStatus: any) => {
  console.log('[EditorNew] Received tool status:', toolStatus);
  // EditorContainer会处理这些事件
};

const onNoteContentUpdated = (updateData: any) => {
  console.log('[EditorNew] 收到笔记内容更新事件:', updateData);
  
  // 检查是否是当前笔记的更新
  if (props.noteId && updateData.noteId && parseInt(props.noteId) === updateData.noteId) {
    console.log('[EditorNew] 更新当前笔记内容');
    
    // 更新编辑器内容
    if (updateData.content !== undefined) {
      emit('update:modelValue', updateData.content);
      
      // 如果标题也更新了，可以通过事件通知父组件
      if (updateData.title) {
        emit('title-updated', updateData.title);
      }
    }
  }
};

const onAgentResponseComplete = (data: { responseText: string, conversationId?: string | number }) => {
  console.log('[EditorNew] Response complete:', data);
  
  // 更新对话ID
  if (data.conversationId && props.conversationId !== data.conversationId) {
    emit('update:conversationId', data.conversationId);
    console.log('[EditorNew] Updated conversationId to:', data.conversationId);
  }
};

const onAgentResponseError = (error: any) => {
  console.error('[EditorNew] Agent response error:', error);
};

// 处理会话历史记录加载完成
const handleConversationHistoryLoaded = (data: any) => {
  // 更新会话管理器的状态
  conversationManager.conversationHistory.value = data.history || [];
  conversationManager.historyDisplayIndex.value = data.length > 0 ? data.length - 1 : -1;
  conversationManager.lastLoadedSessionId.value = data.sessionId;
  
  // 转发事件给父组件
  emit('conversation-history-loaded', data);
};

// 监听会话ID变化，加载历史记录
watch(() => props.conversationId, (newId) => {
  conversationManager.loadConversationHistory(newId, emit);
}, { immediate: true });

// 监听笔记ID变化
watch(() => props.noteId, (newId) => {
  console.log('[EditorNew] 笔记ID变化:', newId);
  // EditorContainer会处理noteId的变化
}, { immediate: true });

// 暴露方法给父组件
defineExpose({
  focus: () => editorContainerRef.value?.focus(),
  getContent: () => editorContainerRef.value?.getContent(),
  setContent: (content: string) => editorContainerRef.value?.setContent(content),
  onNoteEditPreview: (previewData: any) => editorContainerRef.value?.onNoteEditPreview(previewData),
  setInteractionMode: (mode: 'modal' | 'sidebar') => editorContainerRef.value?.setInteractionMode(mode),
  getCurrentAgentData: () => editorContainerRef.value?.getCurrentAgentData(),
  closeModal: () => editorContainerRef.value?.closeModal(),
  showModalWithContent: (data: any) => editorContainerRef.value?.showModalWithContent(data),
  handleInsertResponse: (text: string) => editorContainerRef.value?.handleInsertResponse(text)
});
</script>

<style scoped>
/* 这个组件主要是作为容器，样式由EditorContainer处理 */
</style> 