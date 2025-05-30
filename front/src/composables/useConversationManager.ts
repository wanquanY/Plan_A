import { ref } from 'vue';

export function useConversationManager() {
  const conversationHistory = ref<Array<{ user: string; agent: string }>>([]);
  const historyDisplayIndex = ref(-1);
  const lastLoadedSessionId = ref<string | number | null>(null);

  const loadConversationHistory = async (sessionId: number | string | null, emit: Function) => {
    if (sessionId && sessionId === lastLoadedSessionId.value) {
      console.log(`会话ID ${sessionId} 已经加载过，跳过重复加载`);
      return;
    }
    
    if (!sessionId) {
      conversationHistory.value = [];
      historyDisplayIndex.value = -1;
      lastLoadedSessionId.value = null;
      console.log('没有会话ID，清空历史记录');
      
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: [],
        length: 0
      });
      return;
    }

    try {
      console.log(`开始加载会话 ${sessionId} 的历史记录`);
      
      const { default: chatService } = await import('../services/chat');
      const history = await chatService.getSessionAgentHistory(Number(sessionId));
      
      if (history && history.length > 0) {
        conversationHistory.value = history;
        historyDisplayIndex.value = history.length - 1;
        lastLoadedSessionId.value = sessionId;
        console.log(`加载了 ${history.length} 条历史记录`);
        
        emit('conversation-history-loaded', {
          sessionId: sessionId,
          history: history,
          length: history.length
        });
      } else {
        conversationHistory.value = [];
        historyDisplayIndex.value = -1;
        lastLoadedSessionId.value = sessionId;
        
        emit('conversation-history-loaded', {
          sessionId: sessionId,
          history: [],
          length: 0
        });
      }
    } catch (error) {
      console.error('加载历史记录失败:', error);
      conversationHistory.value = [];
      historyDisplayIndex.value = -1;
      lastLoadedSessionId.value = sessionId;
      
      emit('conversation-history-loaded', {
        sessionId: sessionId,
        history: [],
        length: 0
      });
    }
  };

  const addToHistory = (userMessage: string, agentResponse: string) => {
    conversationHistory.value.push({
      user: userMessage,
      agent: agentResponse
    });
    historyDisplayIndex.value = conversationHistory.value.length - 1;
    lastLoadedSessionId.value = null;
  };

  const navigateHistory = (direction: 'prev' | 'next') => {
    if (!conversationHistory.value || conversationHistory.value.length === 0) return null;

    let newIndex = historyDisplayIndex.value;

    if (direction === 'prev' && historyDisplayIndex.value > 0) {
      newIndex--;
    } else if (direction === 'next' && historyDisplayIndex.value < conversationHistory.value.length - 1) {
      newIndex++;
    }

    if (newIndex !== historyDisplayIndex.value) {
      historyDisplayIndex.value = newIndex;
      return conversationHistory.value[newIndex].agent;
    }

    return null;
  };

  return {
    conversationHistory,
    historyDisplayIndex,
    lastLoadedSessionId,
    loadConversationHistory,
    addToHistory,
    navigateHistory,
  };
} 