import { message } from 'ant-design-vue';
import { nextTick } from 'vue';
import chatService from '../services/chat';

export function useAgentSidebarMessageEdit(props: any, emit: any, dependencies: any) {
  const {
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
    scrollToBottom,
    renderSpecialComponents,
    handleToolStatusUpdate,
    toolStatusRef
  } = dependencies;

  // 开始编辑消息
  const startEditMessage = (messageObj: any) => {
    if (isEditingMessage.value) {
      console.warn('请先完成当前消息的编辑');
      return;
    }
    
    console.log('开始编辑消息:', messageObj);
    messageObj.isEditing = true;
    
    // 初始化editContent - 这是关键！
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
  const cancelEditMessage = (messageObj: any) => {
    console.log('取消编辑消息:', messageObj);
    messageObj.isEditing = false;
    messageObj.editContent = '';
    isEditingMessage.value = false;
    
    if (editingController.value) {
      editingController.value.abort();
      editingController.value = null;
    }
  };

  // 获取消息在历史记录中的索引（本地实现，因为需要访问props）
  const getMessageIndexInHistoryLocal = (messageObj: any) => {
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

  // 保存编辑消息并重新执行
  const saveEditMessage = async (messageObj: any, editImages?: any[]) => {
    if (!messageObj.editContent?.trim()) {
      message.warning('请输入消息内容');
      return;
    }
    
    if (!props.conversationId) {
      message.error('无法获取会话ID，请重新打开对话');
      return;
    }
    
    try {
      console.log('保存并重新执行消息:', messageObj, '编辑后的图片:', editImages);
      
      const messageIndex = getMessageIndexInHistoryLocal(messageObj);
      if (messageIndex === -1) {
        message.error('无法找到消息在历史记录中的位置');
        return;
      }
      
      // 取消编辑状态
      messageObj.isEditing = false;
      isEditingMessage.value = false;
      
      // 更新消息内容 - 处理包含图片的消息
      let updatedContent = messageObj.editContent.trim();
      if (messageObj.type === 'user') {
        try {
          const parsed = JSON.parse(messageObj.content);
          if (parsed.type === 'user_message') {
            // 包含图片的消息，更新文本内容和图片列表
            parsed.text_content = updatedContent;
            parsed.images = editImages || [];  // 使用编辑后的图片列表
            updatedContent = JSON.stringify(parsed);
            console.log('更新包含图片的消息:', {
              textContent: parsed.text_content,
              imagesCount: parsed.images.length,
              updatedContent
            });
          }
        } catch (error) {
          // 如果解析失败，说明是纯文本消息，直接使用编辑内容
          console.log('纯文本消息，直接更新内容');
        }
      }
      messageObj.content = updatedContent;
      
      // 找到消息在历史记录中的索引
      const currentMessageIndex = messages.value.findIndex((msg: any) => msg.id === messageObj.id);
      if (currentMessageIndex !== -1) {
        messages.value = messages.value.slice(0, currentMessageIndex + 1);
      }
      
      // 通知父组件清除当前AI响应并开始重新执行
      emit('edit-message', {
        messageIndex,
        newContent: messageObj.content,
        rerun: true
      });
      
      // 创建用于编辑重新执行的AI消息，使用特殊ID标识
      const currentTime = Date.now();
      const baseTimestamp = new Date();
      const agentMessage = {
        id: `edit_agent_${currentTime}_${Math.random().toString(36).substr(2, 9)}`, // 添加edit_前缀标识
        type: 'agent' as const,
        content: '',
        timestamp: baseTimestamp,
        baseTimestamp,
        agent: currentAgent.value,
        isTyping: true,
        contentChunks: []
      };
      messages.value.push(agentMessage);
      console.log('创建编辑重新执行的AI消息，ID:', agentMessage.id);
      
      // 滚动到底部
      nextTick(() => {
        scrollToBottom();
      });
      
      // 调用编辑接口（流式响应）
      const editRequest = {
        message_index: messageIndex,
        content: updatedContent,  // 使用更新后的完整内容
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
            console.log('编辑重新执行时收到工具状态:', toolStatus);
            
            // 查找编辑重新执行的AI消息
            const editAgentMsg = messages.value.find((msg: any) => 
              msg.type === 'agent' && 
              msg.isTyping && 
              msg.id && 
              msg.id.includes('edit_agent_')
            );
            
            if (editAgentMsg) {
              console.log('将工具状态添加到编辑重新执行的消息中:', editAgentMsg.id);
              // 直接将工具状态添加到指定的编辑重新执行消息中
              handleToolStatusUpdate(toolStatus, editAgentMsg);
              
              // 同时调用handleToolStatus来处理笔记编辑工具的特殊逻辑
              const toolResult = handleToolStatus(toolStatus);
              if (toolResult && toolResult.type === 'note_editor_result') {
                console.log('编辑重新执行时检测到笔记编辑工具结果，进行特殊处理');
                // 处理笔记编辑预览
                const noteEditData = toolStatusRef?.value?.handleNoteEditorResult(toolResult.result);
                if (noteEditData) {
                  console.log('编辑重新执行：笔记编辑数据处理成功，发射预览事件:', noteEditData);
                  emit('note-edit-preview', noteEditData);
                } else {
                  console.warn('编辑重新执行：笔记编辑数据处理失败');
                }
              }
            } else {
              console.warn('未找到编辑重新执行的消息来处理工具状态');
            }
          }
          
          // 从响应中提取reasoning_content并作为toolStatus处理
          if (response && response.data && response.data.message) {
            const messageData = response.data.message;
            
            // 如果有思考内容，创建reasoning_content类型的toolStatus
            if (messageData.reasoning_content) {
              const reasoningToolStatus = {
                type: 'reasoning_content',
                reasoning_content: messageData.reasoning_content
              };
              handleToolStatus(reasoningToolStatus);
            }
          }
          
          // 解析响应内容 - 修复：直接从response.data获取，而不是response.data.data
          let content = '';
          if (response && response.data) {
            // 优先使用full_content进行累积显示，这是完整的累积内容
            content = response.data.full_content || 
                      (response.data.message && response.data.message.content) || '';
            console.log('编辑重新执行解析响应数据:', {
              has_full_content: !!response.data.full_content,
              full_content_length: response.data.full_content?.length || 0,
              message_content: response.data.message?.content || '',
              使用的内容长度: content.length
            });
          } else if (typeof response === 'string') {
            content = response;
          }
          
          // 查找编辑的AI消息并更新 - 使用特殊的查找逻辑
          const editAgentMsg = messages.value.find((msg: any) => 
            msg.type === 'agent' && 
            msg.isTyping && 
            msg.id && 
            msg.id.includes('edit_agent_')
          );
          
          if (editAgentMsg) {
            console.log('找到编辑重新执行的AI消息，更新内容长度:', content.length, '预览:', content.substring(0, 100));
            
            // 直接使用handleStreamingText处理流式内容，确保内容正确累积
            handleStreamingText(content, editAgentMsg);
            editAgentMsg.isTyping = !isComplete;
            
            console.log('编辑消息更新后，AI消息内容长度:', editAgentMsg.content?.length || 0);
            console.log('编辑消息contentChunks数量:', editAgentMsg.contentChunks?.length || 0);
          } else {
            console.warn('未找到编辑重新执行的AI消息，当前消息列表:', messages.value.map((m: any) => ({
              id: m.id,
              type: m.type,
              isTyping: m.isTyping
            })));
          }
          
          // 滚动到底部
          nextTick(() => {
            scrollToBottom();
            if (isComplete) {
              renderSpecialComponents();
            }
          });
          
          if (isComplete) {
            editingController.value = null;
            isEditingRerun = false;
            
            // 确保AI消息的isTyping状态被正确设置为false
            if (editAgentMsg) {
              console.log('编辑重新执行完成，设置isTyping为false');
              editAgentMsg.isTyping = false;
              
              // 确保所有工具状态都标记为完成状态
              if (editAgentMsg.contentChunks && editAgentMsg.contentChunks.length > 0) {
                console.log('编辑重新执行完成，更新工具状态为完成');
                editAgentMsg.contentChunks.forEach((chunk: any) => {
                  if (chunk.type === 'tool_status' && 
                      (chunk.status === 'preparing' || chunk.status === 'executing' || !chunk.status)) {
                    console.log('编辑重新执行：更新工具状态为完成:', chunk.tool_name, chunk.tool_call_id);
                    chunk.status = 'completed';
                  }
                });
              }
            }
            
            nextTick(() => {
              console.log('编辑重新执行完成，请求刷新会话历史记录');
              emit('edit-message', {
                messageIndex,
                newContent: messageObj.content,
                rerun: true,
                refreshHistory: true
              });
            });
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
  const saveEditMessageOnly = async (messageObj: any, editImages?: any[]) => {
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
        editImages: editImages,
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
        content: messageObj.editContent.trim(),  // 这里先发送纯文本内容，因为图片处理在成功后
        stream: false,
        agent_id: currentAgent.value?.id,
        is_user_message: true,
        rerun: false
      };
      
      // 对于非流式编辑，直接调用chatService的非流式方法
      const result = await chatService.editMessage(props.conversationId, editRequest) as any;
      
      if (result && (result.success || result.data)) {
        // 更新消息内容 - 处理包含图片的消息
        let updatedContent = messageObj.editContent.trim();
        if (messageObj.type === 'user') {
          try {
            const parsed = JSON.parse(messageObj.content);
            if (parsed.type === 'user_message') {
              // 包含图片的消息，更新文本内容和图片列表
              parsed.text_content = updatedContent;
              parsed.images = editImages || [];  // 使用编辑后的图片列表
              updatedContent = JSON.stringify(parsed);
              console.log('仅保存模式：更新包含图片的消息:', {
                textContent: parsed.text_content,
                imagesCount: parsed.images.length,
                updatedContent
              });
            }
          } catch (error) {
            // 如果解析失败，说明是纯文本消息，直接使用编辑内容
            console.log('仅保存模式：纯文本消息，直接更新内容');
          }
        }
        messageObj.content = updatedContent;
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
      
    } catch (error: any) {
      console.error('编辑消息失败:', error);
      message.error('编辑消息失败: ' + (error.message || '未知错误'));
    }
  };

  return {
    startEditMessage,
    cancelEditMessage,
    saveEditMessage,
    saveEditMessageOnly,
    getMessageIndexInHistoryLocal
  };
} 