<template>
  <div class="agent-response-handler">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, createApp, nextTick } from 'vue';
import chatService from '@/services/chat';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import * as agentResponseService from '@/services/agentResponseService';
import { setupMermaidAutoRender } from '@/services/renderService';
import LoadingAnimation from '../rendering/LoadingAnimation.vue';

// 全局注册一个MutationObserver来检测新添加的Mermaid图表并自动渲染
let mermaidObserver = null;
onMounted(() => {
  // 初始化服务
  agentResponseService.initAgentResponseService();
  
  // 使用renderService中的setupMermaidAutoRender来设置自动渲染
  // 但现在会在流式输出结束后才渲染
  mermaidObserver = setupMermaidAutoRender();
  
  // 在组件挂载后，尝试初始渲染所有图表
  setTimeout(() => {
    agentResponseService.renderAllMermaidDiagrams();
  }, 500);
  
  // 设置Agent输入框事件监听
  setupAgentInputEvents();
});

// 组件卸载时清理observer
onUnmounted(() => {
  if (mermaidObserver) {
    if (typeof mermaidObserver.disconnect === 'function') {
      mermaidObserver.disconnect();
    }
    mermaidObserver = null;
  }
});

// 事件声明
const emit = defineEmits(['agent-response', 'agent-response-chunk', 'agent-response-complete', 'agent-response-error', 'agent-tool-status', 'note-content-updated', 'note-edit-preview']);

// 用于存储会话ID和笔记ID
const conversationId = ref('');
const currentNoteId = ref('');
const isProcessing = ref(false);
let fullResponseAccumulator = ''; // Moved to be accessible and resettable

// 用于存储当前响应的DOM元素，以便实时更新
let currentResponseElement = null;

// 设置当前会话ID
const setConversationId = (id) => {
  console.log(`AgentResponseHandler设置会话ID: ${id || 'null'}`);
  conversationId.value = id || '';
};

// 设置当前笔记ID
const setCurrentNoteId = (id) => {
  console.log(`AgentResponseHandler设置笔记ID: ${id || 'null'}`);
  currentNoteId.value = id || '';
};

// 获取当前笔记ID
const getCurrentNoteId = () => {
  return currentNoteId.value;
};

/**
 * 实时更新响应内容的markdown渲染
 * @param element 响应元素
 * @param content 累积的内容
 */
const updateResponseContent = (element, content) => {
  if (!element) return;
  
  try {
    // 使用agentResponseService处理markdown
    const processedHtml = agentResponseService.processMarkdown(content);
    
    // 更新DOM内容
    element.innerHTML = processedHtml;
    
    // 延迟渲染特殊组件（在内容更新后）
    setTimeout(() => {
      // 渲染代码块
      agentResponseService.processRenderedHtml(processedHtml, element, false);
    }, 100);
  } catch (error) {
    console.error('更新响应内容失败:', error);
    // 如果处理失败，使用简单的换行处理
    element.innerHTML = content.replace(/\n/g, '<br>');
  }
};

// 创建加载动画元素
const createLoadingElement = () => {
  // 创建一个包裹元素
  const wrapper = document.createElement('span');
  wrapper.className = 'loading-animation-container';
  
  // 创建一个新的Vue应用
  const loadingApp = createApp(LoadingAnimation, { 
    type: 'dots',
    inline: true
  });
  
  // 将Vue应用挂载到包裹元素
  loadingApp.mount(wrapper);
  
  return wrapper;
};

// 移除加载动画
const removeLoadingElement = (element) => {
  if (!element) return;
  
  // 获取可能已挂载的Vue应用实例
  const vueApp = element.__vue_app__;
  if (vueApp) {
    // 卸载Vue应用
    vueApp.unmount();
  }
  
  // 从DOM中移除元素
  if (element.parentNode) {
    element.parentNode.removeChild(element);
  }
};

// 在AgentResponseHandler.vue中修复handleChat方法
// 添加一个安全处理selection的辅助函数
const safelyManageSelection = (callback) => {
  try {
    const selection = window.getSelection();
    if (selection && typeof selection.removeAllRanges === 'function') {
      callback(selection);
    } else {
      console.warn('Selection对象不可用或缺少removeAllRanges方法');
    }
  } catch (error) {
    console.error('处理selection时出错:', error);
  }
};

