import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import { createApp, h } from 'vue';
import mermaid from 'mermaid';
import { renderMermaidDynamically, setupMermaidAutoRender } from './renderService';
import { isMindMapContent, isMermaidContent } from './markdownService';

// 设置DOMPurify配置
const configureDOMPurify = () => {
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
      if (lang !== null) {
        node.setAttribute('data-language', lang);
      }
    }
  });
};

// 配置marked选项
const configureMarked = () => {
  // 使用any类型避免类型错误
  const markedOptions: any = {
    renderer: new marked.Renderer(),
    breaks: true,  // 将换行符转换为<br>
    gfm: true      // 启用GitHub风格的Markdown
  };
  
  // 扩展代码渲染器
  const renderer = markedOptions.renderer;
  
  // 重写代码渲染逻辑
  const originalCodeRenderer = renderer.code;
  renderer.code = function(code: string, lang?: string) {
    // 获取语言显示名称
    const displayLang = lang || 'text';
    
    // 特殊处理mermaid图表
    if (lang === 'mermaid') {
      // 创建mermaid类的pre元素，让浏览器直接渲染
      return `<pre><code class="language-mermaid">${code}</code></pre>`;
    }
    
    // 对于普通代码块，使用原始渲染器
    return originalCodeRenderer.call(this, code, lang);
  };

  // 更新marked配置使用自定义渲染器
  marked.setOptions(markedOptions);
};

// 初始化服务
export const initAgentResponseService = () => {
  configureDOMPurify();
  configureMarked();

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
};

// 处理用户输入，检测代码块并自动识别语言
export const processUserInput = (content: string): string => {
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

// 处理渲染后的HTML内容，将特殊容器替换为组件
export const processRenderedHtml = async (htmlContent: string, container: HTMLElement, isStreamEnd = false) => {
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
      
      // 异步导入CodeBlock组件以避免循环依赖
      const CodeBlockModule = await import('../components/CodeBlock.vue');
      const CodeBlock = CodeBlockModule.default;
      
      // 使用导入的createApp函数创建CodeBlock组件实例
      const codeBlockApp = createApp({
        render() {
          return h(CodeBlock, {
            code: code,
            language: language
          });
        }
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
        if (!preElement || preElement.hasAttribute('data-mermaid-processed')) continue;
        
        // 标记为已处理，防止重复处理
        preElement.setAttribute('data-mermaid-processed', 'true');
        
        // 创建一个新的mermaid渲染容器
        const mermaidContainer = document.createElement('div');
        mermaidContainer.className = 'mermaid-container';
        
        // 创建唯一ID的mermaid元素
        const mermaidEl = document.createElement('div');
        const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        mermaidEl.id = mermaidId;
        mermaidEl.className = 'mermaid'; // 不再添加flow-processed标记
        mermaidEl.textContent = code; // 直接设置mermaid内容
        mermaidEl.setAttribute('data-original-content', code); // 保存原始内容
        
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
        
        console.log(`创建新的mermaid元素: ${mermaidId}`);
      }
      // 如果是markdown代码块（可能是思维导图）
      else if (language === 'markdown' || language === 'md') {
        const code = codeBlock.textContent || '';
        const preElement = codeBlock.closest('pre');
        if (!preElement) continue;
        
        // 标记为已处理，但在流式输出结束前不直接创建组件
        preElement.setAttribute('data-markmap-processed', 'true');
        
        // 在流式输出过程中，只检查内容是否符合思维导图格式并记录
        if (isMindMapContent(code)) {
          console.log('检测到思维导图内容，标记等待流式输出结束后处理');
          // 流式输出过程中不直接创建组件，只添加标记
          preElement.setAttribute('data-markmap-content', encodeURIComponent(code));
        }
      }
    }
    
    // 仅在流式输出结束时才渲染mermaid图表和思维导图
    if (isStreamEnd) {
      // 在流式输出结束时，立即尝试渲染mermaid图表
      try {
        console.log('流式输出结束，渲染mermaid图表和思维导图');
        import('./renderService').then(({ renderMermaidDynamically, renderMarkMaps }) => {
          renderMermaidDynamically();
          renderMarkMaps();
        });
      } catch (error) {
        console.error('图表渲染失败:', error);
      }
    } else {
      console.log('流式输出中，标记图表等待最终渲染');
    }
    
    // 查找可能的思维导图内容 (基于内容格式判断)
    const paragraphs = container.querySelectorAll('p:not([data-markmap-processed])');
    for (const p of paragraphs) {
      // 标记为已处理，但在流式输出结束前不直接创建组件
      p.setAttribute('data-markmap-processed', 'true');
      
      const content = p.textContent || '';
      // 检查是否符合思维导图格式
      if (isMindMapContent(content)) {
        console.log('在段落中检测到思维导图内容，标记等待流式输出结束后处理');
        // 流式输出过程中不直接创建组件，只添加标记
        p.setAttribute('data-markmap-content', encodeURIComponent(content));
      }
    }
  } catch (error) {
    console.error('处理渲染HTML时出错:', error);
  }
};

