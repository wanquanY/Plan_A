<template>
  <div class="agent-response-handler">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h, render, createApp, onMounted, onUnmounted, computed } from 'vue';
import chatService from '@/services/chat';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import mermaid from 'mermaid';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import CodeBlock from './CodeBlock.vue';
import MermaidDiagram from './MermaidDiagram.vue';
import MarkMap from './MarkMap.vue';

// 全局注册一个MutationObserver来检测新添加的Mermaid图表并自动渲染
let mermaidObserver = null;
onMounted(() => {
  // 初始化mermaid配置
  mermaid.initialize({
    startOnLoad: false, // 不自动渲染，我们将在需要的地方手动渲染
    theme: 'default',
    securityLevel: 'loose', // 允许点击事件
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
    fontSize: 14,
    flowchart: {
      htmlLabels: true,
      curve: 'basis'
    }
  });
  
  // 创建MutationObserver来监听DOM变化并渲染新增的mermaid图表
  mermaidObserver = new MutationObserver(mutations => {
    let shouldRenderMermaid = false;
    
    mutations.forEach(mutation => {
      if (mutation.type === 'childList' && mutation.addedNodes.length) {
        // 检查是否添加了包含.mermaid或code.language-mermaid的元素
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.classList?.contains('mermaid') || 
                node.querySelector?.('.mermaid, code.language-mermaid')) {
              shouldRenderMermaid = true;
            }
          }
        });
      }
    });
    
    // 如果检测到新的mermaid图表，执行渲染
    if (shouldRenderMermaid) {
      setTimeout(async () => {
        try {
          await mermaid.run();
        } catch (error) {
          console.error('MutationObserver触发的Mermaid渲染失败:', error);
        }
      }, 100); // 短暂延迟确保DOM已完全更新
    }
  });
  
  // 开始监听整个body的变化
  mermaidObserver.observe(document.body, {
    childList: true, 
    subtree: true
  });
  
  // 在组件挂载后，尝试初始渲染所有图表
  setTimeout(() => {
    renderAllMermaidDiagrams();
  }, 500);
});

// 组件卸载时清理observer
onUnmounted(() => {
  if (mermaidObserver) {
    mermaidObserver.disconnect();
    mermaidObserver = null;
  }
});

// 配置marked选项
marked.setOptions({
  breaks: true,       // 将换行符转换为<br>
  gfm: true,          // 启用GitHub风格的Markdown
  headerIds: false,   // 避免自动生成header IDs
  highlight: function(code, lang) {
    // 这里不再自己处理高亮，改为在渲染时使用CodeBlock组件
    return code;
  }
});

// 配置DOMPurify，允许代码块的语言类和样式
DOMPurify.addHook('afterSanitizeAttributes', function(node) {
  // 为代码块添加类属性
  if (node.nodeName === 'CODE' && node.parentNode && node.parentNode.nodeName === 'PRE') {
    // 保留language-*类，用于语法高亮
    node.className = node.className.replace(/language-\w+/, match => match);
  }
  
  // 保留pre标签的data-language属性
  if (node.nodeName === 'PRE' && node.hasAttribute('data-language')) {
    // 确保data-language属性被保留
    const lang = node.getAttribute('data-language');
    node.setAttribute('data-language', lang);
  }
});

// 自定义渲染器添加复制按钮
const renderer = new marked.Renderer();
const originalCodeRenderer = renderer.code;
renderer.code = function(code, language, isEscaped) {
  // 获取语言显示名称
  const displayLang = language || 'text';
  
  // 特殊处理mermaid图表
  if (language === 'mermaid') {
    // 创建mermaid类的pre元素，让浏览器直接渲染
    return `<pre><code class="language-mermaid">${code}</code></pre>`;
  }
  
  // 对于普通代码块，返回原始HTML
  return originalCodeRenderer.call(this, code, language, isEscaped);
};

// 更新marked配置使用自定义渲染器
marked.setOptions({
  renderer: renderer
});

// 用于生成思维导图的正则表达式
const mindMapRegex = /^# .+(\n[#]+ .+)+$/m;

