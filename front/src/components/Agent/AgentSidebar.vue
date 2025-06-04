<template>
  <div v-if="visible" class="agent-sidebar" :style="{ width: sidebarWidth + 'px' }">
    <!-- 可拖动的分隔条 -->
    <ResizableHandle @resize="handleResize" />
    
    <!-- 侧边栏头部 -->
    <AgentSidebarHeader @close="close" :noteId="noteId" @session-switched="handleSessionSwitched" ref="headerRef" />

    <!-- 聊天消息区域 -->
    <AgentMessageList
      :messages="messages"
      @start-edit="startEditMessage"
      @save-edit="saveEditMessage"
      @save-edit-only="saveEditMessageOnly"
      @cancel-edit="cancelEditMessage"
      @copy-message="copyMessage"
      @insert-to-editor="insertToEditor"
      ref="messageListRef"
    />

    <!-- 输入区域 -->
    <AgentSidebarInputArea
      @send="handleSendMessage"
      @select-agent="handleSelectAgent"
      @upload-file="handleUploadFile"
      @stop-response="handleStopResponse"
      :is-agent-responding="isAgentResponding"
      ref="inputAreaRef"
    />

    <!-- 工具状态处理组件（隐藏） -->
    <AgentSidebarToolStatus ref="toolStatusRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import AgentSidebarHeader from './sidebar/AgentSidebarHeader.vue';
import AgentSidebarInputArea from './sidebar/AgentSidebarInputArea.vue';
import AgentSidebarToolStatus from './sidebar/AgentSidebarToolStatus.vue';
import AgentMessageList from './AgentMessageList.vue';
import ResizableHandle from './ResizableHandle.vue';
import { useAgentSidebarLogic } from '../../composables/useAgentSidebarLogic';
import { useAgentSidebarHistory } from '../../composables/useAgentSidebarHistory';
import { useAgentSidebarMessageEdit } from '../../composables/useAgentSidebarMessageEdit';
import { parseAgentMessage, extractTextFromInteractionFlow } from '../../utils/messageParser';
import chatService from '../../services/chat';

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

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history', 'adjust-tone', 'edit-message', 'resize', 'note-edit-preview', 'stop-response', 'session-switched']);

// 组件引用
const messageListRef = ref(null);
const inputAreaRef = ref(null);
const toolStatusRef = ref(null);
const headerRef = ref(null);

// 使用主要业务逻辑
const {
  currentAgent,
  sidebarWidth,
  messages,
  isEditingMessage,
  editingController,
  lastProcessedResponse,
  handleResize,
  restoreSidebarWidth,
  handleToolStatus,
  processTextResponse,
  handleSendMessage,
  handleSelectAgent,
  handleUploadFile,
  renderMarkdown,
  // 从composables导出的方法
  deduplicateMessages,
  addUserMessage,
  addAgentMessage,
  getCurrentTypingMessage,
  startEdit,
  cancelEdit,
  getMessageIndexInHistory,
  clearMessages,
  copyMessage,
  handleToolStatusUpdate,
  handleStreamingText,
  handleCompleteResponse,
  getSortedContentChunks
} = useAgentSidebarLogic(props, emit);

// 使用历史记录管理逻辑
const {
  initializeFromHistory
} = useAgentSidebarHistory(props, {
  messages,
  deduplicateMessages,
  clearMessages,
  getCurrentTypingMessage,
  currentAgent,
  getSortedContentChunks,
  parseAgentMessage,
  extractTextFromInteractionFlow
});

// 使用消息编辑逻辑
const {
  startEditMessage,
  cancelEditMessage,
  saveEditMessage,
  saveEditMessageOnly,
  getMessageIndexInHistoryLocal
} = useAgentSidebarMessageEdit(props, emit, {
  messages,
  isEditingMessage,
  editingController,
  currentAgent,
  addAgentMessage,
  getCurrentTypingMessage,
  getMessageIndexInHistory,
  handleToolStatus,
  handleStreamingText,
  handleCompleteResponse,
  scrollToBottom: () => messageListRef.value?.scrollToBottom(),
  renderSpecialComponents: () => toolStatusRef.value?.renderSpecialComponents(),
  handleToolStatusUpdate,
  toolStatusRef
});