// 处理笔记编辑工具结果的函数
const handleNoteEditorResult = (toolResult) => {
  console.log('[AgentResponseHandler] 处理笔记编辑工具结果:', toolResult);
  console.log('[AgentResponseHandler] 工具结果类型:', typeof toolResult);
  console.log('[AgentResponseHandler] 工具结果内容:', JSON.stringify(toolResult, null, 2));
  
  try {
    let resultData = toolResult;
    
    // 如果结果是字符串，尝试解析为JSON
    if (typeof toolResult === 'string') {
      try {
        resultData = JSON.parse(toolResult);
        console.log('[AgentResponseHandler] 解析JSON后的结果:', resultData);
      } catch (e) {
        console.warn('[AgentResponseHandler] 无法解析工具结果为JSON:', e);
        return;
      }
    }
    
    console.log('[AgentResponseHandler] 检查编辑结果字段:', {
      success: resultData?.success,
      note_id: resultData?.note_id,
      content_exists: resultData?.content !== undefined,
      content_length: resultData?.content?.length || 0,
      is_preview: resultData?.is_preview
    });
    
    // 检查是否是成功的笔记编辑结果
    if (resultData && resultData.success && resultData.note_id && resultData.content !== undefined) {
      console.log('[AgentResponseHandler] 检测到成功的笔记编辑，准备发射预览事件');
      console.log('[AgentResponseHandler] 当前笔记ID:', currentNoteId.value);
      console.log('[AgentResponseHandler] 编辑的笔记ID:', resultData.note_id);
      
      const previewData = {
        noteId: resultData.note_id,
        content: resultData.content,
        title: resultData.title,
        editType: resultData.edit_type,
        changes: resultData.changes,
        timestamp: Date.now()
      };
      
      console.log('[AgentResponseHandler] 准备发射的预览数据:', previewData);
      
      // 发射预览事件而不是直接更新内容
      emit('note-edit-preview', previewData);
      
      console.log('[AgentResponseHandler] 已发射note-edit-preview事件');
    } else {
      console.log('[AgentResponseHandler] 编辑结果不符合预览条件，跳过预览');
      console.log('[AgentResponseHandler] 检查结果详情:', {
        hasResult: !!resultData,
        hasSuccess: resultData?.success,
        hasNoteId: !!resultData?.note_id,
        hasContent: resultData?.content !== undefined
      });
    }
  } catch (error) {
    console.error('[AgentResponseHandler] 处理笔记编辑结果时出错:', error);
  }
};