// 检查内容是否可能是思维导图
const isMindMapContent = (content) => {
  // 检查是否符合思维导图格式：以#开头的多行内容，至少有一个二级标题
  return mindMapRegex.test(content) || 
         // 至少包含一个一级标题和多个层级标题
         (content.match(/^#\s+.+/m) && content.match(/^#{2,}\s+.+/m));
};

// 处理渲染后的HTML内容，将特殊容器替换为组件
const processRenderedHtml = async (htmlContent, container) => {
  try {
    // 处理普通代码块
    const codeContainers = container.querySelectorAll('.code-container');
    for (const codeContainer of codeContainers) {
      const code = decodeURIComponent(codeContainer.getAttribute('data-code') || '');
      const language = codeContainer.getAttribute('data-language') || 'text';
      
      // 创建CodeBlock组件
      const codeBlockEl = document.createElement('div');
      codeBlockEl.className = 'code-block-component';
      codeContainer.replaceWith(codeBlockEl);
      
      // 使用导入的createApp函数创建CodeBlock组件实例
      const codeBlockApp = createApp(CodeBlock, {
        code: code,
        language: language
      });
      codeBlockApp.mount(codeBlockEl);
    }
    
    // 获取页面上的所有代码块元素
    const allCodeBlocks = container.querySelectorAll('pre code');
    for (const codeBlock of allCodeBlocks) {
      // 提取语言
      const classNames = Array.from(codeBlock.classList || []);
      const langClass = classNames.find(cls => cls.startsWith('language-'));
      const language = langClass ? langClass.replace('language-', '') : 'text';
      
      // 如果是mermaid代码块
      if (language === 'mermaid') {
        const code = codeBlock.textContent || '';
        const preElement = codeBlock.closest('pre');
        if (!preElement) continue;
        
        // 创建一个新的mermaid渲染容器
        const mermaidContainer = document.createElement('div');
        mermaidContainer.className = 'mermaid-container';
        
        // 创建唯一ID的mermaid元素
        const mermaidEl = document.createElement('div');
        const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        mermaidEl.id = mermaidId;
        mermaidEl.className = 'mermaid';
        mermaidEl.textContent = code; // 直接设置mermaid内容
        
        // 添加复制按钮
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = '复制';
        copyButton.onclick = () => {
          navigator.clipboard.writeText(code);
          copyButton.textContent = '已复制';
          setTimeout(() => {
            copyButton.textContent = '复制';
          }, 2000);
        };
        
        // 组装DOM
        mermaidContainer.appendChild(mermaidEl);
        mermaidContainer.appendChild(copyButton);
        
        // 替换原始pre元素
        preElement.replaceWith(mermaidContainer);
      }
      // 如果是markdown代码块（可能是思维导图）
      else if (language === 'markdown' || language === 'md') {
        const code = codeBlock.textContent || '';
        const preElement = codeBlock.closest('pre');
        if (!preElement) continue;
        
        // 检查内容是否符合思维导图格式
        if (isMindMapContent(code)) {
          console.log('检测到思维导图内容，创建MarkMap组件');
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper';
          
          // 替换原始pre元素
          preElement.replaceWith(markMapContainer);
          
          // 使用Vue创建MarkMap组件
          const markMapApp = createApp({
            render() {
              return h(MarkMap, {
                content: code,
                height: '400px'
              });
            }
          });
          
          // 挂载组件到DOM
          markMapApp.mount(markMapContainer);
        }
      }
    }
    
    // 最后，重新初始化和渲染所有mermaid图表
    try {
      // 重新初始化mermaid配置
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
        fontSize: 14,
        flowchart: {
          htmlLabels: true,
          curve: 'basis'
        }
      });
      
      // 手动运行mermaid渲染全部图表
      await mermaid.run({
        querySelector: '.mermaid',
      });
    } catch (mermaidError) {
      console.error('Mermaid渲染失败:', mermaidError);
    }
    
    // 查找可能的思维导图内容 (基于内容格式判断)
    const paragraphs = container.querySelectorAll('p');
    for (const p of paragraphs) {
      const content = p.textContent || '';
      // 检查是否符合思维导图格式 (以#开头的多行内容)
      if (isMindMapContent(content)) {
        console.log('在段落中检测到思维导图内容，创建MarkMap组件');
        // 创建MarkMap组件
        const markMapEl = document.createElement('div');
        markMapEl.className = 'mark-map-component';
        p.replaceWith(markMapEl);
        
        // 使用导入的createApp函数创建MarkMap组件实例
        const markMapApp = createApp(MarkMap, {
          content: content,
          height: '400px'
        });
        markMapApp.mount(markMapEl);
      }
    }
  } catch (error) {
    console.error('处理渲染HTML时出错:', error);
  }
};

const conversationId = ref('');
const isProcessing = ref(false);

