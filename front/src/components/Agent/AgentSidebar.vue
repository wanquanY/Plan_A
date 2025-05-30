<template>
  <div v-if="visible" class="agent-sidebar" :style="{ width: sidebarWidth + 'px' }">
    <!-- 可拖动的分隔条 -->
    <ResizableHandle @resize="handleResize" />
    
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
import { ref, onMounted, watch, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import UnifiedInput from '../unified-input/UnifiedInput.vue';
import AgentMessageList from './AgentMessageList.vue';
import MermaidRenderer from '../rendering/MermaidRenderer.vue';
import CodeBlock from '../rendering/CodeBlock.vue';
import MarkMap from '../rendering/MarkMap.vue';
import ResizableHandle from './ResizableHandle.vue';
import { useAgentChat } from '../../composables/useAgentChat';
import { useStreamingResponse } from '../../composables/useStreamingResponse';
import { parseAgentMessage, extractTextFromInteractionFlow, extractReasoningFromInteractionFlow, hasReasoningContent } from '../../utils/messageParser';
import { renderMermaidDynamically, renderCodeBlocks, renderMarkMaps } from '../../services/renderService';
import { markdownToHtml } from '../../services/markdownService';
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
  }
});

const emit = defineEmits(['close', 'send', 'select-agent', 'request-insert', 'navigate-history', 'adjust-tone', 'edit-message', 'resize', 'note-edit-preview']);

// 组件引用
const unifiedInputRef = ref(null);
const messageListRef = ref(null);
const mermaidRenderer = ref(null);
const codeBlockRenderer = ref(null);
const markMapRenderer = ref(null);

// 使用composables
const {
  messages,
  isEditingMessage,
  editingController,
  lastProcessedResponse,
  deduplicateMessages,
  addUserMessage,
  addAgentMessage,
  getCurrentTypingMessage,
  startEditMessage: startEdit,
  cancelEditMessage: cancelEdit,
  getMessageIndexInHistory,
  clearMessages,
  copyMessage
} = useAgentChat();

const {
  handleToolStatus: handleToolStatusUpdate,
  handleStreamingText,
  handleCompleteResponse,
  getSortedContentChunks
} = useStreamingResponse();

// 注意：移除了 useToolCallsStatus，工具状态现在通过 contentChunks 管理

// 当前选择的Agent
const currentAgent = ref(null);

// 侧边栏宽度管理
const sidebarWidth = ref(400); // 默认宽度

// 处理侧边栏宽度调整
const handleResize = (newWidth: number) => {
  sidebarWidth.value = newWidth;
  
  // 向父组件发出resize事件
  emit('resize', newWidth);
  
  // 可选：保存到localStorage
  try {
    localStorage.setItem('agent-sidebar-width', newWidth.toString());
  } catch (error) {
    console.warn('无法保存侧边栏宽度到localStorage:', error);
  }
};

// 从localStorage恢复侧边栏宽度
const restoreSidebarWidth = () => {
  try {
    const savedWidth = localStorage.getItem('agent-sidebar-width');
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= 300 && width <= 600) {
        sidebarWidth.value = width;
      }
    }
  } catch (error) {
    console.warn('无法从localStorage恢复侧边栏宽度:', error);
  }
};

// 处理工具状态更新
const handleToolStatus = (toolStatus: any) => {
  console.log('AgentSidebar 处理工具状态:', toolStatus);
  
  // 检查是否是思考内容
  if (toolStatus.type === 'reasoning_content') {
    console.log('AgentSidebar 检测到思考内容:', toolStatus.reasoning_content);
    
    // 将思考内容添加到当前正在进行的AI消息的contentChunks中
    const currentMsg = getCurrentTypingMessage();
    if (currentMsg) {
      // 初始化contentChunks（如果还没有）
      if (!currentMsg.contentChunks) {
        currentMsg.contentChunks = [];
      }
      
      // 查找最后一个chunk，如果是reasoning类型，则合并内容
      const lastChunk = currentMsg.contentChunks[currentMsg.contentChunks.length - 1];
      if (lastChunk && lastChunk.type === 'reasoning') {
        // 合并到现有的思考内容中
        lastChunk.content += toolStatus.reasoning_content;
        lastChunk.timestamp = new Date(); // 更新时间戳
        
        console.log('已合并思考内容到现有chunk:', {
          totalReasoningLength: lastChunk.content.length,
          newContentLength: toolStatus.reasoning_content.length
        });
      } else {
        // 创建新的思考内容chunk
        const reasoningChunk = {
          type: 'reasoning',
          content: toolStatus.reasoning_content,
          timestamp: new Date()
        };
        
        currentMsg.contentChunks.push(reasoningChunk);
        
        console.log('已创建新的思考内容chunk:', {
          reasoningLength: toolStatus.reasoning_content.length,
          totalChunks: currentMsg.contentChunks.length
        });
      }
    }
    
    return; // 思考内容不需要进一步处理
  }
  
  // 检查是否是笔记编辑工具的完成状态
  if (toolStatus.tool_name === 'note_editor' && toolStatus.status === 'completed' && toolStatus.result) {
    console.log('[AgentSidebar] 检测到笔记编辑工具完成，处理结果');
    console.log('[AgentSidebar] 工具结果原始内容:', toolStatus.result);
    handleNoteEditorResult(toolStatus.result);
  }
  
  // 实时添加工具状态到当前正在进行的AI消息中
  nextTick(() => {
    const currentMsg = getCurrentTypingMessage();
    if (currentMsg) {
      handleToolStatusUpdate(toolStatus, currentMsg);
    }
  });
};