// 修改handleChat方法，增加对selection的安全处理
const handleChat = async (agentId, userInput, editor, range) => {
  if (isProcessing.value) {
    console.warn('AI正在处理中，请等待上一个请求完成');
    return;
  }
  
  // 设置为处理中状态
  isProcessing.value = true;
  
  try {
    // 生成响应元素的唯一ID
    const responseId = `agent-response-${Date.now()}`;
    
    // 确保范围有效
    if (!range) {
      console.warn('未提供有效的选择范围，将尝试使用当前选择');
      const currentSelection = window.getSelection();
      if (currentSelection && currentSelection.rangeCount > 0) {
        range = currentSelection.getRangeAt(0);
      } else {
        // 无法获取范围，创建一个新范围指向编辑器末尾
        if (editor) {
          range = document.createRange();
          range.selectNodeContents(editor);
          range.collapse(false); // 折叠到末尾
        } else {
          console.error('无法获取有效范围且未提供editor参数');
          isProcessing.value = false;
          return;
        }
      }
    }
    
    // 创建一个新的选择对象
    let selection;
    try {
      selection = window.getSelection();
      if (!selection) throw new Error('无法获取Selection对象');
    } catch (error) {
      console.error('获取Selection对象失败:', error);
      isProcessing.value = false;
      return;
    }
    
    // 安全地处理选择范围
    safelyManageSelection((selection) => {
      // 删除所有现有选区
      selection.removeAllRanges();
      // 添加我们的范围
      selection.addRange(range.cloneRange());
    });
    
    // 处理输入内容
    const processedInput = agentResponseService.processUserInput(userInput);
    
    // 创建响应容器，并插入到当前选择位置
    const responseContainer = document.createElement('div');
    responseContainer.className = 'agent-response-container';
    
    // 创建响应段落，添加加载动画
    const responseParagraph = document.createElement('p');
    responseParagraph.className = 'agent-response-paragraph';
    responseParagraph.id = responseId; // 添加唯一ID以便后续查找
    responseParagraph.appendChild(createLoadingElement());
    
    // 将响应容器添加到响应段落
    responseContainer.appendChild(responseParagraph);
    
    // 使用当前选择的范围插入响应容器
    try {
      range.deleteContents();
      range.insertNode(responseContainer);
      
      // 更新范围指向响应容器后面
      range.setStartAfter(responseContainer);
      range.collapse(true);
      
      // 安全地更新选择
      safelyManageSelection((selection) => {
        selection.removeAllRanges();
        selection.addRange(range);
      });
      
      // 触发编辑器内容更新事件
      setTimeout(() => {
        const editorContent = responseContainer.closest('.editor-content');
        if (editorContent) {
          editorContent.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, 0);
      
      // 更新触发聊天请求
      triggerChatRequest(agentId, processedInput, responseParagraph);
      
    } catch (error) {
      console.error('插入响应容器时出错:', error);
      isProcessing.value = false;
    }
  } catch (error) {
    console.error('处理聊天请求时出错:', error);
    isProcessing.value = false;
  }
};

// 设置Agent输入框事件监听
const setupAgentInputEvents = () => {
  // 使用事件委托，监听document上的事件
  document.addEventListener('keydown', (event) => {
    // 检查事件目标是否是agent-input类的输入框
    if (event.target && (event.target as HTMLElement).classList.contains('agent-input')) {
      const input = event.target as HTMLInputElement;
      
      // 跳过没有关联Agent的输入框
      if (input.classList.contains('no-agent')) {
        return;
      }
      
      // 按Enter键发送消息
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // 阻止默认的换行行为
        
        // 从输入框获取Agent ID
        const agentId = input.getAttribute('data-agent-id');
        if (agentId) {
          // 获取编辑器引用
          const editorRef = input.closest('.editor-content');
          if (editorRef) {
            handleInputChat(input, agentId, editorRef);
          }
        }
      }
    }
  });
  
  // 监听发送按钮点击事件
  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
    if (target && target.classList.contains('agent-send-button') && !target.disabled) {
      // 获取相关的输入框
      const inputContainer = target.closest('.agent-input-container');
      if (inputContainer) {
        const input = inputContainer.querySelector('.agent-input') as HTMLInputElement;
        
        // 跳过没有关联Agent的输入框
        if (input && !input.classList.contains('no-agent')) {
          const agentId = input.getAttribute('data-agent-id');
          if (agentId) {
            // 获取编辑器引用
            const editorRef = input.closest('.editor-content');
            if (editorRef) {
              handleInputChat(input, agentId, editorRef);
            }
          }
        }
      }
    }
  });
};

