import { ref, computed, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import chatService from '../services/chat';

export interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'loading';
  content: string;
  originalContent?: string;
  timestamp: Date;
  baseTimestamp?: Date;
  agent?: any;
  isTyping?: boolean;
  isEditing?: boolean;
  editContent?: string;
  contentChunks?: ContentChunk[];
  lastTextLength?: number;
  reasoningContent?: string;
  reasoningStartTime?: number;
  reasoningEndTime?: number;
  reasoningCompleted?: boolean;
}

export interface ContentChunk {
  type: 'text' | 'tool_status' | 'reasoning';
  content?: string;
  tool_name?: string;
  status?: string;
  tool_call_id?: string;
  timestamp: Date;
  result?: any;
  error?: any;
  segmentIndex?: number;
}

export function useAgentChat() {
  const messages = ref<ChatMessage[]>([]);
  const isEditingMessage = ref(false);
  const editingController = ref<AbortController | null>(null);
  const lastProcessedResponse = ref('');

  // 消息去重函数
  const deduplicateMessages = (messageList: ChatMessage[]) => {
    const seen = new Set();
    return messageList.filter(msg => {
      const key = `${msg.type}_${msg.content}_${msg.timestamp?.getTime() || 0}`;
      if (seen.has(key)) {
        console.log('发现重复消息，已过滤:', msg.id || 'no-id');
        return false;
      }
      seen.add(key);
      return true;
    });
  };

  // 添加用户消息
  const addUserMessage = (content: string, agent: any, images?: any[]) => {
    const currentTime = Date.now();
    
    // 构建消息内容，支持图片数据
    let messageContent = content;
    if (images && images.length > 0) {
      // 构建包含图片和文本的完整消息结构
      const fullMessageContent = {
        "type": "user_message",
        "text_content": content,
        "images": images.map(image => ({
          "url": image.url,
          "name": image.name,
          "size": image.size
        }))
      };
      messageContent = JSON.stringify(fullMessageContent);
    }
    
    const userMessage: ChatMessage = {
      id: `user_${currentTime}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'user',
      content: messageContent,
      timestamp: new Date(),
      agent
    };
    messages.value.push(userMessage);
    console.log('添加用户消息，ID:', userMessage.id, '包含图片:', images?.length || 0);
    return userMessage;
  };

  // 添加AI消息
  const addAgentMessage = (agent: any) => {
    const currentTime = Date.now();
    const baseTimestamp = new Date();
    const agentMessage: ChatMessage = {
      id: `agent_${currentTime + 1}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent',
      content: '',
      timestamp: baseTimestamp,
      baseTimestamp,
      agent,
      isTyping: true,
      contentChunks: []
    };
    messages.value.push(agentMessage);
    return agentMessage;
  };

  // 查找当前正在输入的AI消息
  const getCurrentTypingMessage = () => {
    return messages.value.find(msg => 
      msg.type === 'agent' && 
      msg.isTyping && 
      (!msg.id || (!msg.id.includes('edit_') && !msg.id.startsWith('history_')))
    );
  };

  // 开始编辑消息
  const startEditMessage = (messageObj: ChatMessage) => {
    if (isEditingMessage.value) {
      console.warn('请先完成当前消息的编辑');
      return;
    }
    
    console.log('开始编辑消息:', messageObj);
    messageObj.isEditing = true;
    
    // 如果是包含图片的用户消息，只编辑文本内容
    if (messageObj.type === 'user') {
      try {
        const parsed = JSON.parse(messageObj.content);
        if (parsed.type === 'user_message') {
          // 包含图片的消息，只编辑文本内容
          messageObj.editContent = parsed.text_content || '';
          console.log('检测到包含图片的消息，仅编辑文本内容:', parsed.text_content);
        } else {
          // 纯文本消息
          messageObj.editContent = messageObj.content;
        }
      } catch (error) {
        // 如果解析失败，说明是纯文本消息
        messageObj.editContent = messageObj.content;
      }
    } else {
      // 非用户消息，直接使用原内容
      messageObj.editContent = messageObj.content;
    }
    
    isEditingMessage.value = true;
    
    // 聚焦到编辑框
    nextTick(() => {
      const textareas = document.querySelectorAll('.edit-textarea');
      if (textareas.length > 0) {
        const textarea = textareas[textareas.length - 1] as HTMLTextAreaElement;
        textarea.focus();
        textarea.select();
      }
    });
  };

  // 取消编辑消息
  const cancelEditMessage = (messageObj: ChatMessage) => {
    console.log('取消编辑消息:', messageObj);
    messageObj.isEditing = false;
    messageObj.editContent = '';
    isEditingMessage.value = false;
    
    if (editingController.value) {
      editingController.value.abort();
      editingController.value = null;
    }
  };

  // 获取消息在历史记录中的索引
  const getMessageIndexInHistory = (messageObj: ChatMessage, conversationHistory: any[]) => {
    console.log('=== 开始计算消息ID ===');
    console.log('要编辑的消息内容:', messageObj.content);
    console.log('当前会话历史:', conversationHistory);
    
    if (!conversationHistory || conversationHistory.length === 0) {
      console.log('没有会话历史记录');
      return -1;
    }
    
    // 方法1：通过消息内容精确匹配查找
    for (let i = 0; i < conversationHistory.length; i++) {
      const conversation = conversationHistory[i];
      
      if (conversation.user && conversation.user === messageObj.content && conversation.userMessageId) {
        console.log(`找到匹配的用户消息，对话索引: ${i}, 消息ID: ${conversation.userMessageId}`);
        return conversation.userMessageId;
      }
    }
    
    // 方法2：通过消息ID中的索引位置查找
    if (messageObj.id && messageObj.id.startsWith('history_')) {
      const match = messageObj.id.match(/history_(\d+)_user/);
      if (match) {
        const historyIndex = parseInt(match[1]);
        console.log(`从消息ID提取历史索引: ${historyIndex}`);
        
        if (historyIndex >= 0 && historyIndex < conversationHistory.length) {
          const conversation = conversationHistory[historyIndex];
          if (conversation && conversation.userMessageId) {
            console.log(`通过位置找到消息ID: ${conversation.userMessageId}`);
            return conversation.userMessageId;
          }
        }
      }
    }
    
    // 方法3：使用最后一个用户消息ID
    const lastConversation = conversationHistory[conversationHistory.length - 1];
    if (lastConversation && lastConversation.userMessageId) {
      console.log(`使用最后一个用户消息ID: ${lastConversation.userMessageId}`);
      return lastConversation.userMessageId;
    }
    
    console.log('无法找到任何有效的消息ID');
    return -1;
  };

  // 清空消息
  const clearMessages = () => {
    messages.value = [];
    lastProcessedResponse.value = '';
  };

  // 复制消息
  const copyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      console.log('消息已复制到剪贴板');
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  return {
    messages,
    isEditingMessage,
    editingController,
    lastProcessedResponse,
    deduplicateMessages,
    addUserMessage,
    addAgentMessage,
    getCurrentTypingMessage,
    startEditMessage,
    cancelEditMessage,
    getMessageIndexInHistory,
    clearMessages,
    copyMessage
  };
} 