// 处理笔记编辑工具结果的函数（复制自AgentResponseHandler）
const handleNoteEditorResult = (toolResult) => {
  console.log('[AgentSidebar] 处理笔记编辑工具结果:', toolResult);
  console.log('[AgentSidebar] 工具结果类型:', typeof toolResult);
  console.log('[AgentSidebar] 工具结果内容:', JSON.stringify(toolResult, null, 2));
  
  try {
    let resultData = toolResult;
    
    // 如果结果是字符串，尝试解析为JSON
    if (typeof toolResult === 'string') {
      try {
        resultData = JSON.parse(toolResult);
        console.log('[AgentSidebar] 解析JSON后的结果:', resultData);
      } catch (e) {
        console.warn('[AgentSidebar] 无法解析工具结果为JSON:', e);
        return;
      }
    }
    
    console.log('[AgentSidebar] 检查编辑结果字段:', {
      success: resultData?.success,
      note_id: resultData?.note_id,
      content_exists: resultData?.content !== undefined,
      content_length: resultData?.content?.length || 0,
      is_preview: resultData?.is_preview
    });
    
    // 检查是否是成功的笔记编辑结果
    if (resultData && resultData.success && resultData.note_id && resultData.content !== undefined) {
      console.log('[AgentSidebar] 笔记编辑成功，准备发射预览事件');
      
      // 发射笔记编辑预览事件
      emit('note-edit-preview', {
        noteId: resultData.note_id,
        title: resultData.title,
        content: resultData.content,
        editType: resultData.edit_type,
        isPreview: resultData.is_preview || false,
        changes: resultData.changes,
        updatedAt: resultData.updated_at,
        contentPreview: resultData.content_preview
      });
      
      console.log('[AgentSidebar] 已发射笔记编辑预览事件');
    } else {
      console.log('[AgentSidebar] 笔记编辑结果不符合预期格式:', {
        has_success: !!resultData?.success,
        has_note_id: !!resultData?.note_id,
        has_content: resultData?.content !== undefined
      });
    }
  } catch (error) {
    console.error('[AgentSidebar] 处理笔记编辑结果时出错:', error);
  }
};