// 处理输入框中的聊天消息
const handleInputChat = async (inputElement, agentId, userInput, containerElement) => {
  if (isProcessing.value || !userInput.trim() || !agentId) return;
  
  // 处理用户输入，自动检测代码块语言
  const processedInput = agentResponseService.processUserInput(userInput);
  
  try {
    isProcessing.value = true;
    console.log(`发送消息到助手，agentId: ${agentId}, 会话ID: ${conversationId.value || '新会话'}, 笔记ID: ${currentNoteId.value || '无'}, 内容长度: ${processedInput.length}`);
    
    // 禁用输入框和发送按钮，显示处理中状态
    if (inputElement) {
      inputElement.disabled = true;
      inputElement.placeholder = '处理中...';
      
      // 禁用发送按钮
      const sendButton = containerElement?.querySelector('.agent-send-button');
      if (sendButton) {
        sendButton.disabled = true;
      }
    }
    
    // 创建响应段落
    const responseParagraph = document.createElement('div');
    responseParagraph.className = 'agent-response-paragraph';
    responseParagraph.innerHTML = '<div class="agent-response-loading">AI思考中...</div>';
    
    // 如果有容器元素，将响应段落插入到容器元素后面
    if (containerElement && containerElement.parentNode) {
      containerElement.parentNode.insertBefore(responseParagraph, containerElement.nextSibling);
      
      // 添加样式，使容器不可编辑
      containerElement.classList.add('processing');
    }
    
    // 准备发送数据
    const payload = {
      prompt: processedInput,
      agent_id: agentId,
      session_id: conversationId.value || null,
      note_id: currentNoteId.value
    };
    
    // 发送请求
    const response = await apiService.post('/completions', payload);
    console.log('AI响应:', response.data);
    
    // 处理响应
    if (response.data && response.data.data) {
      const completionData = response.data.data;
      
      // 保存会话ID
      if (completionData.session_id) {
        conversationId.value = completionData.session_id;
        localStorage.setItem('lastConversationId', completionData.session_id);
        console.log(`更新会话ID: ${conversationId.value}`);
      }
      
      // 更新响应内容
      responseParagraph.innerHTML = '';
      responseParagraph.className = 'agent-response-paragraph';
      
      // 创建响应头部
      const headerDiv = document.createElement('div');
      headerDiv.className = 'agent-response-header';
      
      // 添加Agent头像和名称
      const agentHeader = document.createElement('div');
      agentHeader.className = 'agent-header';
      
      const agentAvatar = document.createElement('img');
      agentAvatar.className = 'agent-avatar';
      agentAvatar.src = completionData.agent?.avatar_url || 'https://placehold.co/40x40?text=AI';
      agentAvatar.alt = 'Agent Avatar';
      agentAvatar.onerror = function() {
        this.src = 'https://placehold.co/40x40?text=AI';
      };
      
      const agentName = document.createElement('span');
      agentName.className = 'agent-name';
      agentName.textContent = completionData.agent?.name || 'AI助手';
      
      agentHeader.appendChild(agentAvatar);
      agentHeader.appendChild(agentName);
      headerDiv.appendChild(agentHeader);
      
      // 添加响应内容
      const contentDiv = document.createElement('div');
      contentDiv.className = 'agent-response-content';
      contentDiv.innerHTML = agentResponseService.processMarkdown(completionData.completion || '');
      
      // 添加到响应段落
      responseParagraph.appendChild(headerDiv);
      responseParagraph.appendChild(contentDiv);
      
      // 渲染Mermaid图表
      setTimeout(() => {
        agentResponseService.renderMermaidDiagrams();
      }, 100);
    }
  } catch (error) {
    console.error('处理AI助手响应时出错:', error);
    
    // 创建错误响应
    const errorDiv = document.createElement('div');
    errorDiv.className = 'agent-response-error';
    errorDiv.innerHTML = '处理请求时出错，请重试。';
    
    // 如果有容器元素，将错误消息插入到容器元素后面
    if (containerElement && containerElement.parentNode) {
      containerElement.parentNode.insertBefore(errorDiv, containerElement.nextSibling);
    }
  } finally {
    isProcessing.value = false;
    
    // 重置输入框状态
    if (inputElement) {
      inputElement.value = '';
      inputElement.disabled = false;
      inputElement.placeholder = `问${inputElement.getAttribute('data-agent-name') || 'AI助手'}...`;
      
      // 启用发送按钮
      const sendButton = containerElement?.querySelector('.agent-send-button');
      if (sendButton) {
        sendButton.disabled = false;
      }
      
      // 恢复容器样式
      if (containerElement) {
        containerElement.classList.remove('processing');
      }
      
      // 聚焦到输入框
      setTimeout(() => {
        inputElement.focus();
      }, 0);
    }
  }
};

