import { nextTick } from 'vue';

export function useAgentSidebarHistory(props: any, dependencies: any) {
  const {
    messages,
    deduplicateMessages,
    clearMessages,
    getCurrentTypingMessage,
    currentAgent,
    getSortedContentChunks,
    parseAgentMessage,
    extractTextFromInteractionFlow
  } = dependencies;

  // 从会话历史初始化聊天记录
  const initializeFromHistory = (forceUpdate = false) => {
    console.log('=== useAgentSidebarHistory: 初始化聊天记录 ===');
    console.log('历史记录数量:', props.conversationHistory?.length || 0);
    console.log('forceUpdate:', forceUpdate);
    console.log('当前isAgentResponding:', props.isAgentResponding);
    
    // 如果当前正在响应且不是强制更新，不要重新初始化
    if (props.isAgentResponding && !forceUpdate) {
      console.log('当前正在响应中，跳过历史记录初始化');
      return;
    }
    
    // 如果有正在进行的AI消息且不是强制更新，也跳过初始化
    const hasActiveAgentMessage = messages.value.some((msg: any) => msg.type === 'agent' && msg.isTyping);
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
    messages.value.forEach((msg: any) => {
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
          type: 'user' as const,
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
        if (typeof parsedMessage === 'object' && parsedMessage && parsedMessage.type === 'agent_response') {
          displayContent = extractTextFromInteractionFlow(parsedMessage.interaction_flow);
          
          // 将交互流程转换为contentChunks格式
          contentChunks = parsedMessage.interaction_flow.map((segment: any) => {
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
          }).filter((chunk: any) => chunk !== null);
        } else {
          // 旧格式，创建简单的文本块
          contentChunks = [{
            type: 'text' as const,
            content: displayContent,
            timestamp: new Date()
          }];
        }
        
        const agentMsg = {
          id: `history_${index}_agent`,
          type: 'agent' as const,
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
      const currentActiveMessages = messages.value.filter((msg: any) => 
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
      const activeMessages = messages.value.filter((msg: any) => 
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
  };

  return {
    initializeFromHistory
  };
} 