// 处理文本响应
const processTextResponse = (textContent: string) => {
  console.log('处理文本响应:', textContent.length, '字符');
  
  // 尝试解析agentResponse，检查是否是JSON结构
  let parsedResponse = null;
  let displayContent = textContent;
  let contentChunks = [];
  
  try {
    // 尝试解析JSON结构
    parsedResponse = parseAgentMessage(textContent);
    
    if (typeof parsedResponse === 'object' && parsedResponse.type === 'agent_response') {
      console.log('检测到JSON结构的agent响应，interaction_flow长度:', parsedResponse.interaction_flow?.length || 0);
      
      // 提取纯文本内容用于显示
      displayContent = extractTextFromInteractionFlow(parsedResponse.interaction_flow);
      
      // 将交互流程转换为contentChunks格式
      contentChunks = parsedResponse.interaction_flow.map((segment: any) => {
        if (segment.type === 'text') {
          return {
            type: 'text',
            content: segment.content,
            timestamp: new Date(segment.timestamp)
          };
        } else if (segment.type === 'tool_call') {
          return {
            type: 'tool_status',
            tool_name: segment.name,
            status: segment.status,
            tool_call_id: segment.id,
            timestamp: new Date(segment.started_at),
            result: segment.result,
            error: segment.error
          };
        } else if (segment.type === 'reasoning') {
          // 思考内容也添加到contentChunks中，用于时序渲染
          return {
            type: 'reasoning',
            content: segment.content,
            timestamp: new Date(segment.timestamp)
          };
        }
        return segment;
      }).filter(chunk => chunk !== null);
      
      console.log('转换后的contentChunks:', contentChunks.map(chunk => `${chunk.type}:${chunk.tool_name || chunk.content?.substring(0, 20) || 'empty'}`));
    } else {
      // 不是JSON结构，使用原始内容
      console.log('不是JSON结构，使用原始内容处理');
      contentChunks = [{
        type: 'text',
        content: textContent,
        timestamp: new Date()
      }];
    }
  } catch (error) {
    console.log('解析agentResponse失败，使用原始内容:', error.message);
    // 解析失败，使用原始内容
    contentChunks = [{
      type: 'text',
      content: textContent,
      timestamp: new Date()
    }];
  }
  
  // 查找现有的正在进行的AI消息（排除历史消息和编辑消息）
  const existingAgentMsgIndex = messages.value.findIndex(msg => 
    msg.type === 'agent' && 
    msg.isTyping && 
    (!msg.id || (!msg.id.includes('edit_') && !msg.id.startsWith('history_')))
  );
  
  if (existingAgentMsgIndex !== -1) {
    // 更新现有消息
    const currentMsg = messages.value[existingAgentMsgIndex];
    
    // 更新消息内容
    currentMsg.content = displayContent;
    currentMsg.originalContent = textContent; // 保存原始内容
    currentMsg.isTyping = props.isAgentResponding;
    
    // 如果是JSON结构响应，说明是最终的完整响应，直接替换
    if (typeof parsedResponse === 'object' && parsedResponse.type === 'agent_response') {
      console.log('收到最终JSON结构响应，替换为完整的interaction_flow');
      currentMsg.contentChunks = contentChunks;
    } else {
      // 对于非JSON结构响应（流式文本），智能分段处理
      handleStreamingText(textContent, currentMsg);
    }
    
    console.log('更新现有AI消息，索引:', existingAgentMsgIndex);
    console.log('显示内容长度:', displayContent.length);
    console.log('内容块数量:', currentMsg.contentChunks?.length || 0);
    
    // 更新最后处理的响应内容
    lastProcessedResponse.value = textContent;
  } else {
    // 检查是否已经有相同内容的消息，避免重复添加
    const hasSameContent = messages.value.some(msg => 
      msg.type === 'agent' && 
      msg.content === displayContent && 
      !msg.isTyping &&
      !msg.id?.startsWith('history_') // 排除历史消息
    );
    
    // 检查是否已经有相同时间戳的消息（避免快速重复添加）
    const currentTime = Date.now();
    const hasRecentMessage = messages.value.some(msg => 
      msg.type === 'agent' && 
      Math.abs(msg.timestamp?.getTime() - currentTime) < 1000 && // 1秒内
      !msg.id?.startsWith('history_')
    );
    
    if (!hasSameContent && !hasRecentMessage) {
      // 添加新的AI消息
      const agentMessage = {
        id: `agent_${currentTime}_${Math.random().toString(36).substr(2, 9)}`, // 更唯一的ID
        type: 'agent',
        content: displayContent,
        originalContent: textContent, // 保存原始内容
        timestamp: new Date(),
        agent: currentAgent.value,
        isTyping: props.isAgentResponding,
        contentChunks: contentChunks
      };
      messages.value.push(agentMessage);
      console.log('添加新的AI消息，ID:', agentMessage.id);
      console.log('显示内容长度:', displayContent.length);
      console.log('内容块数量:', contentChunks.length);
      
      // 更新最后处理的响应内容
      lastProcessedResponse.value = textContent;
    } else {
      console.log('检测到重复内容或时间过近，跳过添加');
    }
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
};

// 从会话历史初始化聊天记录
const initializeFromHistory = (forceUpdate = false) => {
  console.log('=== AgentSidebar: 初始化聊天记录 ===');
  console.log('历史记录数量:', props.conversationHistory?.length || 0);
  console.log('forceUpdate:', forceUpdate);
  console.log('当前isAgentResponding:', props.isAgentResponding);
  
  // 如果当前正在响应且不是强制更新，不要重新初始化
  if (props.isAgentResponding && !forceUpdate) {
    console.log('当前正在响应中，跳过历史记录初始化');
    return;
  }
  
  // 如果有正在进行的AI消息且不是强制更新，也跳过初始化
  const hasActiveAgentMessage = messages.value.some(msg => msg.type === 'agent' && msg.isTyping);
  if (hasActiveAgentMessage && !forceUpdate) {
    console.log('有正在进行的AI消息，跳过历史记录初始化');
    return;
  }
  
  if (!props.conversationHistory || props.conversationHistory.length === 0) {
    console.log('历史记录为空，清空messages');
    clearMessages();
    return;
  }

  console.log('开始处理历史记录，条数:', props.conversationHistory.length);
  
  // 检查当前messages是否已经包含了这些历史记录
  const currentHistoryIds = new Set();
  messages.value.forEach(msg => {
    if (msg.id && msg.id.startsWith('history_')) {
      currentHistoryIds.add(msg.id);
    }
  });
  
  // 生成新的历史记录ID集合
  const newHistoryIds = new Set();
  props.conversationHistory.forEach((conversation: any, index: number) => {
    if (conversation.user) {
      newHistoryIds.add(`history_${index}_user`);
    }
    if (conversation.agent) {
      newHistoryIds.add(`history_${index}_agent`);
    }
  });
  
  // 检查是否是相同的历史记录
  const isSameHistory = currentHistoryIds.size === newHistoryIds.size && 
    [...currentHistoryIds].every(id => newHistoryIds.has(id));
  
  if (isSameHistory && !forceUpdate) {
    console.log('历史记录内容相同，跳过重复初始化');
    return;
  }
  
  console.log('历史记录内容不同，开始重新初始化');
  
  const newMessages: any[] = [];
  
  props.conversationHistory.forEach((conversation: any, index: number) => {
    console.log(`处理第${index}条历史记录:`, conversation);
    
    // 添加用户消息
    if (conversation.user) {
      const userMsg = {
        id: `history_${index}_user`,
        type: 'user',
        content: conversation.user,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index) * 60000),
        agent: currentAgent.value
      };
      newMessages.push(userMsg);
    }
    
    // 添加AI消息
    if (conversation.agent) {
      const parsedMessage = parseAgentMessage(conversation.agent);
      let displayContent = conversation.agent;
      let contentChunks: any[] = [];
      
      // 如果是新的JSON结构，构建contentChunks
      if (typeof parsedMessage === 'object' && parsedMessage.type === 'agent_response') {
        displayContent = extractTextFromInteractionFlow(parsedMessage.interaction_flow);
        
        // 将交互流程转换为contentChunks格式
        contentChunks = parsedMessage.interaction_flow.map((segment: any) => {
          if (segment.type === 'text') {
            return {
              type: 'text',
              content: segment.content,
              timestamp: new Date(segment.timestamp)
            };
          } else if (segment.type === 'tool_call') {
            return {
              type: 'tool_status',
              tool_name: segment.name,
              status: segment.status,
              tool_call_id: segment.id,
              timestamp: new Date(segment.started_at),
              result: segment.result,
              error: segment.error
            };
          } else if (segment.type === 'reasoning') {
            // 思考内容也添加到contentChunks中，用于时序渲染
            return {
              type: 'reasoning',
              content: segment.content,
              timestamp: new Date(segment.timestamp)
            };
          }
          return segment;
        }).filter(chunk => chunk !== null);
      } else {
        // 旧格式，创建简单的文本块
        contentChunks = [{
          type: 'text',
          content: displayContent,
          timestamp: new Date()
        }];
      }
      
      const agentMsg = {
        id: `history_${index}_agent`,
        type: 'agent',
        content: displayContent,
        originalContent: conversation.agent,
        timestamp: new Date(Date.now() - (props.conversationHistory.length - index - 0.5) * 60000),
        agent: currentAgent.value,
        isTyping: false,
        contentChunks: contentChunks
      };
      newMessages.push(agentMsg);
    }
  });
  
  // 更新消息列表
  if (forceUpdate) {
    // 在强制更新时，也要保留当前正在进行的消息状态
    const currentActiveMessages = messages.value.filter(msg => 
      msg.type === 'agent' && 
      !msg.id?.startsWith('history_') &&
      (msg.isTyping || (!msg.isTyping && Math.abs(msg.timestamp?.getTime() - Date.now()) < 10000)) // 10秒内的消息
    );
    
    // 如果有当前活动消息，检查是否应该替换为历史记录中的对应消息
    if (currentActiveMessages.length > 0) {
      console.log('检测到当前活动消息，尝试保留其状态');
      
      // 检查最新的历史记录是否与当前活动消息对应
      const lastHistoryAgent = newMessages.filter(msg => msg.type === 'agent').pop();
      const currentActiveMsg = currentActiveMessages[currentActiveMessages.length - 1];
      
      if (lastHistoryAgent && currentActiveMsg) {
        // 比较内容是否相似（去除空白和标点后比较）
        const normalizeText = (text: string) => text.replace(/[\s\n\r\t.,!?;:]/g, '').toLowerCase();
        const historyContent = normalizeText(lastHistoryAgent.content || '');
        const currentContent = normalizeText(currentActiveMsg.content || '');
        
        // 如果内容相似度高，说明这是同一条消息，保留当前消息状态
        if (historyContent.includes(currentContent) || currentContent.includes(historyContent)) {
          console.log('检测到历史记录与当前消息对应，保留当前消息状态');
          
          // 移除历史记录中的对应消息，保留当前消息
          const filteredNewMessages = newMessages.filter(msg => msg.id !== lastHistoryAgent.id);
          
          // 更新当前消息的ID为历史记录格式，但保留其他状态
          currentActiveMsg.id = lastHistoryAgent.id;
          currentActiveMsg.originalContent = lastHistoryAgent.originalContent;
          
          messages.value = deduplicateMessages([...filteredNewMessages, currentActiveMsg]);
        } else {
          // 内容不匹配，正常替换
          messages.value = deduplicateMessages(newMessages);
        }
      } else {
        // 没有对应关系，正常替换
        messages.value = deduplicateMessages(newMessages);
      }
    } else {
      // 没有当前活动消息，正常替换
      messages.value = deduplicateMessages(newMessages);
    }
  } else {
    const activeMessages = messages.value.filter(msg => 
      msg.type === 'agent' && msg.isTyping && msg.content !== '' && 
      !msg.id?.startsWith('history_')
    );
    
    if (activeMessages.length > 0) {
      const uniqueActiveMessages = activeMessages.filter((activeMsg: any) => 
        !newMessages.some(newMsg => 
          newMsg.content === activeMsg.content && 
          newMsg.type === activeMsg.type
        )
      );
      messages.value = deduplicateMessages([...newMessages, ...uniqueActiveMessages]);
    } else {
      messages.value = deduplicateMessages(newMessages);
    }
  }
  
  console.log('最终messages状态:', messages.value);
  
  // 滚动到底部
  nextTick(() => {
    messageListRef.value?.scrollToBottom();
  });
};