// 添加triggerChatRequest函数，将流式响应处理分离为单独函数
const triggerChatRequest = async (agentId, userInputContent, responseParagraph = null, model = null) => {
  if (isProcessing.value) {
    console.warn('[AgentResponseHandler] Still processing a previous request.');
    return;
  }
  isProcessing.value = true;
  let streamSignaledEnd = false; // Flag to ensure end signals (complete/error) are sent once
  fullResponseAccumulator = ''; // Reset accumulator for this new request

  // 保存当前响应元素的引用，用于实时更新
  currentResponseElement = responseParagraph;

  console.log(`[AgentResponseHandler] Triggering chat request. AgentID: ${agentId}, ConvID: ${conversationId.value}, NoteID: ${currentNoteId.value}, Model: ${model || '默认'}`);

  try {
    const chatRequest = {
      agent_id: agentId,
      content: userInputContent,
      session_id: conversationId.value || null,
      note_id: currentNoteId.value || null,
      model: model,
      images: chatImages.value.length > 0 ? chatImages.value : undefined
    };

    const streamCallback = async (response, isComplete, convId, toolStatus) => {
      if (streamSignaledEnd) {
        console.log('[AgentResponseHandler] streamCallback called after stream already signaled end. Ignoring.');
        return;
      }

      try {
        // 现在response是完整的API响应数据
        const data = (response && response.code === 200 && response.data) ? response.data : {};
        let chunkContent = '';
        
        console.log('[AgentResponseHandler] 流式响应数据:', {
          has_response: !!response,
          response_code: response?.code,
          has_data: !!response?.data,
          full_content_length: data.full_content?.length || 0,
          message_content: data.message?.content || '',
          done: data.done
        });
        
        // 处理工具状态更新
        if (toolStatus) {
          console.log('[AgentResponseHandler] 收到工具状态更新:', toolStatus);
          console.log('[AgentResponseHandler] 工具状态详情:', {
            type: toolStatus.type,
            tool_name: toolStatus.tool_name,
            status: toolStatus.status,
            tool_call_id: toolStatus.tool_call_id,
            has_result: !!toolStatus.result,
            result_length: toolStatus.result ? JSON.stringify(toolStatus.result).length : 0
          });
          
          // 检查是否是笔记编辑工具的完成状态
          if (toolStatus.tool_name === 'note_editor' && toolStatus.status === 'completed' && toolStatus.result) {
            console.log('[AgentResponseHandler] 检测到笔记编辑工具完成，处理结果');
            console.log('[AgentResponseHandler] 工具结果原始内容:', toolStatus.result);
            handleNoteEditorResult(toolStatus.result);
          } else if (toolStatus.tool_name === 'note_editor') {
            console.log('[AgentResponseHandler] 笔记编辑工具状态不满足条件:', {
              tool_name: toolStatus.tool_name,
              status: toolStatus.status,
              has_result: !!toolStatus.result
            });
          }
          
          emit('agent-tool-status', toolStatus);
        }
        
        // 优先使用full_content进行累积显示
        if (data.full_content !== undefined) {
          // 使用完整的累积内容直接更新显示
          const currentFullContent = data.full_content;
          
          // 实时更新响应内容的markdown渲染
          if (currentResponseElement) {
            // 移除加载动画（如果存在）
            const loadingElement = currentResponseElement.querySelector('.loading-animation-container, .agent-response-loading');
            if (loadingElement) {
              loadingElement.remove();
            }
            
            // 实时渲染完整的累积内容
            updateResponseContent(currentResponseElement, currentFullContent);
          }
          
          // 计算增量部分用于事件发射
          if (currentFullContent.length > fullResponseAccumulator.length) {
            chunkContent = currentFullContent.substring(fullResponseAccumulator.length);
            fullResponseAccumulator = currentFullContent; // 更新累积器
          }
        } else if (data.message && data.message.content) {
          // 如果没有full_content，使用增量的message.content
          chunkContent = data.message.content;
          fullResponseAccumulator += chunkContent;
          
          // 实时更新响应内容的markdown渲染
          if (currentResponseElement) {
            // 移除加载动画（如果存在）
            const loadingElement = currentResponseElement.querySelector('.loading-animation-container, .agent-response-loading');
            if (loadingElement) {
              loadingElement.remove();
            }
            
            // 实时渲染累积的内容
            updateResponseContent(currentResponseElement, fullResponseAccumulator);
          }
        }
        
        const isStreamDone = data.done || isComplete;

        if (chunkContent) {
          emit('agent-response-chunk', chunkContent);
        }

        if (isStreamDone) {
          streamSignaledEnd = true;
          // 确保最终内容是完整的
          const finalContent = data.full_content || fullResponseAccumulator;
          
          console.log('[AgentResponseHandler] 流式响应完成，最终内容长度:', finalContent.length);
          
          // 最终渲染完整内容
          if (currentResponseElement) {
            updateResponseContent(currentResponseElement, finalContent);
            
            // 流式响应结束后，立即渲染特殊组件，不要延迟
            nextTick(() => {
              agentResponseService.processRenderedHtml(finalContent, currentResponseElement, true);
              
              // 立即触发特殊组件渲染
              nextTick(() => {
                const { renderContentComponents } = import('../../services/renderService');
                renderContentComponents.then(module => {
                  module.renderContentComponents(true);
                });
              });
            });
          }
          
          console.log(`[AgentResponseHandler] Stream ended. Emitting complete. ConvID: ${convId}, Response: ${finalContent}`);
          emit('agent-response-complete', { responseText: finalContent, conversationId: convId });
        }
      } catch (errorInCallback) {
        if (!streamSignaledEnd) {
          streamSignaledEnd = true;
          console.error('[AgentResponseHandler] Error in streamCallback, emitting agent-response-error:', errorInCallback);
          emit('agent-response-error', errorInCallback);
        }
      }
    };

    // This now directly calls the service that handles streaming and uses the callback
    await chatService.streamChat(chatRequest, streamCallback);

  } catch (error) {
    console.error('[AgentResponseHandler] Error in triggerChatRequest:', error);
    emit('agent-response-error', error);
  } finally {
    isProcessing.value = false;
    // 清理当前响应元素引用
    currentResponseElement = null;
    console.log('[AgentResponseHandler] triggerChatRequest finally block. streamSignaledEnd:', streamSignaledEnd);
  }
};