// 处理用户输入，检测代码块并自动识别语言
const processUserInput = (content) => {
  if (!content) return '';
  
  // 检查是否有@Web指令
  const hasWebDirective = content.includes('@Web');
  if (hasWebDirective) {
    // 处理@Web指令后的代码块，强制识别为HTML
    content = content.replace(/@Web\s+```(?:\w*\n)?([\s\S]+?)```/g, (match, code) => {
      return `@Web \`\`\`html\n${code}\`\`\``;
    });
  }
  
  // 检查是否包含代码块
  const hasCodeBlock = content.includes('```');
  
  // 替换没有语言指定的代码块，使用自动检测
  let processedContent = content;
  if (hasCodeBlock) {
    // 正则表达式匹配代码块，捕获语言指定部分(如果存在)和代码块内容
    processedContent = content.replace(/```(?:([\w#+.]+)?\n)?([\s\S]+?)```/g, (match, lang, code) => {
      // 检查代码块是否是思维导图内容
      if (isMindMapContent(code) && (!lang || lang === 'markdown' || lang === 'md')) {
        return '```markdown\n' + code + '\n```';
      }
      
      // 如果没有指定语言，使用highlight.js自动检测
      if (!lang) {
        try {
          // 检查是否是mermaid图表，特殊处理
          if (code.trim().startsWith('graph ') || 
              code.trim().startsWith('sequenceDiagram') || 
              code.trim().startsWith('classDiagram') || 
              code.trim().startsWith('flowchart') ||
              code.trim().match(/^flowchart\s+TD/) ||
              code.trim().match(/^flowchart\s+LR/) ||
              code.trim().startsWith('gantt') ||
              code.trim().startsWith('pie') ||
              code.trim().startsWith('erDiagram')) {
            return '```mermaid\n' + code + '\n```';
          }
          
          // 使用highlight.js自动检测语言
          const result = hljs.highlightAuto(code);
          lang = result.language || 'text';
          
          console.log(`自动检测代码块语言: ${lang}`);
        } catch (error) {
          console.error('自动检测语言失败:', error);
          lang = 'text';
        }
      } else if (lang && lang.toLowerCase() === 'flow') {
        // 自动将flow语言转换为mermaid flowchart
        return '```mermaid\nflowchart TD\n' + code + '\n```';
      }
      
      // 返回带有语言标记的代码块
      return `\`\`\`${lang || 'text'}\n${code}\`\`\``;
    });
  }
  
  return processedContent;
};

// 事件声明
const emit = defineEmits(['agent-response']);