// 发送消息
const handleSendMessage = (messageData: any) => {
  // 注意：不再需要清空工具状态，因为现在使用 contentChunks 系统
  
  // 检查是否已经有相同内容的用户消息
  const hasSameUserMessage = messages.value.some(msg => 
    msg.type === 'user' && 
    msg.content === messageData.content &&
    Math.abs(msg.timestamp?.getTime() - Date.now()) < 5000
  );
  
  if (hasSameUserMessage) {
    console.log('检测到重复的用户消息，跳过发送');
    return;
  }
  
  // 添加用户消息和AI消息
  addUserMessage(messageData.content, messageData.agent);
  addAgentMessage(messageData.agent);

  // 滚动到底部
  nextTick(() => {
    messageListRef.value?.scrollToBottom();
  });

  // 发送给父组件
  emit('send', messageData);
};

// 选择Agent
const handleSelectAgent = (agent: any) => {
  currentAgent.value = agent;
  emit('select-agent', agent);
};

// 上传文件
const handleUploadFile = () => {
  console.log('上传文件功能待实现');
};

// 插入到编辑器
const insertToEditor = (content: string) => {
  emit('request-insert', content);
};

// 开始编辑消息
const startEditMessage = (messageObj: any) => {
  startEdit(messageObj);
};

// 取消编辑消息
const cancelEditMessage = (messageObj: any) => {
  cancelEdit(messageObj);
};