const exposedMethods = {
  findLastMention: agentResponseService.findLastMention,
  extractUserInput: agentResponseService.extractUserInput,
  handleChat,
  isProcessing: isProcessing,
  setConversationId,
  setCurrentNoteId,
  getCurrentNoteId,
  ensureCodeBlocksHaveLanguage: agentResponseService.ensureCodeBlocksHaveLanguage,
  renderMermaidDiagrams: agentResponseService.renderMermaidDiagrams,
  setupCodeCopyButtons: agentResponseService.setupCodeCopyButtons,
  setupCodeBlocks: agentResponseService.setupCodeBlocks,
  processRenderedHtml: agentResponseService.processRenderedHtml,
  forceRenderDiagrams: agentResponseService.forceRenderDiagrams,
  handleInputChat,
  triggerChatRequest: triggerChatRequest
};

defineExpose(exposedMethods);
</script>

<style scoped>
.agent-response-handler {
  display: contents;
}

:deep(.agent-response-paragraph) {
  margin: 0 0 12px;
  white-space: normal;
  line-height: 1.5;
  padding: 10px 14px;
  background-color: #f8f9fa;
  border-left: 3px solid #1677ff;
  border-radius: 0 4px 4px 0;
  position: relative;
  margin-top: 6px;
  outline: none;
}

:deep(.agent-response-paragraph:focus) {
  background-color: #f0f7ff;
  border-left-color: #40a9ff;
}

:deep(.mermaid-container) {
  margin: 1em 0;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 15px;
  border: 1px solid #eaecef;
  position: relative;
  text-align: center;
}

:deep(.mermaid) {
  display: inline-block !important;
  text-align: center;
  overflow: visible;
  max-width: 100%;
  margin: 0 auto;
}

:deep(.mermaid svg) {
  display: inline-block !important;
  margin: 0 auto !important;
  max-width: 100%;
}