// 插入到编辑器
const insertToEditor = (content: string) => {
  emit('request-insert', content);
};

// 滚动到底部
const scrollToBottom = () => {
  messageListRef.value?.scrollToBottom();
};

// 关闭侧边栏
const close = () => {
  emit('close');
};

// 增强的工具状态处理器，添加笔记编辑结果处理
const enhancedHandleToolStatus = (toolStatus: any) => {
  console.log('🔧 [AgentSidebar] enhancedHandleToolStatus被调用');
  console.log('🔧 [AgentSidebar] 收到工具状态:', toolStatus);
  console.log('🔧 [AgentSidebar] 工具状态详细信息:', JSON.stringify(toolStatus, null, 2));
  
  // 先直接进行UI更新，像编辑重新执行一样
  const currentMsg = getCurrentTypingMessage();
  if (currentMsg) {
    console.log('🔧 [AgentSidebar] 正常对话找到当前消息，直接更新工具状态UI:', {
      id: currentMsg.id,
      toolName: toolStatus.tool_name,
      status: toolStatus.status,
      toolCallId: toolStatus.tool_call_id
    });
    handleToolStatusUpdate(toolStatus, currentMsg);
  } else {
    console.warn('🔧 [AgentSidebar] 没有找到当前消息，无法更新工具状态UI');
    console.warn('🔧 [AgentSidebar] 当前消息列表:', messages.value.map(msg => ({
      id: msg.id,
      type: msg.type,
      isTyping: msg.isTyping
    })));
  }
  
  // 然后进行特殊逻辑处理
  const result = handleToolStatus(toolStatus);
  
  // 如果是笔记编辑工具结果，进行特殊处理
  if (result && result.type === 'note_editor_result') {
    console.log('[AgentSidebar] 检测到笔记编辑工具结果，开始处理预览');
    console.log('[AgentSidebar] toolStatusRef是否存在:', !!toolStatusRef.value);
    console.log('[AgentSidebar] handleNoteEditorResult方法是否存在:', typeof toolStatusRef.value?.handleNoteEditorResult);
    
    const noteEditData = toolStatusRef.value?.handleNoteEditorResult(result.result);
    if (noteEditData) {
      console.log('[AgentSidebar] 笔记编辑数据处理成功，发射预览事件:', noteEditData);
      emit('note-edit-preview', noteEditData);
    } else {
      console.warn('[AgentSidebar] 笔记编辑数据处理失败 - handleNoteEditorResult返回null');
      console.warn('[AgentSidebar] 原始工具结果:', result.result);
    }
  }
  
  // 也检查工具状态本身是否是笔记编辑工具的完成状态
  if (toolStatus.tool_name === 'note_editor' && toolStatus.status === 'completed' && toolStatus.result) {
    console.log('[AgentSidebar] 直接检测到笔记编辑工具完成状态');
    console.log('[AgentSidebar] toolStatusRef是否存在:', !!toolStatusRef.value);
    console.log('[AgentSidebar] handleNoteEditorResult方法是否存在:', typeof toolStatusRef.value?.handleNoteEditorResult);
    
    const noteEditData = toolStatusRef.value?.handleNoteEditorResult(toolStatus.result);
    if (noteEditData) {
      console.log('[AgentSidebar] 直接处理笔记编辑结果成功，发射预览事件:', noteEditData);
      emit('note-edit-preview', noteEditData);
    } else {
      console.warn('[AgentSidebar] 直接处理笔记编辑结果失败 - handleNoteEditorResult返回null');
      console.warn('[AgentSidebar] 原始工具状态结果:', toolStatus.result);
    }
  }
  
  console.log('🔧 [AgentSidebar] enhancedHandleToolStatus处理完成');
};

