<template>
  <div class="agent-response-handler">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, createApp } from 'vue';
import chatService from '@/services/chat';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import * as agentResponseService from '@/services/agentResponseService';
import { setupMermaidAutoRender } from '@/services/renderService';
import LoadingAnimation from './LoadingAnimation.vue';

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
const emit = defineEmits(['agent-response']);

// 用于存储会话ID和笔记ID
const conversationId = ref('');
const currentNoteId = ref('');
const isProcessing = ref(false);

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
      conversation_id: conversationId.value || null,
      note_id: currentNoteId.value
    };
    
    // 发送请求
    const response = await apiService.post('/completions', payload);
    console.log('AI响应:', response.data);
    
    // 处理响应
    if (response.data && response.data.data) {
      const completionData = response.data.data;
      
      // 保存会话ID
      if (completionData.conversation_id) {
        conversationId.value = completionData.conversation_id;
        localStorage.setItem('lastConversationId', completionData.conversation_id.toString());
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
const triggerChatRequest = async (agentId, processedInput, responseParagraph) => {
  try {
    // 确保响应段落存在
    if (!responseParagraph || !responseParagraph.id) {
      console.error('响应段落不存在或没有ID');
      isProcessing.value = false;
      return;
    }
    
    const responseId = responseParagraph.id;
    
    // 准备聊天请求
    const chatRequest = {
      content: processedInput,
      stream: true,
      agent_id: parseInt(agentId)
    };
    
    // 如果有会话ID，则添加到请求中
    if (conversationId.value && conversationId.value !== 'null' && conversationId.value !== 'undefined') {
      chatRequest.conversation_id = parseInt(conversationId.value);
      console.log(`使用已有会话ID: ${chatRequest.conversation_id}`);
    } else {
      // 无会话ID或会话ID无效，则传0表示创建新会话
      chatRequest.conversation_id = 0; 
      console.log(`新建笔记使用conversation_id=0表示创建新会话`);
      
      // 如果没有会话ID但有笔记ID，则添加笔记ID到请求中
      if (currentNoteId.value) {
        console.log(`正在创建新会话，关联到笔记ID: ${currentNoteId.value}`);
        chatRequest.note_id = parseInt(currentNoteId.value);
      }
    }
    
    console.log(`发送聊天请求:`, chatRequest);
    
    // 处理流式响应的回调函数
    let previousContent = '';
    const streamCallback = async (response, isComplete, convId) => {
      try {
        // 提取content, isEnd和convId
        const data = response.data?.data || {};
        const content = data.full_content || '';
        const isEnd = data.done || isComplete;
        
        console.log(`收到流响应: convId=${convId}, isEnd=${isEnd}, 内容长度=${content.length}`);
        
        // 提取agent信息并发送事件
        if (data.agent_info) {
          emit('agent-response', { 
            agent_info: data.agent_info,
            message: data.message || {}
          });
        }
        
        // 确保响应段落存在且仍然在DOM中
        const responseParagraph = document.getElementById(responseId);
        if (!responseParagraph) {
          console.warn('响应段落已从DOM中移除或找不到');
          return;
        }
        
        // 检查是否仍有加载动画
        const loadingElement = responseParagraph.querySelector('.loading-animation-container');
        const shouldForceUpdate = !!loadingElement; // 如果存在加载动画，则需要强制更新
        
        // 如果内容没有变化，不更新DOM（但如果是结束消息或需要强制更新，则始终更新）
        if (content === previousContent && !isEnd && !shouldForceUpdate) {
          return;
        }
        
        console.log(`更新响应内容，长度: ${content.length}, 是否结束: ${isEnd}, 会话ID: ${convId}`);
        
        try {
          // 首先处理内容，识别代码块语言
          const processedContent = agentResponseService.processUserInput(content || "");
          
          // 将Markdown转换为HTML并进行安全处理
          let htmlContent = marked(processedContent || "");
          
          // DOMPurify消毒处理防止XSS攻击
          if (typeof DOMPurify !== 'undefined') {
            htmlContent = DOMPurify.sanitize(htmlContent, {
              ADD_ATTR: ['class', 'data-language', 'id', 'data-code', 'data-mermaid-code', 'data-original-content'], // 允许自定义属性
              ADD_TAGS: ['code', 'pre', 'div', 'svg', 'rect', 'path'] // 确保代码标签和SVG元素保留
            });
          }
          
          // 移除加载动画（如果存在）
          if (loadingElement) {
            removeLoadingElement(loadingElement);
          }
          
          // 更新内容
          responseParagraph.innerHTML = htmlContent || "无响应内容";
          previousContent = content;
          
          // 如果内容正在生成中（非结束状态），添加加载动画到内容末尾
          if (!isEnd) {
            const newLoadingElement = createLoadingElement();
            responseParagraph.appendChild(newLoadingElement);
          }
          
          // 处理渲染后的HTML内容，替换为组件
          await agentResponseService.processRenderedHtml(htmlContent, responseParagraph, isEnd);
          
        } catch (error) {
          console.error('处理Markdown内容时出错:', error);
          // 回退到纯文本处理
          responseParagraph.textContent = content || "无响应内容";
        }
        
        // 当响应完成时
        if (isEnd) {
          finishResponse(responseParagraph, convId, content);
        }
      } catch (error) {
        console.error('处理流式响应时出错:', error);
      } finally {
        // 响应完成时结束处理状态
        if (isComplete) {
          isProcessing.value = false;
          
          // 确保最后移除所有加载动画
          const responseParagraph = document.getElementById(responseId);
          if (responseParagraph) {
            const loadingElements = responseParagraph.querySelectorAll('.loading-animation-container');
            loadingElements.forEach(el => removeLoadingElement(el));
          }
        }
      }
    };
    
    // 调用chatWithAgent发送请求
    await chatService.chatWithAgent(chatRequest, streamCallback);
    
    // 安全超时处理
    const safetyTimeout = setTimeout(() => {
      if (isProcessing.value) {
        console.warn('检测到流式响应处理超时，强制结束处理状态');
        const responseParagraph = document.getElementById(responseId);
        if (responseParagraph) {
          const loadingElements = responseParagraph.querySelectorAll('.loading-animation-container');
          loadingElements.forEach(el => removeLoadingElement(el));
          responseParagraph.textContent = "响应超时，请重试";
        }
        isProcessing.value = false;
      }
    }, 30000); // 30秒超时

    return safetyTimeout;
  } catch (error) {
    console.error('触发聊天请求时出错:', error);
    isProcessing.value = false;
  }
};

// 添加完成响应的辅助函数
const finishResponse = (responseParagraph, convId, content) => {
  try {
    // 只有在有效的会话ID时才更新
    if (convId && convId !== 0) {
      conversationId.value = convId.toString();
      console.log(`响应完成，保存会话ID: ${conversationId.value}, 最终内容长度: ${content.length}`);
      
      // 确保EditorContent组件的模型值得到更新
      const editorContent = responseParagraph.closest('.editor-content');
      if (editorContent) {
        try {
          editorContent.dispatchEvent(new Event('input', { bubbles: true }));
          
          // 安全地更新选择位置
          safelyManageSelection((selection) => {
            const range = document.createRange();
            if (responseParagraph && responseParagraph.parentNode) {
              range.setStartAfter(responseParagraph);
              range.collapse(true);
              selection.removeAllRanges();
              selection.addRange(range);
            }
          });
          
          // 延迟处理代码块和图表
          setTimeout(() => {
            try {
              agentResponseService.ensureCodeBlocksHaveLanguage();
              agentResponseService.setupCodeBlocks();
              
              if (mermaidObserver && typeof mermaidObserver.renderPending === 'function') {
                mermaidObserver.renderPending();
              } else {
                agentResponseService.renderMermaidDiagrams();
              }
            } catch (error) {
              console.error('处理代码块或图表时出错:', error);
            }
          }, 500);
        } catch (error) {
          console.error('完成响应时出错:', error);
        }
      }
    }
  } catch (error) {
    console.error('完成响应处理时出错:', error);
  }
};

// 暴露给父组件的方法
defineExpose({
  findLastMention: agentResponseService.findLastMention,
  extractUserInput: agentResponseService.extractUserInput,
  handleChat,
  isProcessing,
  setConversationId,
  setCurrentNoteId,
  getCurrentNoteId,
  ensureCodeBlocksHaveLanguage: agentResponseService.ensureCodeBlocksHaveLanguage,
  renderMermaidDiagrams: agentResponseService.renderMermaidDiagrams,
  setupCodeCopyButtons: agentResponseService.setupCodeCopyButtons,
  setupCodeBlocks: agentResponseService.setupCodeBlocks,
  processRenderedHtml: agentResponseService.processRenderedHtml,
  forceRenderDiagrams: agentResponseService.forceRenderDiagrams,
  handleInputChat  // 暴露新的方法
});
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
  min-height: 400px;
  position: relative;
}

:deep(.markmap-svg) {
  width: 100%;
  min-height: 400px;
  outline: none;
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