// 确保代码块有正确的语言标识
export const ensureCodeBlocksHaveLanguage = () => {
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
        hljs.highlightElement(block as HTMLElement);
      } catch (error) {
        console.error('代码高亮处理失败:', error);
      }
    });
  } catch (error) {
    console.error('处理代码块语言失败:', error);
  }
};

// 渲染mermaid图表
export const renderMermaidDiagrams = () => {
  try {
    // 使用renderService中的renderMermaidDynamically函数
    renderMermaidDynamically();
  } catch (error) {
    console.error('渲染mermaid图表失败:', error);
  }
};

// 添加代码块复制功能
export const setupCodeCopyButtons = () => {
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
      if (preBlock.parentNode && 
          preBlock.parentNode instanceof HTMLElement && 
          preBlock.parentNode.classList.contains('code-block-wrapper')) {
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
      copyButton.addEventListener('click', function(this: HTMLElement) {
        // 找到代码块内容
        const codeBlock = this.parentNode?.querySelector('code');
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

// 设置代码块为CodeBlock组件
export const setupCodeBlocks = async () => {
  try {
    // 查找所有尚未处理的代码块
    const codeBlocks = document.querySelectorAll('pre > code:not(.processed-code-block)');
    if (codeBlocks.length === 0) return;
    
    console.log(`找到${codeBlocks.length}个未处理的代码块，将替换为CodeBlock组件`);
    
    // 导入CodeBlock组件
    const CodeBlockModule = await import('../components/CodeBlock.vue');
    const CodeBlock = CodeBlockModule.default;
    
    for (const codeElement of codeBlocks) {
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
    }
  } catch (error) {
    console.error('设置代码块组件时出错:', error);
  }
};

// 手动触发图表渲染
export const forceRenderDiagrams = () => {
  console.log('手动触发图表渲染');
  
  // 重置任何带有flow-processed或mermaid-processed类的元素
  const markedMermaidElements = document.querySelectorAll('.mermaid.flow-processed, .mermaid.mermaid-processed');
  if (markedMermaidElements.length > 0) {
    console.log(`重置${markedMermaidElements.length}个带有特殊标记的Mermaid元素`);
    markedMermaidElements.forEach(el => {
      if (!(el as HTMLElement).hasAttribute('data-processed')) {
        (el as HTMLElement).classList.remove('flow-processed');
        (el as HTMLElement).classList.remove('mermaid-processed');
      }
    });
  }
  
  // 直接调用渲染方法
  console.log('调用渲染方法');
  import('./renderService').then(({ renderMermaidDynamically, renderMarkMaps }) => {
    renderMermaidDynamically();
    renderMarkMaps();
  });
  
  // 为确保渲染完成，延迟一段时间后再次尝试渲染
  setTimeout(() => {
    // 查找所有未处理的Mermaid元素
    const unprocessedMermaidElements = document.querySelectorAll('.mermaid:not([data-processed])') as NodeListOf<HTMLElement>;
    if (unprocessedMermaidElements.length > 0) {
      console.log(`发现${unprocessedMermaidElements.length}个未处理的Mermaid元素，再次尝试渲染`);
      
      // 尝试直接使用mermaid API渲染
      try {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'loose',
          flowchart: {
            htmlLabels: true,
            curve: 'basis',
            useMaxWidth: false
          }
        });
        
        if (typeof mermaid.run === 'function') {
          mermaid.run({
            querySelector: '.mermaid:not([data-processed])'
          }).catch(err => {
            console.error('mermaid.run渲染失败，尝试其他方法', err);
            // 尝试传统方法
            try {
              mermaid.init(undefined, unprocessedMermaidElements);
            } catch (initErr) {
              console.error('mermaid.init也失败', initErr);
            }
          });
        } else {
          // 降级到传统方法
          mermaid.init(undefined, unprocessedMermaidElements);
        }
      } catch (error) {
        console.error('所有渲染方法都失败', error);
      }
    } else {
      console.log('没有找到需要渲染的Mermaid图表');
    }
    
    // 再次尝试渲染思维导图
    import('./renderService').then(({ renderMarkMaps }) => {
      renderMarkMaps();
    });
  }, 300);
};

// 从编辑器中提取用户输入
export const extractUserInput = (editorRef: HTMLElement, lastMention: HTMLElement | null) => {
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
export const findLastMention = (editorRef: HTMLElement) => {
  const mentions = editorRef.querySelectorAll('.user-mention:not([data-processed="true"])');
  return mentions.length ? mentions[mentions.length - 1] as HTMLElement : null;
};

// 查找最后一个活跃的@提及元素（包括已处理的，用于标记为已处理）
export const findLastActiveMention = (editorRef: HTMLElement) => {
  const mentions = editorRef.querySelectorAll('.user-mention');
  return mentions.length ? mentions[mentions.length - 1] as HTMLElement : null;
};

// 渲染所有Mermaid图表
export const renderAllMermaidDiagrams = async () => {
  try {
    console.log('尝试渲染所有Mermaid图表...');
    
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
    
    // 使用renderService中的renderMermaidDynamically函数进行渲染
    renderMermaidDynamically();
    
    console.log('所有Mermaid图表渲染完成');
  } catch (error) {
    console.error('渲染全部Mermaid图表失败:', error);
  }
}; 