// 监听AI响应变化
watch(() => props.agentResponse, (newResponse) => {
  if (newResponse) {
    console.log('收到新的agentResponse:', newResponse.length, '字符');
    
    // 检查是否与上次处理的内容相同，避免重复处理
    if (newResponse === lastProcessedResponse.value) {
      console.log('内容与上次相同，跳过重复处理');
      return;
    }
    
    // 检查是否有正在进行的编辑重新执行
    const hasEditingMessage = messages.value.some(msg => 
      msg.type === 'agent' && 
      msg.isTyping && 
      msg.id && 
      (msg.id.includes('edit_') || msg.id.includes('edit_agent_'))
    );
    
    // 如果有编辑重新执行的消息，不处理普通的agentResponse
    if (hasEditingMessage) {
      console.log('检测到编辑重新执行中，跳过普通agentResponse处理');
      return;
    }
    
    // 🔧 修复：移除在这里处理工具状态的逻辑，工具状态应该通过enhancedHandleToolStatus回调处理
    // 这里只处理文本内容，工具状态由独立的回调机制处理
    console.log('🔧 AgentSidebar watch agentResponse: 只处理文本内容，工具状态由回调处理');
    
    // 处理普通的文本响应（不尝试解析工具状态）
    processTextResponse(newResponse);
  }
});

// 监听响应状态变化
watch(() => props.isAgentResponding, (isResponding) => {
  if (!isResponding) {
    // 响应完成，移除打字指示器（包括普通响应和编辑重新执行）
    const typingMsgIndex = messages.value.findIndex(msg => 
      msg.type === 'agent' && msg.isTyping
    );
    if (typingMsgIndex !== -1) {
      const typingMsg = messages.value[typingMsgIndex];
      typingMsg.isTyping = false;
      
      console.log('响应完成，消息ID:', typingMsg.id, '消息类型:', typingMsg.id?.includes('edit_') ? '编辑重新执行' : '普通响应');
      console.log('响应完成时的contentChunks:', typingMsg.contentChunks?.map(chunk => ({
        type: chunk.type,
        tool_name: chunk.tool_name,
        status: chunk.status,
        tool_call_id: chunk.tool_call_id
      })));
      
      // 响应完成时，确保所有工具状态都标记为完成状态
      if (typingMsg.contentChunks && typingMsg.contentChunks.length > 0) {
        console.log('响应完成，更新工具状态并优化contentChunks结构');
        
        // 更新所有还在执行中的工具状态为完成状态
        typingMsg.contentChunks.forEach(chunk => {
          if (chunk.type === 'tool_status' && 
              (chunk.status === 'preparing' || chunk.status === 'executing' || !chunk.status)) {
            console.log('更新工具状态为完成:', chunk.tool_name, chunk.tool_call_id, '原状态:', chunk.status);
            chunk.status = 'completed';
          }
        });
        
        console.log('工具状态更新后的contentChunks:', typingMsg.contentChunks?.map(chunk => ({
          type: chunk.type,
          tool_name: chunk.tool_name,
          status: chunk.status,
          tool_call_id: chunk.tool_call_id
        })));
        
        // 调用handleCompleteResponse来优化结构
        handleCompleteResponse(typingMsg.content || '', typingMsg);
      }
    }
    
    // 响应完成后，清理最后处理的响应内容，为下次对话做准备
    lastProcessedResponse.value = '';
    
    // 响应完成后，立即触发特殊组件渲染，不要延迟
    nextTick(() => {
      toolStatusRef.value?.renderSpecialComponents();
    });
    
    // 响应完成后，刷新会话列表（如果有noteId）
    if (props.noteId && headerRef.value && headerRef.value.refreshSessions) {
      console.log('[AgentSidebar] 响应完成，刷新会话列表');
      setTimeout(() => {
        headerRef.value.refreshSessions();
      }, 1000); // 稍微延迟一下，确保后端已经生成并保存了会话标题
    }
  }
});

// Watch 侧边栏显示状态，自动聚焦
watch(() => props.visible, (visible) => {
  if (visible) {
    nextTick(() => {
      inputAreaRef.value?.focus();
      scrollToBottom();
    });
  }
});