:deep(.copy-button) {
  position: absolute;
  top: 5px;
  right: 5px;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

:deep(.copy-button:hover) {
  opacity: 1;
  background-color: #e0e0e0;
}

/* 思维导图组件样式 */
:deep(.markmap-component-wrapper),
:deep(.mark-map-component) {
  margin: 1em 0;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 5px;
  overflow: hidden;
  border: 1px solid #eaecef;
  min-height: 200px; /* 减少最小高度 */
  position: relative;
}

:deep(.markmap-svg) {
  width: 100%;
  min-height: 200px; /* 减少最小高度 */
  height: auto; /* 添加自适应高度 */
  outline: none;
  transition: height 0.3s ease; /* 添加过渡效果 */
}

/* 隐藏工具栏，使用单个按钮代替 */
:deep(.markmap-toolbar) {
  display: none !important;
}

/* 移除冗余的按钮样式 */
:deep(.markmap-copy-button),
:deep(.copy-button) {
  display: none !important;
}

:deep(.markdown-content) {
  /* Markdown基本样式 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  color: #333;
  
  /* 标题样式 */
  & h1 {
    font-size: 2em;
    margin: 0.4em 0;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.2em;
  }
  
  & h2 {
    font-size: 1.5em;
    margin: 0.5em 0;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.2em;
  }
  
  & h3 {
    font-size: 1.25em;
    margin: 0.6em 0;
  }
  
  & h4 {
    font-size: 1em;
    margin: 0.7em 0;
  }
  
  /* 段落样式 */
  & p {
    margin: 0.5em 0;
  }
  
  /* 列表样式 */
  & ul, & ol {
    padding-left: 1.5em;
    margin: 0.6em 0;
  }
  
  & li {
    margin: 0.3em 0;
  }
  
  /* 代码块样式 */
  & pre {
    background-color: #f6f8fa;
    border-radius: 3px;
    padding: 12px;
    overflow: auto;
    margin: 0.6em 0;
    font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 85%;
  }
  
  & code {
    background-color: rgba(27, 31, 35, 0.05);
    border-radius: 3px;
    font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
    padding: 0.2em 0.4em;
    font-size: 85%;
  }
  
  & pre > code {
    background-color: transparent;
    padding: 0;
  }
  
  /* 引用样式 */
  & blockquote {
    margin: 0.6em 0;
    padding: 0 0.8em;
    color: #6a737d;
    border-left: 0.25em solid #dfe2e5;
  }
  
  /* 表格样式 */
  & table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.6em 0;
  }
  
  & th, & td {
    padding: 4px 10px;
    border: 1px solid #dfe2e5;
  }
  
  & th {
    background-color: #f6f8fa;
  }
  
  & tr:nth-child(even) {
    background-color: #f6f8fa;
  }
  
  /* 水平线样式 */
  & hr {
    height: 0.25em;
    padding: 0;
    margin: 16px 0;
    background-color: #e1e4e8;
    border: 0;
  }
  
  /* 链接样式 */
  & a {
    color: #0366d6;
    text-decoration: none;
  }
  
  & a:hover {
    text-decoration: underline;
  }
  
  /* 图片样式 */
  & img {
    max-width: 100%;
    box-sizing: border-box;
    background-color: #fff;
  }
  
  /* mermaid图表容器样式 */
  & .mermaid-wrapper {
    margin: 0.6em 0;
    position: relative;
    background-color: #f6f8fa;
    border-radius: 3px;
    padding: 15px;
    overflow: auto;
  }
  
  & .mermaid {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
  
  & .mermaid-wrapper .code-copy-button {
    top: 5px;
    right: 5px;
    background-color: rgba(246, 248, 250, 0.8);
  }
}

/* 设置全局的Mermaid SVG样式，确保任何地方的Mermaid图表都居中 */
:global(svg[id^="mermaid-"]) {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100% !important;
  width: fit-content !important;
}

:global(svg[id^="mermaid-"] > *) {
  margin: 0 auto !important;
}

/* 设置全局的Markmap SVG样式 */
:global(svg[id^="markmap-"]) {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100%;
}

:deep(.loading-animation-container) {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
  margin-left: 6px;
  color: #1677ff;
  height: 20px;
  padding: 0 4px;
  border-radius: 3px;
  background-color: rgba(22, 119, 255, 0.08);
  animation: pulse-bg 2s infinite ease-in-out;
}

@keyframes pulse-bg {
  0%, 100% {
    background-color: rgba(22, 119, 255, 0.08);
  }
  50% {
    background-color: rgba(22, 119, 255, 0.15);
  }
}
</style> 