import { ref, watch, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import { useAgentChat } from './useAgentChat';
import { useStreamingResponse } from './useStreamingResponse';
import { parseAgentMessage, extractTextFromInteractionFlow, extractReasoningFromInteractionFlow, hasReasoningContent } from '../utils/messageParser';
import { markdownToHtml, renderRealtimeMarkdown } from '../services/markdownService';
import chatService from '../services/chat';

export function useAgentSidebarLogic(props: any, emit: any) {
  // 当前选择的Agent
  const currentAgent = ref(null);

  // 侧边栏宽度管理
  const sidebarWidth = ref(400); // 默认宽度

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
        if (lastChunk && lastChunk.type === 'reasoning' && lastChunk.content) {
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
            type: 'reasoning' as const,
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
      console.log('[useAgentSidebarLogic] 检测到笔记编辑工具完成，处理结果');
      console.log('[useAgentSidebarLogic] 工具结果原始内容:', toolStatus.result);
      // 返回工具结果以便外部处理
      return { type: 'note_editor_result', result: toolStatus.result };
    }
    
    // 移除对handleToolStatusUpdate的调用，因为在AgentSidebar中已经直接调用了
    // 这里只处理特殊逻辑，UI更新在外层直接处理
    console.log('[useAgentSidebarLogic] handleToolStatus 只处理特殊逻辑，UI更新已在外层处理');
  };

  // 处理文本响应
  const processTextResponse = (textContent: string) => {
    console.log('处理文本响应:', textContent.length, '字符');
    
    // 尝试解析agentResponse，检查是否是JSON结构
    let parsedResponse = null;
    let displayContent = textContent;
    let contentChunks: any[] = [];
    
    try {
      // 尝试解析JSON结构
      parsedResponse = parseAgentMessage(textContent);
      
      if (typeof parsedResponse === 'object' && parsedResponse && parsedResponse.type === 'agent_response') {
        console.log('检测到JSON结构的agent响应，interaction_flow长度:', parsedResponse.interaction_flow?.length || 0);
        
        // 提取纯文本内容用于显示
        displayContent = extractTextFromInteractionFlow(parsedResponse.interaction_flow);
        
        // 将交互流程转换为contentChunks格式
        contentChunks = parsedResponse.interaction_flow.map((segment: any) => {
          if (segment.type === 'text') {
            return {
              type: 'text' as const,
              content: segment.content,
              timestamp: new Date(segment.timestamp)
            };
          } else if (segment.type === 'tool_call') {
            return {
              type: 'tool_status' as const,
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
              type: 'reasoning' as const,
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
          type: 'text' as const,
          content: textContent,
          timestamp: new Date()
        }];
      }
    } catch (error: unknown) {
      console.log('解析agentResponse失败，使用原始内容:', error instanceof Error ? error.message : '未知错误');
      // 解析失败，使用原始内容
      contentChunks = [{
        type: 'text' as const,
        content: textContent,
        timestamp: new Date()
      }];
    }
    
    // 首先查找编辑重新执行的AI消息
    const editingAgentMsgIndex = messages.value.findIndex(msg => 
      msg.type === 'agent' && 
      msg.isTyping && 
      msg.id && 
      (msg.id.includes('edit_agent_') || msg.id.includes('edit_'))
    );
    
    if (editingAgentMsgIndex !== -1) {
      // 更新编辑重新执行的消息
      const currentMsg = messages.value[editingAgentMsgIndex];
      console.log('找到编辑重新执行的消息，更新内容:', currentMsg.id);
      
      // 更新消息内容
      currentMsg.content = displayContent;
      currentMsg.originalContent = textContent; // 保存原始内容
      currentMsg.isTyping = props.isAgentResponding;
      
      // 如果是JSON结构响应，说明是最终的完整响应，直接替换
      if (typeof parsedResponse === 'object' && parsedResponse && parsedResponse.type === 'agent_response') {
        console.log('收到最终JSON结构响应，替换为完整的interaction_flow');
        currentMsg.contentChunks = contentChunks;
      } else {
        // 对于非JSON结构响应（流式文本），智能分段处理
        handleStreamingText(textContent, currentMsg);
      }
      
      console.log('更新编辑重新执行AI消息，索引:', editingAgentMsgIndex);
      console.log('显示内容长度:', displayContent.length);
      console.log('内容块数量:', currentMsg.contentChunks?.length || 0);
      
      // 更新最后处理的响应内容
      lastProcessedResponse.value = textContent;
      return;
    }
    
    // 查找现有的正在进行的AI消息（排除历史消息和编辑消息）
    const existingAgentMsgIndex = messages.value.findIndex(msg => 
      msg.type === 'agent' && 
      msg.isTyping && 
      (!msg.id || (!msg.id.includes('edit_') && !msg.id.includes('edit_agent_') && !msg.id.startsWith('history_')))
    );
    
    if (existingAgentMsgIndex !== -1) {
      // 更新现有消息
      const currentMsg = messages.value[existingAgentMsgIndex];
      
      // 更新消息内容
      currentMsg.content = displayContent;
      currentMsg.originalContent = textContent; // 保存原始内容
      currentMsg.isTyping = props.isAgentResponding;
      
      // 如果是JSON结构响应，说明是最终的完整响应，直接替换
      if (typeof parsedResponse === 'object' && parsedResponse && parsedResponse.type === 'agent_response') {
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
          type: 'agent' as const,
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
  };

  // 发送消息
  const handleSendMessage = (messageData: any) => {
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
    addUserMessage(messageData.content, messageData.agent, messageData.images);
    addAgentMessage(messageData.agent);

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

  // 渲染markdown内容
  const renderMarkdown = (content: string, isTyping = false) => {
    if (!content) return '';
    
    try {
      // 使用优化的实时markdown渲染器
      const htmlContent = renderRealtimeMarkdown(content, isTyping);
      return htmlContent;
    } catch (error) {
      console.error('渲染markdown失败:', error);
      // 如果渲染失败，回退到纯文本显示
      return content.replace(/\n/g, '<br>');
    }
  };

  return {
    // 状态
    currentAgent,
    sidebarWidth,
    messages,
    isEditingMessage,
    editingController,
    lastProcessedResponse,
    
    // 方法
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
  };
} 