// 监听会话历史变化
watch(() => props.conversationHistory, (newHistory, oldHistory) => {
  console.log('=== AgentSidebarRefactored: 会话历史发生变化 ===');
  console.log('新历史记录数量:', newHistory?.length || 0);
  console.log('当前isAgentResponding:', props.isAgentResponding);
  
  // 如果当前正在响应，延迟处理历史记录变化
  if (props.isAgentResponding) {
    console.log('当前正在响应中，延迟处理历史记录变化');
    return;
  }
  
  // 深度比较历史记录内容，避免因为引用变化导致的重复初始化
  const isContentSame = (arr1: any[], arr2: any[]) => {
    if (!arr1 && !arr2) return true;
    if (!arr1 || !arr2) return false;
    if (arr1.length !== arr2.length) return false;
    
    return arr1.every((item1, index) => {
      const item2 = arr2[index];
      return item1?.user === item2?.user && 
             item1?.agent === item2?.agent &&
             item1?.userMessageId === item2?.userMessageId &&
             item1?.agentMessageId === item2?.agentMessageId;
    });
  };
  
  // 如果内容完全相同，跳过处理
  if (isContentSame(newHistory, oldHistory)) {
    console.log('历史记录内容完全相同，跳过处理');
    return;
  }
  
  // 检测是否是笔记切换或新建笔记
  const isNoteSwitching = (
    // 从有记录变为无记录（新建笔记场景）
    (oldHistory && oldHistory.length > 0 && (!newHistory || newHistory.length === 0))
  ) || (
    // 从无记录变为有记录（切换到有历史的笔记）
    (!oldHistory || oldHistory.length === 0) && newHistory && newHistory.length > 0
  ) || (
    // 历史记录内容完全不同（切换不同的笔记）
    oldHistory && newHistory && 
    oldHistory.length > 0 && newHistory.length > 0 &&
    (oldHistory[0]?.user !== newHistory[0]?.user ||
     oldHistory[0]?.agent !== newHistory[0]?.agent ||
     oldHistory[oldHistory.length - 1]?.user !== newHistory[newHistory.length - 1]?.user ||
     oldHistory[oldHistory.length - 1]?.agent !== newHistory[newHistory.length - 1]?.agent)
  );
  
  console.log('是否检测到笔记切换:', isNoteSwitching);
  
  // 检查是否只是在历史记录末尾添加了新的对话（新消息场景）
  const isNewMessageAdded = oldHistory && newHistory && 
    newHistory.length === oldHistory.length + 1 &&
    oldHistory.every((item, index) => 
      item.user === newHistory[index]?.user && 
      item.agent === newHistory[index]?.agent
    );
  
  console.log('是否只是添加了新消息:', isNewMessageAdded);
  
  if (isNoteSwitching) {
    console.log('检测到笔记切换，强制更新历史记录');
    initializeFromHistory(true); // 强制更新
  } else if (isNewMessageAdded) {
    console.log('检测到新消息添加，延迟更新以避免与当前流式响应冲突');
    // 延迟更新，确保当前流式响应完成
    setTimeout(() => {
      if (!props.isAgentResponding) {
        console.log('延迟更新历史记录');
        initializeFromHistory(false);
      }
    }, 200); // 增加延迟时间
  } else {
    console.log('正常历史记录变化，常规更新');
    // 使用防抖机制，避免频繁更新
    setTimeout(() => {
      if (!props.isAgentResponding) {
        initializeFromHistory(false);
      }
    }, 100);
  }
}, { deep: true, immediate: false });

// 组件挂载时初始化
onMounted(() => {
  // 恢复侧边栏宽度
  restoreSidebarWidth();
  
  // 初始化历史记录（如果有的话）
  if (props.conversationHistory && props.conversationHistory.length > 0) {
    console.log('组件挂载时初始化历史记录');
    initializeFromHistory();
  } else {
    console.log('组件挂载时无历史记录，保持空状态');
    clearMessages();
  }
  
  nextTick(() => {
    inputAreaRef.value?.focus();
  });
});

// 暴露方法给父组件
defineExpose({
  handleToolStatus: enhancedHandleToolStatus
});

// 停止Agent响应
const handleStopResponse = () => {
  console.log('[AgentSidebar] 用户请求停止响应');
  emit('stop-response');
};

// 处理会话切换
const handleSessionSwitched = (sessionId: number) => {
  console.log('[AgentSidebar] 会话切换到:', sessionId);
  
  // 清理当前消息
  clearMessages();
  
  // 发射会话切换事件给父组件，让父组件重新加载会话历史
  emit('session-switched', sessionId);
};
</script>

<style scoped>
.agent-sidebar {
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e5e7eb;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  /* 确保组件立即显示，避免闪烁 */
  opacity: 1;
  visibility: visible;
  min-width: 300px;
  max-width: 600px;
}
</style> 