// 保存编辑消息并重新执行
const saveEditMessage = async (messageObj: any) => {
  if (!messageObj.editContent?.trim()) {
    message.warning('请输入消息内容');
    return;
  }
  
  if (!props.conversationId) {
    message.error('无法获取会话ID，请重新打开对话');
    return;
  }
  
  try {
    console.log('保存并重新执行消息:', messageObj);
    
    const messageIndex = getMessageIndexInHistoryLocal(messageObj);
    if (messageIndex === -1) {
      message.error('无法找到消息在历史记录中的位置');
      return;
    }
    
    // 取消编辑状态
    messageObj.isEditing = false;
    isEditingMessage.value = false;
    
    // 更新消息内容
    messageObj.content = messageObj.editContent.trim();
    
    // 找到消息在历史记录中的索引
    const currentMessageIndex = messages.value.findIndex(msg => msg.id === messageObj.id);
    if (currentMessageIndex !== -1) {
      messages.value = messages.value.slice(0, currentMessageIndex + 1);
    }
    
    // 通知父组件清除当前AI响应并开始重新执行
    emit('edit-message', {
      messageIndex,
      newContent: messageObj.content,
      rerun: true
    });
    
    // 添加AI消息用于显示工具状态和流式内容
    const agentMessage = addAgentMessage(currentAgent.value);
    
    // 滚动到底部
    nextTick(() => {
      messageListRef.value?.scrollToBottom();
    });
    
    // 调用编辑接口（流式响应）
    const editRequest = {
      message_index: messageIndex,
      content: messageObj.editContent.trim(),
      stream: true,
      agent_id: currentAgent.value?.id,
      is_user_message: true,
      rerun: true
    };
    
    console.log('发送编辑请求:', editRequest);
    
    let isEditingRerun = true;
    
    editingController.value = await chatService.editMessage(
      props.conversationId,
      editRequest,
      (response: any, isComplete: boolean, conversationId: any, toolStatus: any) => {
        if (!isEditingRerun) return;
        
        // 处理工具状态更新
        if (toolStatus) {
          handleToolStatus(toolStatus);
        }
        
        // 从响应中提取reasoning_content并作为toolStatus处理
        if (response && response.data && response.data.data && response.data.data.message) {
          const messageData = response.data.data.message;
          
          // 如果有思考内容，创建reasoning_content类型的toolStatus
          if (messageData.reasoning_content) {
            const reasoningToolStatus = {
              type: 'reasoning_content',
              reasoning_content: messageData.reasoning_content
            };
            handleToolStatus(reasoningToolStatus);
          }
        }
        
        // 解析响应内容
        let content = '';
        if (response && response.data && response.data.data) {
          content = response.data.data.full_content || 
                    (response.data.data.message && response.data.data.message.content) || '';
        } else if (typeof response === 'string') {
          content = response;
        }
        
        // 查找编辑的AI消息并更新
        const editAgentMsg = getCurrentTypingMessage();
        if (editAgentMsg) {
          if (!handleCompleteResponse(content, editAgentMsg)) {
            handleStreamingText(content, editAgentMsg);
          }
          editAgentMsg.isTyping = !isComplete;
        }
        
        // 滚动到底部
        nextTick(() => {
          messageListRef.value?.scrollToBottom();
          if (isComplete) {
            setTimeout(() => {
              renderSpecialComponents();
            }, 100);
          }
        });
        
        if (isComplete) {
          editingController.value = null;
          isEditingRerun = false;
          
          // 确保AI消息的isTyping状态被正确设置为false
          const editAgentMsg = getCurrentTypingMessage();
          if (editAgentMsg) {
            console.log('重新回答完成，设置isTyping为false');
            editAgentMsg.isTyping = false;
          }
          
          setTimeout(() => {
            console.log('编辑重新执行完成，请求刷新会话历史记录');
            emit('edit-message', {
              messageIndex,
              newContent: messageObj.content,
              rerun: true,
              refreshHistory: true
            });
          }, 500);
        }
      }
    );
    
    message.success('消息编辑成功，正在重新执行...');
    
  } catch (error: any) {
    console.error('编辑消息失败:', error);
    message.error('编辑消息失败: ' + (error.message || '未知错误'));
    
    // 恢复编辑状态
    messageObj.isEditing = true;
    isEditingMessage.value = true;
  }
};

