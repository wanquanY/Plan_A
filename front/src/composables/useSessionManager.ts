import { ref, inject, type Ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import chatService from '../services/chat';
import { formatMessagesToHtml as formatMessagesToHtmlFromService } from '../services/markdownService';

// 定义会话历史记录的类型
interface ConversationHistoryItem {
  user: string;
  agent: string;
  userMessageId?: string;
  agentMessageId?: string;
}

export function useSessionManager() {
  const router = useRouter();
  const route = useRoute();
  
  // 从全局布局获取会话ID和会话列表，添加类型注解
  const currentSessionId = inject<Ref<string | null>>('currentSessionId');
  const sessions = inject<Ref<any[]>>('sessions');
  const fetchSessions = inject<() => Promise<void>>('fetchSessions');

  // 会话相关状态，添加类型定义
  const sidebarConversationHistory = ref<ConversationHistoryItem[]>([]);
  const sidebarHistoryIndex = ref(-1);
  const sidebarHistoryLength = ref(0);
  const sidebarAgentResponse = ref('');
  const sidebarIsAgentResponding = ref(false);

  // 添加当前响应控制器的引用
  const currentResponseController = ref<AbortController | null>(null);
  
  // 添加当前响应的会话ID引用，用于停止时获取正确的会话ID
  const currentResponseConversationId = ref<string | null>(null);
  
  // 添加当前用户消息内容的引用，用于停止时保存
  const currentUserMessageContent = ref<string>('');

  // 获取会话详情
  const fetchSessionDetail = async (sessionId: string) => {
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
  const loadSessionHistoryToSidebar = async (sessionId: string) => {
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
      
      // 初始化当前响应的会话ID
      currentResponseConversationId.value = currentSessionId?.value || null;
      
      // 记录当前用户消息内容
      currentUserMessageContent.value = data.content || '';
      
      // 添加安全超时机制 - 如果6分钟后仍在响应中，强制重置状态
      const safetyTimeoutId = setTimeout(() => {
        if (sidebarIsAgentResponding.value) {
          console.warn('[useSessionManager] 安全超时：6分钟后强制重置响应状态');
          sidebarIsAgentResponding.value = false;
          if (currentResponseController.value) {
            currentResponseController.value.abort();
            currentResponseController.value = null;
          }
          sidebarAgentResponse.value += '\n\n[响应超时，已自动停止]';
        }
      }, 360000); // 6分钟超时
      
      // 获取笔记ID的值
      const noteIdValue = currentNoteId?.value;
      console.log('发送请求时的笔记ID:', noteIdValue);
      
      // 准备聊天请求
      const chatRequest: any = {
        agent_id: data.agentId || data.agent?.id || 1,
        content: data.content,
        session_id: currentSessionId?.value,
        note_id: noteIdValue,
        model: data.model
      };
      
      // 如果有图片数据，添加到请求中
      if (data.images && data.images.length > 0) {
        chatRequest.images = data.images;
        console.log('发送聊天请求包含图片:', data.images.length, '张');
        console.log('图片URL列表:', data.images.map((img: any) => img.url));
      }
      
      console.log('准备发送的聊天请求数据:', JSON.stringify(chatRequest, null, 2));
      
      // 验证关键数据
      console.log('关键数据验证:', {
        '请求中的note_id': chatRequest.note_id,
        '请求中的session_id': chatRequest.session_id,
        '请求中的agent_id': chatRequest.agent_id,
        '当前全局SessionId': currentSessionId?.value,
        '传入的noteId': data.noteId || 'undefined',
        '从noteIdRef获取的值': noteIdValue
      });
      
      // 使用chatService的streamChat方法，保存控制器引用
      currentResponseController.value = await chatService.streamChat(chatRequest, (response, isComplete, conversationId, toolStatus, reasoningContent) => {
        // 流式响应回调
        console.log('收到流式响应:', { response, isComplete, conversationId, toolStatus, reasoningContent });
        
        let content = '';
        
        // 正确解析响应数据格式
        // 现在response是完整的API响应数据，不是字符串
        if (response && response.code === 200 && response.data) {
          const responseData = response.data;
          
          // 优先使用full_content进行累积显示，这是完整的累积内容
          if (responseData.full_content !== undefined) {
            content = responseData.full_content;
          } else if (responseData.message && responseData.message.content) {
            // 如果没有full_content，使用增量的message.content
            content = responseData.message.content;
          }
          
          console.log('useSessionManager 解析到的内容:', {
            full_content: responseData.full_content,
            message_content: responseData.message?.content,
            使用的内容: content,
            内容长度: content.length
          });
        } else if (typeof response === 'string') {
          // 兼容处理：如果直接是字符串（旧格式）
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
          console.log('工具状态详细信息:', JSON.stringify(toolStatus, null, 2));
          
          // 🔧 修复：检查工具状态的数据格式并确保正确传递
          let processedToolStatus = toolStatus;
          
          // 如果工具状态嵌套在data字段中，提取出来
          if (toolStatus.data && toolStatus.data.tool_status) {
            console.log('检测到嵌套的工具状态数据，提取tool_status字段');
            processedToolStatus = toolStatus.data.tool_status;
          }
          
          console.log('处理后的工具状态:', processedToolStatus);
          
          // 注意：不再将工具状态插入到文本中，现在使用 contentChunks 系统
          // 只调用工具状态处理回调，让新的组件系统处理显示
          if (onToolStatus) {
            console.log('调用工具状态处理回调函数');
            onToolStatus(processedToolStatus);
          } else {
            console.warn('没有提供工具状态处理回调函数');
          }
        }
        
        if (content) {
          sidebarAgentResponse.value = content;
          console.log('更新侧边栏响应内容，长度:', content.length);
        }
        
        // 更新会话ID
        if (conversationId && conversationId !== finalConversationId) {
          finalConversationId = conversationId;
          // 同时更新当前响应的会话ID引用
          currentResponseConversationId.value = conversationId;
          console.log('更新会话ID:', finalConversationId);
        }
        
        if (isComplete) {
          console.log('流式响应完成');
          sidebarIsAgentResponding.value = false;
          currentResponseController.value = null; // 清空控制器引用
          clearTimeout(safetyTimeoutId); // 清除安全超时
          
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
              
              // **新增：验证笔记关联**
              if (noteIdValue) {
                try {
                  console.log('🔍 验证笔记关联：开始查询笔记 ', noteIdValue, ' 的关联会话');
                  const noteSessionsResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:1314/api/v1'}/note/${noteIdValue}/sessions`, {
                    headers: {
                      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    }
                  });
                  
                  if (noteSessionsResponse.ok) {
                    const noteSessionsData = await noteSessionsResponse.json();
                    console.log('🔍 笔记关联查询结果:', noteSessionsData);
                    console.log('🔍 关联的会话数量:', noteSessionsData.data?.sessions?.length || 0);
                    console.log('🔍 关联的会话列表:', noteSessionsData.data?.sessions?.map((s: any) => ({ id: s.id, title: s.title })) || []);
                    
                    if (noteSessionsData.data?.sessions?.some((s: any) => s.id === sessionIdToUse)) {
                      console.log('✅ 验证成功：新会话已正确关联到笔记');
                    } else {
                      console.error('❌ 验证失败：新会话未关联到笔记！');
                      console.error('❌ 期望的会话ID:', sessionIdToUse);
                      console.error('❌ 实际关联的会话:', noteSessionsData.data?.sessions || []);
                    }
                  } else {
                    console.error('🔍 查询笔记关联失败:', noteSessionsResponse.status, noteSessionsResponse.statusText);
                  }
                } catch (error) {
                  console.error('🔍 验证笔记关联时出错:', error);
                }
              }
              
              try {
                // 重新获取会话历史记录，包含正确的消息ID
                if (!sessionIdToUse) return;
                const agentHistory = await chatService.getSessionAgentHistory(sessionIdToUse);
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
            
            // 清空当前响应的会话ID引用（响应完成）
            currentResponseConversationId.value = null;
            
            // 清空当前用户消息内容引用
            currentUserMessageContent.value = '';
          }, 800); // 增加延迟时间，确保服务器端消息已完全保存
        }
        
        return { toolStatus }; // 返回工具状态供外部处理
      });
      
    } catch (error: any) {
      console.error('发送消息失败:', error);
      sidebarAgentResponse.value = `抱歉，AI助手出错了: ${error.message || '未知错误'}`;
      sidebarIsAgentResponding.value = false;
      
      // 清空当前响应的会话ID引用
      currentResponseConversationId.value = null;
      
      // 清空当前用户消息内容引用
      currentUserMessageContent.value = '';
    }
  };

  // 停止Agent响应
  const handleStopResponse = async () => {
    console.log('[useSessionManager] 停止Agent响应');
    
    if (currentResponseController.value) {
      console.log('[useSessionManager] 找到当前响应控制器，执行停止');
      
      // 保存当前状态到变量，因为停止后可能会被清空
      // 优先使用当前响应的会话ID，如果没有则使用全局会话ID
      const conversationId = currentResponseConversationId.value || currentSessionId?.value;
      const currentContent = sidebarAgentResponse.value;
      
      // 获取当前用户输入的内容（用于首次聊天时保存）
      const lastUserMessage = currentUserMessageContent.value || 
        (sidebarConversationHistory.value.length > 0 ? 
          sidebarConversationHistory.value[sidebarConversationHistory.value.length - 1]?.user || '' : '');
      
      console.log('[useSessionManager] 停止响应时的状态:', {
        currentResponseConversationId: currentResponseConversationId.value,
        globalSessionId: currentSessionId?.value,
        selectedConversationId: conversationId,
        contentLength: currentContent?.length || 0,
        lastUserMessage: lastUserMessage.substring(0, 50) + '...'
      });
      
      // 停止流式响应
      currentResponseController.value.abort();
      currentResponseController.value = null;
      sidebarIsAgentResponding.value = false;
      
      // 提示用户停止操作正在进行
      message.info('正在停止响应并保存已生成的内容...');
      
      // 如果有内容需要保存，调用后端API保存
      if (currentContent && currentContent.trim() && conversationId) {
        try {
          console.log('[useSessionManager] 调用后端API保存停止时的内容，会话ID:', conversationId);
          const saved = await chatService.stopAndSaveResponse(
            conversationId,
            currentContent,
            lastUserMessage, // 传递用户消息内容，确保首次聊天时用户消息也被保存
            undefined // agent_id 在后端可以从消息历史中推断
          );
          
          if (saved) {
            console.log('[useSessionManager] 停止时的内容已成功保存到数据库');
            message.success('已停止响应并保存内容到历史记录');
            
            // 如果是新建笔记的首次聊天，更新全局会话ID
            if (!currentSessionId?.value && currentResponseConversationId.value && currentSessionId) {
              currentSessionId.value = currentResponseConversationId.value;
              console.log('[useSessionManager] 更新全局会话ID为:', currentResponseConversationId.value);
            }
          } else {
            console.warn('[useSessionManager] 停止时的内容保存失败');
            message.warning('已停止响应，但保存内容时出现问题');
          }
        } catch (error) {
          console.error('[useSessionManager] 保存停止时的内容时出错:', error);
          message.error('已停止响应，但保存内容失败');
        }
      } else {
        console.log('[useSessionManager] 停止时没有内容需要保存或没有会话ID:', {
          hasContent: !!(currentContent && currentContent.trim()),
          hasConversationId: !!conversationId,
          contentPreview: currentContent?.substring(0, 50) + '...'
        });
        
        if (!conversationId) {
          message.warning('已停止响应，但无法保存内容（没有会话ID）');
        } else {
          message.success('已停止响应');
        }
      }
      
      // 延迟刷新历史记录，确保服务器端数据已保存
      setTimeout(async () => {
        try {
          const idToUse = conversationId;
          if (idToUse) {
            console.log('[useSessionManager] 停止后刷新会话历史记录，使用会话ID:', idToUse);
            // 重新获取会话历史记录，确保包含最新的消息（包括被停止的消息）
            const agentHistory = await chatService.getSessionAgentHistory(idToUse);
            if (agentHistory && agentHistory.length > 0) {
              sidebarConversationHistory.value = [...agentHistory];
              sidebarHistoryLength.value = agentHistory.length;
              sidebarHistoryIndex.value = agentHistory.length - 1;
              console.log('[useSessionManager] 停止后刷新会话历史记录成功，条数:', agentHistory.length);
            }
          }
        } catch (error) {
          console.error('[useSessionManager] 停止后刷新会话历史记录失败:', error);
        }
      }, 1000); // 增加延迟，确保后端有足够时间保存数据
      
      // 清空当前响应的会话ID引用
      currentResponseConversationId.value = null;
      
      // 清空当前用户消息内容引用
      currentUserMessageContent.value = '';
      
      console.log('[useSessionManager] Agent响应已停止');
    } else {
      console.log('[useSessionManager] 没有找到当前响应控制器，可能已经完成或未开始');
      message.info('没有正在进行的响应可以停止');
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
        const agentHistory = await chatService.getSessionAgentHistory(currentSessionId.value);
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

  // 清理函数 - 用于清理状态和控制器
  const cleanup = () => {
    console.log('[useSessionManager] 执行清理操作');
    
    // 停止当前响应
    if (currentResponseController.value) {
      currentResponseController.value.abort();
      currentResponseController.value = null;
    }
    
    // 重置响应状态
    sidebarIsAgentResponding.value = false;
    
    // 清空引用
    currentResponseConversationId.value = null;
    currentUserMessageContent.value = '';
    
    console.log('[useSessionManager] 清理操作完成');
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
    handleStopResponse,
    fetchSessions,
    cleanup // 新增清理函数
  };
} 