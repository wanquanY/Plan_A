import { ref, inject, type Ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import chatService from '../services/chat';
import { formatMessagesToHtml as formatMessagesToHtmlFromService } from '../services/markdownService';

// 定义会话历史记录的类型
interface ConversationHistoryItem {
  user: string;
  agent: string;
  userMessageId?: number;
  agentMessageId?: number;
}

export function useSessionManager() {
  const router = useRouter();
  const route = useRoute();
  
  // 从全局布局获取会话ID和会话列表，添加类型注解
  const currentSessionId = inject<Ref<number | string | null>>('currentSessionId');
  const sessions = inject<Ref<any[]>>('sessions');
  const fetchSessions = inject<() => Promise<void>>('fetchSessions');

  // 会话相关状态，添加类型定义
  const sidebarConversationHistory = ref<ConversationHistoryItem[]>([]);
  const sidebarHistoryIndex = ref(-1);
  const sidebarHistoryLength = ref(0);
  const sidebarAgentResponse = ref('');
  const sidebarIsAgentResponding = ref(false);

  // 获取会话详情
  const fetchSessionDetail = async (sessionId: number) => {
    try {
      if (!sessionId) return;
      
      const sessionData = await chatService.getSessionDetail(sessionId);
      
      if (sessionData) {
        if (currentSessionId) {
          currentSessionId.value = sessionId;
        }
        
        if (sessionData.messages && sessionData.messages.length > 0) {
          // 将会话消息转换为HTML格式
          console.log(`格式化${sessionData.messages.length}条消息`);
          
          // 预处理消息内容，移除不必要的空行
          const cleanedMessages = sessionData.messages.map(msg => {
            // 创建一个浅拷贝，以免修改原始数据
            const cleanedMsg = {...msg};
            
            // 移除前后空白
            cleanedMsg.content = cleanedMsg.content.trim();
            
            // 移除多余的换行
            cleanedMsg.content = cleanedMsg.content.replace(/\n{3,}/g, '\n\n');
            
            return cleanedMsg;
          });
          
          const messagesHtml = formatMessagesToHtmlFromService(cleanedMessages, sessionData.title);
          
          return {
            content: messagesHtml,
            title: sessionData.title || '未命名笔记',
            sessionData
          };
        }
      } else {
        throw new Error('获取会话详情失败');
      }
    } catch (error: any) {
      console.error('获取会话详情失败:', error);
      message.error('获取笔记详情失败，请稍后重试');
      throw error;
    }
  };

  // 创建新会话
  const createNewSession = async () => {
    try {
      // 调用创建会话API
      const response = await chatService.createSession('新笔记');
      if (response && response.id) {
        // 创建成功，刷新会话列表并切换到新会话
        if (fetchSessions) {
          await fetchSessions();
        }
        if (currentSessionId) {
          currentSessionId.value = response.id;
        }
        message.success('新笔记创建成功');
        return response;
      } else {
        message.error('创建笔记失败');
      }
    } catch (error: any) {
      console.error('创建笔记失败:', error);
      message.error('创建笔记失败');
      throw error;
    }
  };

  // 清理侧边栏会话历史
  const clearSidebarHistory = () => {
    console.log('清理侧边栏对话历史记录');
    sidebarConversationHistory.value = [];
    sidebarHistoryIndex.value = -1;
    sidebarHistoryLength.value = 0;
    sidebarAgentResponse.value = '';
    sidebarIsAgentResponding.value = false;
  };

  // 加载会话历史记录到侧边栏
  const loadSessionHistoryToSidebar = async (sessionId: number) => {
    try {
      const agentHistory = await chatService.getSessionAgentHistory(sessionId);
      console.log('获取到的会话历史记录:', agentHistory);
      
      if (agentHistory && agentHistory.length > 0) {
        console.log('会话历史记录详情:', agentHistory);
        sidebarConversationHistory.value = [...agentHistory];
        sidebarHistoryLength.value = agentHistory.length;
        sidebarHistoryIndex.value = agentHistory.length - 1; // 显示最新的回复
        console.log(`加载关联会话历史记录，条数: ${agentHistory.length}`);
        console.log('设置后的sidebarConversationHistory:', sidebarConversationHistory.value);
      } else {
        console.log('会话历史记录为空');
        sidebarConversationHistory.value = [];
      }
    } catch (error) {
      console.error('加载关联会话历史记录失败:', error);
      sidebarConversationHistory.value = [];
      throw error;
    }
  };

  // 处理侧边栏发送消息
  const handleSidebarSend = async (data: any, currentNoteId: any, onToolStatus?: (toolStatus: any) => void) => {
    console.log('处理侧边栏发送消息:', data);
    console.log('当前笔记ID:', currentNoteId?.value);
    
    try {
      sidebarIsAgentResponding.value = true;
      sidebarAgentResponse.value = ''; // 清空之前的响应
      let finalConversationId = currentSessionId?.value;
      
      // 获取笔记ID的值
      const noteIdValue = currentNoteId?.value;
      console.log('发送请求时的笔记ID:', noteIdValue);
      
      // 使用chatService的streamChat方法
      const abortController = await chatService.streamChat({
        agent_id: data.agent?.id || 1, // 使用agent ID，如果没有则使用默认值1
        content: data.content,
        conversation_id: currentSessionId?.value ? Number(currentSessionId.value) : undefined,
        note_id: noteIdValue
      }, (response, isComplete, conversationId, toolStatus, reasoningContent) => {
        // 流式响应回调
        console.log('收到流式响应:', { response, isComplete, conversationId, toolStatus, reasoningContent });
        
        let content = '';
        
        // 正确解析响应数据格式
        if (response && response.data && response.data.data) {
          // 优先使用full_content，如果没有则使用message.content
          content = response.data.data.full_content || 
                    (response.data.data.message && response.data.data.message.content) || '';
        } else if (typeof response === 'string') {
          // 兼容处理：如果直接是字符串
          content = response;
        }
        
        // 处理思考内容
        if (reasoningContent) {
          console.log('useSessionManager 收到思考内容:', reasoningContent);
          
          // 通过onToolStatus回调传递思考内容信息（可以扩展这个回调来处理思考内容）
          if (onToolStatus) {
            // 使用特殊的工具状态格式来传递思考内容
            onToolStatus({
              type: 'reasoning_content',
              reasoning_content: reasoningContent,
              status: isComplete ? 'completed' : 'streaming'
            });
          }
        }
        
        // 处理工具状态更新
        if (toolStatus) {
          console.log('useSessionManager 收到工具状态更新:', toolStatus);
          
          // 注意：不再将工具状态插入到文本中，现在使用 contentChunks 系统
          // 只调用工具状态处理回调，让新的组件系统处理显示
          if (onToolStatus) {
            onToolStatus(toolStatus);
          }
        }
        
        if (content) {
          sidebarAgentResponse.value = content;
          console.log('更新侧边栏响应内容，长度:', content.length);
        }
        
        // 更新会话ID
        if (conversationId && conversationId !== finalConversationId) {
          finalConversationId = conversationId;
          console.log('更新会话ID:', finalConversationId);
        }
        
        if (isComplete) {
          console.log('流式响应完成');
          sidebarIsAgentResponding.value = false;
          
          // 注意：不再在末尾插入工具状态HTML，现在使用 contentChunks 系统
          
          // 如果返回了新的会话ID，更新当前会话ID
          if (finalConversationId && currentSessionId && finalConversationId !== currentSessionId.value) {
            currentSessionId.value = finalConversationId;
            // 更新URL
            router.push({
              query: {
                ...route.query,
                id: finalConversationId
              }
            });
            console.log('更新URL会话ID:', finalConversationId);
          }
          
          // 延迟一小段时间后刷新会话历史记录，确保服务器端消息已保存并获取到正确的消息ID
          setTimeout(async () => {
            if (sidebarAgentResponse.value && (finalConversationId || currentSessionId?.value)) {
                             const sessionIdToUse = finalConversationId || currentSessionId?.value;
              console.log('流式输出完成，刷新会话历史记录以获取消息ID，会话ID:', sessionIdToUse);
              
              try {
                // 重新获取会话历史记录，包含正确的消息ID
                const agentHistory = await chatService.getSessionAgentHistory(Number(sessionIdToUse));
                console.log('重新获取到的会话历史记录:', agentHistory);
                
                if (agentHistory && agentHistory.length > 0) {
                  sidebarConversationHistory.value = [...agentHistory];
                  sidebarHistoryLength.value = agentHistory.length;
                  sidebarHistoryIndex.value = agentHistory.length - 1;
                  console.log(`流式输出完成后刷新会话历史记录成功，条数: ${agentHistory.length}`);
                } else {
                  // 如果获取失败，回退到原来的逻辑
                  console.log('获取会话历史记录失败，使用本地添加方式');
                  sidebarConversationHistory.value.push({
                    user: data.content,
                    agent: sidebarAgentResponse.value,
                    userMessageId: undefined, // 新消息暂时没有ID
                    agentMessageId: undefined // 新消息暂时没有ID
                  });
                  sidebarHistoryIndex.value = sidebarConversationHistory.value.length - 1;
                  sidebarHistoryLength.value = sidebarConversationHistory.value.length;
                  console.log('添加到会话历史记录，总条数:', sidebarConversationHistory.value.length);
                }
              } catch (error) {
                console.error('刷新会话历史记录失败，使用本地添加方式:', error);
                // 如果刷新失败，回退到原来的逻辑
                sidebarConversationHistory.value.push({
                  user: data.content,
                  agent: sidebarAgentResponse.value,
                  userMessageId: undefined, // 新消息暂时没有ID
                  agentMessageId: undefined // 新消息暂时没有ID
                });
                sidebarHistoryIndex.value = sidebarConversationHistory.value.length - 1;
                sidebarHistoryLength.value = sidebarConversationHistory.value.length;
                console.log('添加到会话历史记录，总条数:', sidebarConversationHistory.value.length);
              }
            }
          }, 800); // 增加延迟时间，确保服务器端消息已完全保存
        }
        
        return { toolStatus }; // 返回工具状态供外部处理
      });
      
    } catch (error: any) {
      console.error('发送消息失败:', error);
      sidebarAgentResponse.value = `抱歉，AI助手出错了: ${error.message || '未知错误'}`;
      sidebarIsAgentResponding.value = false;
      throw error;
    }
  };

  // 注意：移除了 findInsertionPoints 和 generateToolStatusHtml 函数，
  // 现在使用新的 contentChunks 系统处理工具状态显示

  // 处理侧边栏导航历史
  const handleSidebarNavigateHistory = (payload: any) => {
    console.log('处理侧边栏导航历史:', payload);
    
    if (!sidebarConversationHistory.value || sidebarConversationHistory.value.length === 0) return;

    const { direction } = payload;
    let newIndex = sidebarHistoryIndex.value;

    if (direction === 'prev' && sidebarHistoryIndex.value > 0) {
      newIndex--;
    } else if (direction === 'next' && sidebarHistoryIndex.value < sidebarConversationHistory.value.length - 1) {
      newIndex++;
    }

    if (newIndex !== sidebarHistoryIndex.value) {
      sidebarHistoryIndex.value = newIndex;
      const historicResponse = sidebarConversationHistory.value[newIndex].agent;
      sidebarAgentResponse.value = historicResponse;
      console.log(`导航到历史记录索引: ${newIndex}`);
    }
  };

  // 处理侧边栏编辑消息
  const handleSidebarEditMessage = async (payload: any) => {
    console.log('处理侧边栏编辑消息:', payload);
    
    const { messageIndex, newContent, rerun, refreshHistory } = payload;
    
    // 如果是刷新历史记录的请求
    if (refreshHistory && currentSessionId?.value) {
      console.log('收到刷新历史记录请求，重新获取会话历史');
      try {
        const agentHistory = await chatService.getSessionAgentHistory(Number(currentSessionId.value));
        console.log('重新获取到的会话历史记录:', agentHistory);
        
        if (agentHistory && agentHistory.length > 0) {
          sidebarConversationHistory.value = [...agentHistory];
          sidebarHistoryLength.value = agentHistory.length;
          sidebarHistoryIndex.value = agentHistory.length - 1;
          console.log(`刷新会话历史记录完成，条数: ${agentHistory.length}`);
        }
      } catch (error) {
        console.error('刷新会话历史记录失败:', error);
      }
      return;
    }
    
    // 更新本地会话历史记录
    if (sidebarConversationHistory.value && sidebarConversationHistory.value.length > 0) {
      const historyIndex = Math.floor(messageIndex / 2);
      
      if (historyIndex >= 0 && historyIndex < sidebarConversationHistory.value.length) {
        // 更新历史记录中的用户消息
        sidebarConversationHistory.value[historyIndex].user = newContent;
        
        if (rerun) {
          // 如果重新执行，移除该条目之后的所有历史记录
          sidebarConversationHistory.value = sidebarConversationHistory.value.slice(0, historyIndex + 1);
          sidebarHistoryLength.value = sidebarConversationHistory.value.length;
          sidebarHistoryIndex.value = sidebarConversationHistory.value.length - 1;
          
          // 清除当前显示的AI响应，准备重新开始流式输出
          sidebarAgentResponse.value = '';
          sidebarIsAgentResponding.value = true;
          
          console.log(`编辑消息并重新执行，保留前 ${historyIndex + 1} 条历史记录，清除当前AI响应`);
        } else {
          console.log(`仅编辑消息内容，历史记录索引 ${historyIndex} 已更新`);
        }
      }
    }
  };

  return {
    // 状态
    currentSessionId,
    sessions,
    sidebarConversationHistory,
    sidebarHistoryIndex,
    sidebarHistoryLength,
    sidebarAgentResponse,
    sidebarIsAgentResponding,
    
    // 方法
    fetchSessionDetail,
    createNewSession,
    clearSidebarHistory,
    loadSessionHistoryToSidebar,
    handleSidebarSend,
    handleSidebarNavigateHistory,
    handleSidebarEditMessage,
    fetchSessions
  };
} 