// 仅保存编辑消息
const saveEditMessageOnly = async (messageObj: any) => {
  if (!messageObj.editContent?.trim()) {
    message.warning('请输入消息内容');
    return;
  }
  
  if (!props.conversationId) {
    message.error('无法获取会话ID，请重新打开对话');
    return;
  }
  
  try {
    console.log('仅保存消息编辑:', {
      messageId: messageObj.id,
      originalContent: messageObj.content,
      newContent: messageObj.editContent,
      conversationId: props.conversationId
    });
    
    // 找到消息在历史记录中的索引
    const messageIndex = getMessageIndexInHistoryLocal(messageObj);
    if (messageIndex === -1) {
      message.error('无法找到消息在历史记录中的位置');
      return;
    }
    
    // 调用编辑接口（非流式，仅编辑）
    const editRequest = {
      message_index: messageIndex,
      content: messageObj.editContent.trim(),
      stream: false,
      agent_id: currentAgent.value?.id,
      is_user_message: true,
      rerun: false
    };
    
    const result = await chatService.editMessage(props.conversationId, editRequest);
    
    if (result.success) {
      // 更新消息内容
      messageObj.content = messageObj.editContent.trim();
      messageObj.isEditing = false;
      isEditingMessage.value = false;
      
      message.success('消息编辑成功');
      
      // 通知父组件消息已编辑
      emit('edit-message', {
        messageIndex,
        newContent: messageObj.content,
        rerun: false
      });
    } else {
      throw new Error('编辑失败');
    }
    
  } catch (error) {
    console.error('编辑消息失败:', error);
    message.error('编辑消息失败: ' + (error.message || '未知错误'));
  }
};

// 获取消息在历史记录中的索引（本地实现，因为需要访问props）
const getMessageIndexInHistoryLocal = (messageObj) => {
  console.log('=== 开始计算消息ID ===');
  console.log('要编辑的消息内容:', messageObj.content);
  console.log('当前会话历史:', props.conversationHistory);
  
  if (!props.conversationHistory || props.conversationHistory.length === 0) {
    console.log('没有会话历史记录');
    return -1;
  }
  
  // 方法1：通过消息内容精确匹配查找
  for (let i = 0; i < props.conversationHistory.length; i++) {
    const conversation = props.conversationHistory[i];
    
    if (conversation.user && conversation.user === messageObj.content && conversation.userMessageId) {
      console.log(`找到匹配的用户消息，对话索引: ${i}, 消息ID: ${conversation.userMessageId}`);
      console.log(`匹配内容: "${conversation.user}"`);
      return conversation.userMessageId;
    }
  }
  
  console.log('通过内容匹配找不到消息ID，尝试通过消息位置查找');
  
  // 方法2：通过消息ID中的索引位置查找
  if (messageObj.id && messageObj.id.startsWith('history_')) {
    // 从ID中提取索引，格式：history_0_user
    const match = messageObj.id.match(/history_(\d+)_user/);
    if (match) {
      const historyIndex = parseInt(match[1]);
      console.log(`从消息ID提取历史索引: ${historyIndex}`);
      
      if (historyIndex >= 0 && historyIndex < props.conversationHistory.length) {
        const conversation = props.conversationHistory[historyIndex];
        if (conversation && conversation.userMessageId) {
          console.log(`通过位置找到消息ID: ${conversation.userMessageId}`);
          return conversation.userMessageId;
        }
      }
    }
  }
  
  console.log('通过位置也找不到消息ID，尝试使用最后一个用户消息ID');
  
  // 方法3：使用最后一个对话的用户消息ID（作为fallback）
  const lastConversation = props.conversationHistory[props.conversationHistory.length - 1];
  if (lastConversation && lastConversation.userMessageId) {
    console.log(`使用最后一个用户消息ID: ${lastConversation.userMessageId}`);
    console.log('=== 消息ID计算完成 ===');
    return lastConversation.userMessageId;
  }
  
  console.log('无法找到任何有效的消息ID');
  console.log('=== 消息ID计算失败 ===');
  return -1;
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
  // 使用 messageListRef 来滚动
  messageListRef.value?.scrollToBottom();
};