// 用于处理与AI助手的聊天
const handleChat = async (agentId: string, userInput: string, editorRef: HTMLElement) => {
  if (isProcessing.value || !userInput.trim() || !agentId) return;
  
  // 处理用户输入，自动检测代码块语言
  const processedInput = processUserInput(userInput);
  
  // 用于保存响应段落的ID
  let responseId = '';
  let initialUpdate = true; // 标记是否是首次更新
  
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
    const responseParagraph = document.createElement('div'); // 使用div替代p以支持复杂的Markdown渲染
    responseParagraph.className = 'agent-response-paragraph markdown-content';
    // 添加唯一ID以便后续引用
    responseId = `agent-response-${Date.now()}`;
    responseParagraph.id = responseId;
    console.log(`创建响应段落，ID: ${responseId}`);
    
    // 获取当前光标所在的位置，并插入响应段落
    const range = selection.getRangeAt(0);
    range.insertNode(responseParagraph);
    
    // 将光标移动到响应段落后面
    selection.removeAllRanges();
    const newRange = document.createRange();
    newRange.setStartAfter(responseParagraph);
    newRange.collapse(true);
    selection.addRange(newRange);
    
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
        const processedContent = processUserInput(content || "");
        
        // 将Markdown转换为HTML并进行安全处理
        let htmlContent = marked(processedContent || "");
        
        // DOMPurify消毒处理防止XSS攻击
        if (typeof DOMPurify !== 'undefined') {
          htmlContent = DOMPurify.sanitize(htmlContent, {
            ADD_ATTR: ['class', 'data-language', 'id', 'data-code', 'data-mermaid-code'], // 允许自定义属性
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
        await processRenderedHtml(htmlContent, responseParagraph);
        
      } catch (error) {
        console.error('处理Markdown内容时出错:', error);
        // 回退到纯文本处理
        responseParagraph.textContent = content || "无响应内容";
      }
      
      // 当响应完成时，保存会话ID，并确保内容保留
      if (isEnd) {
        // 只有在有效的会话ID时才更新
        if (convId && convId !== 0) {
          const oldId = conversationId.value;
          conversationId.value = convId.toString();
          console.log(`响应完成，保存会话ID: ${conversationId.value}, 最终内容长度: ${content.length}`);
          
          // 确保EditorContent组件的模型值得到更新，但不过度触发
          const editorContent = responseParagraph.closest('.editor-content');
          if (editorContent) {
            // 最终更新一次内容
            try {
              editorContent.dispatchEvent(new Event('input', { bubbles: true }));
              console.log('流式响应完成，编辑器内容已更新');
              
              // 延迟处理代码块，等待DOM渲染完成
              setTimeout(() => {
                // 处理代码块，但避免触发额外的更新
                try {
                  // 先确保所有代码块都有语言标识
                  ensureCodeBlocksHaveLanguage();
                  
                  // 然后使用CodeBlock组件替换代码块
                  setupCodeBlocks();
                  
                  // 再渲染Mermaid图表
                  renderMermaidDiagrams();
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
        const lastMention = findLastActiveMention(editorRef);
        if (lastMention) {
          lastMention.setAttribute('data-processed', 'true');
          console.log('已标记@提及元素为已处理状态');
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
    
    // 不再在这里调用handleAgentResponseComplete，因为它已经在流式响应完成回调中处理了
    
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

// 从编辑器中提取用户输入
const extractUserInput = (editorRef: HTMLElement, lastMention: HTMLElement | null) => {
  if (!lastMention) return null;
  
  // 获取包含@提及的段落元素
  let paragraph = lastMention;
  while (paragraph && paragraph.nodeName !== 'P' && paragraph.nodeName !== 'DIV') {
    paragraph = paragraph.parentNode as HTMLElement;
  }
  
  if (!paragraph) {
    console.warn('无法找到包含@提及的段落元素');
    return null;
  }
  
  // 收集从@提及到段落结束的内容
  let textContent = '';
  let foundMention = false;
  
  // 遍历段落的所有子节点
  for (let i = 0; i < paragraph.childNodes.length; i++) {
    const node = paragraph.childNodes[i];
    
    // 如果找到了@提及元素，开始收集之后的内容
    if (node === lastMention) {
      foundMention = true;
      continue; // 跳过@提及元素本身
    }
    
    // 收集@提及之后的内容
    if (foundMention) {
      if (node.nodeType === Node.TEXT_NODE) {
        textContent += node.textContent;
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        textContent += (node as HTMLElement).innerText;
      }
    }
  }
  
  // 如果找不到文本内容，尝试备用方法
  if (!textContent.trim() && paragraph) {
    const fullParagraphText = paragraph.innerText;
    const mentionText = lastMention.innerText || lastMention.textContent;
    
    if (mentionText) {
      const mentionIndex = fullParagraphText.indexOf(mentionText);
      if (mentionIndex !== -1) {
        textContent = fullParagraphText.substring(mentionIndex + mentionText.length);
      }
    }
  }
  
  console.log(`提取的用户输入: "${textContent.trim()}"`);
  return textContent;
};

// 查找最后一个@提及元素
const findLastMention = (editorRef: HTMLElement) => {
  const mentions = editorRef.querySelectorAll('.user-mention:not([data-processed="true"])');
  return mentions.length ? mentions[mentions.length - 1] as HTMLElement : null;
};

// 查找最后一个活跃的@提及元素（包括已处理的，用于标记为已处理）
const findLastActiveMention = (editorRef: HTMLElement) => {
  const mentions = editorRef.querySelectorAll('.user-mention');
  return mentions.length ? mentions[mentions.length - 1] as HTMLElement : null;
};

// 公共方法：重新渲染所有Mermaid图表
const renderAllMermaidDiagrams = async () => {
  try {
    console.log('尝试渲染所有Mermaid图表...');
    
    // 重新初始化mermaid配置
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
      fontSize: 14,
      flowchart: {
        htmlLabels: true,
        curve: 'basis'
      }
    });
    
    // 查找所有预渲染的代码块，转换为mermaid容器
    const preElements = document.querySelectorAll('pre > code.language-mermaid');
    for (const codeBlock of preElements) {
      const code = codeBlock.textContent || '';
      const preElement = codeBlock.closest('pre');
      if (!preElement) continue;
      
      // 创建mermaid容器
      const mermaidContainer = document.createElement('div');
      mermaidContainer.className = 'mermaid-container';
      
      // 创建mermaid元素
      const mermaidEl = document.createElement('div');
      const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      mermaidEl.id = mermaidId;
      mermaidEl.className = 'mermaid';
      mermaidEl.textContent = code;
      
      // 添加复制按钮
      const copyButton = document.createElement('button');
      copyButton.className = 'copy-button';
      copyButton.textContent = '复制';
      copyButton.onclick = () => {
        navigator.clipboard.writeText(code);
        copyButton.textContent = '已复制';
        setTimeout(() => {
          copyButton.textContent = '复制';
        }, 2000);
      };
      
      // 组装DOM
      mermaidContainer.appendChild(mermaidEl);
      mermaidContainer.appendChild(copyButton);
      
      // 替换原始pre元素
      preElement.replaceWith(mermaidContainer);
    }
    
    // 渲染所有mermaid图表
    await mermaid.run({
      querySelector: '.mermaid',
    });
    
    console.log('所有Mermaid图表渲染完成');
  } catch (error) {
    console.error('渲染全部Mermaid图表失败:', error);
  }
};

// 确保代码块有正确的语言标识
const ensureCodeBlocksHaveLanguage = () => {
  try {
    const codeBlocks = document.querySelectorAll('pre > code');
    codeBlocks.forEach(block => {
      // 检查代码块是否已经有语言类
      if (!block.className.includes('language-')) {
        // 使用highlight.js的自动检测语言功能
        try {
          const code = block.textContent || '';
          const result = hljs.highlightAuto(code);
          const lang = result.language || 'text';
          
          console.log(`代码块语言自动检测结果: ${lang}`);
          
          // 添加语言类
          block.className = `language-${lang}`;
          
          // 为父pre标签添加data-language属性
          const preTag = block.parentElement;
          if (preTag) {
            preTag.setAttribute('data-language', lang);
          }
        } catch (error) {
          console.error('自动检测语言失败:', error);
          // 失败时设置为text
          block.className = 'language-text';
        }
      }
      
      // 应用语法高亮
      try {
        hljs.highlightElement(block);
      } catch (error) {
        console.error('代码高亮处理失败:', error);
      }
    });
  } catch (error) {
    console.error('处理代码块语言失败:', error);
  }
};

// 渲染mermaid图表
const renderMermaidDiagrams = () => {
  try {
    // 使用已导入的mermaid，而不是动态导入
    const mermaidDivs = document.querySelectorAll('.mermaid');
    if (mermaidDivs.length > 0) {
      console.log(`找到${mermaidDivs.length}个mermaid图表，开始渲染`);
      
      // 重新初始化mermaid配置
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
        fontSize: 14,
        flowchart: {
          htmlLabels: true,
          curve: 'basis'
        }
      });
      
      // 渲染图表
      setTimeout(async () => {
        try {
          await mermaid.run({
            querySelector: '.mermaid'
          });
        } catch (err) {
          console.error('Mermaid渲染失败:', err);
        }
      }, 0);
    }
  } catch (error) {
    console.error('渲染mermaid图表失败:', error);
  }
};

// 添加代码块复制功能
const setupCodeCopyButtons = () => {
  try {
    // 首先查找没有复制按钮的代码块
    const preBlocks = document.querySelectorAll('pre:not(.has-copy-button)');
    if (preBlocks.length === 0) {
      // 没有需要处理的代码块，直接返回
      return;
    }
    
    console.log(`找到${preBlocks.length}个未处理的代码块，添加复制按钮`);
    
    preBlocks.forEach(preBlock => {
      // 标记为已处理，防止重复处理
      preBlock.classList.add('has-copy-button');
      
      // 如果已经在code-block-wrapper中，跳过
      if (preBlock.parentNode && preBlock.parentNode.classList.contains('code-block-wrapper')) {
        return;
      }
      
      // 创建代码块容器
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      
      // 获取语言名称
      const lang = preBlock.getAttribute('data-language') || 'text';
      
      // 创建复制按钮
      const copyButton = document.createElement('div');
      copyButton.className = 'code-copy-button';
      copyButton.title = '复制代码';
      copyButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      `;
      
      // 添加事件监听器，直接绑定到按钮上
      copyButton.addEventListener('click', function() {
        // 找到代码块内容
        const codeBlock = this.parentNode.querySelector('code');
        if (codeBlock) {
          // 获取代码内容并复制到剪贴板
          const codeText = codeBlock.textContent || '';
          navigator.clipboard.writeText(codeText).then(() => {
            // 显示复制成功状态
            this.classList.add('copied');
            this.setAttribute('title', '已复制!');
            
            // 2秒后恢复原始状态
            setTimeout(() => {
              this.classList.remove('copied');
              this.setAttribute('title', '复制代码');
            }, 2000);
          }).catch(err => {
            console.error('复制失败:', err);
          });
        }
      });
      
      // 如果父元素存在，则插入到DOM中
      if (preBlock.parentNode) {
        // 保存原始位置
        const parentNode = preBlock.parentNode;
        const nextSibling = preBlock.nextSibling;
        
        // 构建新的结构
        wrapper.appendChild(preBlock);
        wrapper.appendChild(copyButton);
        
        // 插入到原始位置
        if (nextSibling) {
          parentNode.insertBefore(wrapper, nextSibling);
        } else {
          parentNode.appendChild(wrapper);
        }
      }
    });
  } catch (error) {
    console.error('设置代码块复制按钮时出错:', error);
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

// 设置代码块为CodeBlock组件
const setupCodeBlocks = () => {
  try {
    // 查找所有尚未处理的代码块
    const codeBlocks = document.querySelectorAll('pre > code:not(.processed-code-block)');
    if (codeBlocks.length === 0) return;
    
    console.log(`找到${codeBlocks.length}个未处理的代码块，将替换为CodeBlock组件`);
    
    codeBlocks.forEach(codeElement => {
      // 标记为已处理，避免重复处理
      codeElement.classList.add('processed-code-block');
      
      // 获取代码内容和语言
      const code = codeElement.textContent || '';
      let language = 'text';
      
      // 从class中提取语言
      const classList = codeElement.className.split(' ');
      for (const cls of classList) {
        if (cls.startsWith('language-')) {
          language = cls.replace('language-', '');
          break;
        }
      }
      
      // 找到pre标签
      const preElement = codeElement.parentElement;
      if (!preElement) return;
      
      // 创建包装div替代pre标签
      const wrapperDiv = document.createElement('div');
      wrapperDiv.className = 'code-block-component-wrapper';
      
      // 在pre标签之后插入包装div
      if (preElement.parentNode) {
        preElement.parentNode.insertBefore(wrapperDiv, preElement.nextSibling);
        
        // 使用Vue创建CodeBlock组件
        const codeBlockApp = createApp({
          render() {
            return h(CodeBlock, {
              code: code,
              language: language
            });
          }
        });
        
        // 挂载组件到DOM
        codeBlockApp.mount(wrapperDiv);
        
        // 隐藏原始pre标签（不立即删除，以免破坏布局）
        preElement.style.display = 'none';
        preElement.classList.add('replaced-by-component');
      }
    });
  } catch (error) {
    console.error('设置代码块组件时出错:', error);
  }
};

// 处理chat流式响应
const handleChatMessages = async (response) => {
  try {
    const data = response.data || {};
    
    // 检查响应结构
    if (!data || !data.data) {
      console.warn('收到无效的响应数据结构:', data);
      return;
    }
    
    // 提取消息内容和agent信息
    const message = data.data.message || {};
    const agentInfo = data.data.agent_info || null;
    
    // 发送agent信息
    if (agentInfo) {
      emit('agent-response', { 
        agent_info: agentInfo,
        message: message 
      });
    }
    
    // ... 原有的处理逻辑
  } catch (error) {
    console.error('处理流式响应时出错:', error);
  }
};

// 暴露给父组件的方法
defineExpose({
  findLastMention,
  extractUserInput,
  handleChat,
  isProcessing,
  setConversationId,
  ensureCodeBlocksHaveLanguage,
  renderMermaidDiagrams,
  setupCodeCopyButtons,
  setupCodeBlocks,
  processRenderedHtml,
  isMindMapContent
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

:deep(.markmap-toolbar) {
  position: absolute;
  top: 5px;
  right: 5px;
  display: flex;
  gap: 5px;
  z-index: 10;
}

:deep(.fit-button),
:deep(.markmap-copy-button) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background-color: rgba(246, 248, 250, 0.8);
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease, background-color 0.2s ease;
  border: 1px solid #eaecef;
  color: #666;
}

:deep(.markmap-component-wrapper:hover .fit-button),
:deep(.markmap-component-wrapper:hover .markmap-copy-button) {
  opacity: 1;
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
    text-align: center;
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
}

/* 设置全局的Markmap SVG样式 */
:global(svg[id^="markmap-"]) {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100%;
}
</style> 