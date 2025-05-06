<template>
  <div class="agent-response-handler">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import chatService from '@/services/chat';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import * as agentResponseService from '@/services/agentResponseService';
import { setupMermaidAutoRender } from '@/services/renderService';

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

// 用于存储会话ID
const conversationId = ref('');
const isProcessing = ref(false);

// 用于处理与AI助手的聊天
const handleChat = async (agentId: string, userInput: string, editorRef: HTMLElement) => {
  if (isProcessing.value || !userInput.trim() || !agentId) return;
  
  // 处理用户输入，自动检测代码块语言
  const processedInput = agentResponseService.processUserInput(userInput);
  
  // 用于保存响应段落的ID
  let responseId = '';
  
  try {
    isProcessing.value = true;
    console.log(`发送消息到助手，agentId: ${agentId}, 会话ID: ${conversationId.value || '新会话'}, 内容长度: ${processedInput.length}`);
    
    // 保存当前光标位置
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      console.warn('无法获取当前选区');
      return;
    }
    
    // 创建响应段落
    const responseParagraph = document.createElement('div');
    responseParagraph.className = 'agent-response-paragraph markdown-content';
    // 添加唯一ID以便后续引用
    responseId = `agent-response-${Date.now()}`;
    responseParagraph.id = responseId;
    console.log(`创建响应段落，ID: ${responseId}`);
    
    // 获取当前光标所在的位置，并插入响应段落
    const range = selection.getRangeAt(0);
    range.insertNode(responseParagraph);
    
    // 初始文本提示
    responseParagraph.textContent = "加载中...";
    
    // 确保编辑器内容更新
    setTimeout(() => {
      const editorContent = responseParagraph.closest('.editor-content');
      if (editorContent) {
        editorContent.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }, 0);
    
    // 处理流式响应的回调函数
    let previousContent = '';
    const streamCallback = async (response, isComplete, convId) => {
      try {
        // 提取content, isEnd和convId
        const data = response.data?.data || {};
        const content = data.full_content || '';
        const isEnd = data.done || isComplete;
        
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
        
        // 如果文本仍然是"加载中..."，即使内容没变也需要更新（清除加载提示）
        const shouldForceUpdate = responseParagraph.textContent === "加载中...";
        
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
          
          // 更新内容并移除"加载中..."提示
          if (responseParagraph.textContent === "加载中...") {
            responseParagraph.textContent = "";
          }
          responseParagraph.innerHTML = htmlContent || "无响应内容";
          previousContent = content;
          
          // 处理渲染后的HTML内容，替换为组件
          await agentResponseService.processRenderedHtml(htmlContent, responseParagraph, isEnd);
          
        } catch (error) {
          console.error('处理Markdown内容时出错:', error);
          // 回退到纯文本处理
          responseParagraph.textContent = content || "无响应内容";
        }
        
        // 当响应完成时，保存会话ID，并确保内容保留
        if (isEnd) {
          // 只有在有效的会话ID时才更新
          if (convId && convId !== 0) {
            conversationId.value = convId.toString();
            console.log(`响应完成，保存会话ID: ${conversationId.value}, 最终内容长度: ${content.length}`);
            
            // 确保EditorContent组件的模型值得到更新，但不过度触发
            const editorContent = responseParagraph.closest('.editor-content');
            if (editorContent) {
              // 最终更新一次内容
              try {
                editorContent.dispatchEvent(new Event('input', { bubbles: true }));
                console.log('流式响应完成，编辑器内容已更新');
                
                // 将光标定位到响应段落的末尾
                const selection = window.getSelection();
                selection.removeAllRanges();
                const range = document.createRange();
                // 检查响应段落是否存在于DOM中
                if (responseParagraph && responseParagraph.parentNode) {
                  // 设置光标在响应段落后面
                  range.setStartAfter(responseParagraph);
                  range.collapse(true);
                  selection.addRange(range);
                  console.log('已将光标定位到响应内容后面');
                }
                
                // 延迟处理代码块，等待DOM渲染完成
                setTimeout(() => {
                  // 处理代码块，但避免触发额外的更新
                  try {
                    // 先确保所有代码块都有语言标识
                    agentResponseService.ensureCodeBlocksHaveLanguage();
                    
                    // 然后使用CodeBlock组件替换代码块
                    agentResponseService.setupCodeBlocks();
                    
                    // 触发渲染流式输出期间累积的mermaid图表
                    if (mermaidObserver && typeof mermaidObserver.renderPending === 'function') {
                      console.log('流式输出完成，触发累积的mermaid图表渲染');
                      mermaidObserver.renderPending();
                    } else {
                      // 如果mermaidObserver不可用，则使用服务中的方法直接渲染
                      console.log('mermaidObserver不可用，直接调用renderMermaidDiagrams');
                      agentResponseService.renderMermaidDiagrams();
                    }
                    
                    // 添加额外的Mermaid图表渲染保障机制
                    setTimeout(() => {
                      // 使用服务中的强制渲染方法确保图表正确渲染
                      agentResponseService.forceRenderDiagrams();
                    }, 500);
                  } catch (error) {
                    console.error('最终处理代码块时出错:', error);
                  } finally {
                    isProcessing.value = false;
                  }
                }, 300);
              } catch (error) {
                console.error('最终更新编辑器内容时出错:', error);
                isProcessing.value = false;
              }
            } else {
              isProcessing.value = false;
            }
          } else {
            console.warn(`响应完成但没有有效会话ID: ${convId}`);
            isProcessing.value = false; // 即使没有会话ID也要结束处理状态
          }
          
          // 标记最后使用的@提及元素为已处理，防止重复触发
          const lastMention = agentResponseService.findLastActiveMention(editorRef);
          if (lastMention) {
            lastMention.setAttribute('data-processed', 'true');
            console.log('已标记@提及元素为已处理状态');
          }
        }
      } catch (error) {
        console.error('处理流式响应时出错:', error);
        if (isComplete) {
          isProcessing.value = false;
        }
      }
    };
    
    // 发送请求并处理流式响应
    console.log(`准备发送聊天请求，使用会话ID: ${conversationId.value || '未设置'}`);
    
    // 确保会话ID是数字
    let currentConvId = undefined;
    if (conversationId.value && conversationId.value !== '0' && conversationId.value !== '') {
      currentConvId = parseInt(conversationId.value);
      console.log(`使用现有会话ID: ${currentConvId}`);
    }
    
    await chatService.chatWithAgent({
      content: processedInput, // 使用处理后的输入
      agent_id: parseInt(agentId),
      conversation_id: currentConvId
    }, streamCallback);
    
    // 防止永久加载状态：设置一个安全超时，确保即使回调没有正确完成，也会清除加载状态
    const safetyTimeout = setTimeout(() => {
      // 如果5秒后仍然在处理中，则强制结束处理状态
      if (isProcessing.value) {
        console.warn('检测到流式响应处理超时，强制结束处理状态');
        
        // 清除"加载中..."文本
        const responseParagraph = document.getElementById(responseId);
        if (responseParagraph && responseParagraph.textContent === "加载中...") {
          responseParagraph.textContent = "响应超时，请重试";
        }
        
        isProcessing.value = false;
      }
    }, 5000);
    
  } catch (error) {
    console.error('调用AI助手时出错:', error);
    isProcessing.value = false;
  }
};

// 设置会话ID
const setConversationId = (id) => {
  console.log(`AgentResponseHandler.setConversationId被调用，值：${id || 'null'}`);
  if (id) {
    conversationId.value = id.toString();
    console.log(`AgentResponseHandler会话ID已设置: ${conversationId.value}`);
  } else {
    // 当id为null时，清空会话ID
    conversationId.value = null;
    console.log('AgentResponseHandler会话ID已清空');
  }
};

// 暴露给父组件的方法
defineExpose({
  findLastMention: agentResponseService.findLastMention,
  extractUserInput: agentResponseService.extractUserInput,
  handleChat,
  isProcessing,
  setConversationId,
  ensureCodeBlocksHaveLanguage: agentResponseService.ensureCodeBlocksHaveLanguage,
  renderMermaidDiagrams: agentResponseService.renderMermaidDiagrams,
  setupCodeCopyButtons: agentResponseService.setupCodeCopyButtons,
  setupCodeBlocks: agentResponseService.setupCodeBlocks,
  processRenderedHtml: agentResponseService.processRenderedHtml,
  forceRenderDiagrams: agentResponseService.forceRenderDiagrams
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
</style> 