// 关闭侧边栏
const close = () => {
  emit('close');
};

// 渲染特殊组件（Mermaid、代码块、思维导图等）
const renderSpecialComponents = () => {
  nextTick(() => {
    try {
      // 渲染 Mermaid 图表
      renderMermaidDynamically();
      
      // 渲染代码块
      renderCodeBlocks();
      
      // 渲染思维导图
      renderMarkMaps();
      
      console.log('特殊组件渲染完成');
    } catch (error) {
      console.error('渲染特殊组件失败:', error);
    }
  });
};

// 渲染markdown内容
const renderMarkdown = (content) => {
  if (!content) return '';
  
  try {
    // 使用markdownService渲染markdown
    const htmlContent = markdownToHtml(content);
    return htmlContent;
  } catch (error) {
    console.error('渲染markdown失败:', error);
    // 如果渲染失败，回退到纯文本显示
    return content.replace(/\n/g, '<br>');
  }
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
      msg.type === 'agent' && msg.isTyping && msg.id && msg.id.includes('edit_')
    );
    
    // 如果有编辑重新执行的消息，不处理普通的agentResponse
    if (hasEditingMessage) {
      console.log('检测到编辑重新执行中，跳过普通agentResponse处理');
      return;
    }
    
    // 尝试解析是否包含工具状态信息
    let responseData = null;
    try {
      responseData = JSON.parse(newResponse);
    } catch (error) {
      // 不是JSON格式，继续处理为普通文本
    }
    
    // 检查是否包含思考内容
    if (responseData && responseData.data && responseData.data.message && responseData.data.message.reasoning_content) {
      console.log('检测到思考内容:', responseData.data.message.reasoning_content.length, '字符');
      console.log('思考内容片段:', `"${responseData.data.message.reasoning_content}"`);
      const reasoningContent = responseData.data.message.reasoning_content;
      
      // 处理思考内容
      if (reasoningContent) {
        // 将思考内容添加到当前正在进行的AI消息的contentChunks中
        const currentMsg = getCurrentTypingMessage();
        if (currentMsg) {
          // 初始化contentChunks（如果还没有）
          if (!currentMsg.contentChunks) {
            currentMsg.contentChunks = [];
          }
          
          // 查找最后一个chunk，如果是reasoning类型，则合并内容
          const lastChunk = currentMsg.contentChunks[currentMsg.contentChunks.length - 1];
          if (lastChunk && lastChunk.type === 'reasoning') {
            // 合并到现有的思考内容中
            lastChunk.content += reasoningContent;
            lastChunk.timestamp = new Date(); // 更新时间戳
            
            console.log('已合并思考内容到现有chunk:', {
              totalReasoningLength: lastChunk.content.length,
              newContentLength: reasoningContent.length
            });
          } else {
            // 创建新的思考内容chunk
            const reasoningChunk = {
              type: 'reasoning',
              content: reasoningContent,
              timestamp: new Date()
            };
            
            currentMsg.contentChunks.push(reasoningChunk);
            
            console.log('已创建新的思考内容chunk:', {
              reasoningLength: reasoningContent.length,
              totalChunks: currentMsg.contentChunks.length
            });
          }
        }
      }
    } else if (responseData && responseData.data && responseData.data.message && responseData.data.message.content) {
      // 当开始有正式内容输出时，不需要特殊处理
      console.log('检测到正式内容开始');
    }
    
    // 如果响应包含工具状态，先处理工具状态
    if (responseData && responseData.data && responseData.data.tool_status) {
      console.log('检测到工具状态信息:', responseData.data.tool_status);
      const currentMsg = getCurrentTypingMessage();
      if (currentMsg) {
        handleToolStatus(responseData.data.tool_status);
      }
      
      // 如果还有文本内容，继续处理文本
      if (responseData.data.message && responseData.data.message.content) {
        // 处理文本内容，但不重复处理工具状态
        const textContent = responseData.data.full_content || responseData.data.message.content;
        if (textContent && textContent !== lastProcessedResponse.value) {
          // 继续处理文本内容
          processTextResponse(textContent);
        }
      }
      
      // 即使没有文本内容，也要更新lastProcessedResponse以避免重复处理
      lastProcessedResponse.value = newResponse;
      
      // 滚动到底部
      nextTick(() => {
        scrollToBottom();
      });
      
      return;
    }
    
    // 处理普通的文本响应
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
      
      // 优化contentChunks结构，合并连续的文本块
      if (typingMsg.contentChunks && typingMsg.contentChunks.length > 0) {
        console.log('响应完成，优化contentChunks结构');
        // 调用handleCompleteResponse来优化结构
        handleCompleteResponse(typingMsg.content || '', typingMsg);
      }
    }
    
    // 响应完成后，清理最后处理的响应内容，为下次对话做准备
    lastProcessedResponse.value = '';
    
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
  console.log('当前isAgentResponding:', props.isAgentResponding);
  
  // 如果当前正在响应，延迟处理历史记录变化
  if (props.isAgentResponding) {
    console.log('当前正在响应中，延迟处理历史记录变化');
    return;
  }
  
  // 深度比较历史记录内容，避免因为引用变化导致的重复初始化
  const isContentSame = (arr1, arr2) => {
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
  
  // 检测是否是笔记切换或新建笔记：
  // 1. 从有记录变为无记录（新建笔记）
  // 2. 从无记录变为有记录（切换到有历史的笔记）
  // 3. 历史记录内容完全不同（切换笔记）
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
}, { deep: true, immediate: false }); // 移除immediate，避免组件初始化时的重复调用

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
    messages.value = [];
  }
  
  nextTick(() => {
    unifiedInputRef.value?.focus();
  });
});

// 暴露方法给父组件
defineExpose({
  handleToolStatus
});

// 添加调试信息
console.log('AgentSidebar defineExpose:', {
  handleToolStatus: typeof handleToolStatus
});

// 注意：formatTextWithBreaks、getToolStatusIcon、getToolDisplayName 函数已移除，
// 这些功能现在在子组件中实现

// 注意：getToolStatusText 函数已移除，现在在子组件中实现

// 注意：getSortedContentChunks 已在 useStreamingResponse composable 中定义

// 注意：formatContentWithToolStatus 和 generateToolStatusHtml 函数已移除，
// 现在使用新的组件结构来处理工具状态显示


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

/* 编辑状态下隐藏操作按钮 */
.message.user-message .message-content.editing + .message-actions {
  display: none;
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

/* 注意：移除了旧的内联工具状态样式，现在使用 AgentToolCall 组件 */

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

/* 工具状态内容块样式 */
.content-chunk .tool-call-card {
  margin-top: 8px;
  margin-bottom: 4px;
}

/* 注意：移除了内联工具状态样式，现在使用 AgentToolCall 组件 */

/* 工具卡片样式 - 简约版 */
.tool-call-card {
  background: transparent;
  border: none;
  border-left: 3px solid #e5e7eb;
  border-radius: 0;
  margin: 8px 0;
  padding: 8px 12px;
  transition: all 0.2s ease;
  clear: both;
  display: block;
}

.tool-call-card:hover {
  background: rgba(0, 0, 0, 0.02);
}

.tool-call-card.executing {
  border-left-color: #3b82f6;
  background: rgba(59, 130, 246, 0.03);
}

.tool-call-card.completed {
  border-left-color: #10b981;
  background: rgba(16, 185, 129, 0.03);
}

.tool-call-card.error {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.03);
}

.tool-call-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
}

.tool-call-header .tool-icon {
  font-size: 14px;
  display: flex;
  align-items: center;
  min-width: 16px;
  opacity: 0.7;
}

.tool-call-header .tool-name {
  font-weight: 500;
  color: #6b7280;
  font-size: 13px;
}

.tool-call-header .tool-status-text {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
  margin-right: 8px;
}

.tool-call-header .expand-icon {
  font-size: 14px;
  color: #9ca3af;
  transition: transform 0.2s ease;
  cursor: pointer;
  margin-left: auto;
  font-weight: bold;
}

.tool-call-header .expand-icon.expanded {
  transform: rotate(90deg);
}

.tool-result {
  margin-top: 8px;
  padding: 8px 0;
  max-height: 400px;
  overflow-y: auto;
}

.tool-result pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  line-height: 1.4;
  color: #6b7280;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: #f8fafc;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.tool-error {
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 4px;
}

.tool-error .error-text {
  font-size: 12px;
  color: #dc2626;
  font-weight: 400;
}

.tool-call-card.executing .tool-icon {
  animation: rotate 2s linear infinite;
}

/* 搜索结果样式 */
.search-results {
  margin: 0;
}

.search-item {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f3f4f6;
}

.search-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.search-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #2563eb;
  text-decoration: none;
  line-height: 1.3;
  margin-bottom: 4px;
}

.search-title:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.search-snippet {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  margin: 0;
}
</style> 
