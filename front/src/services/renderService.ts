import { createApp, h } from 'vue';
import type { Component } from 'vue';
import mermaid from 'mermaid';
import { isMindMapContent } from './markdownService';

/**
 * 渲染mermaid图表
 */
export const renderMermaidDiagrams = () => {
  try {
    const mermaidDivs = document.querySelectorAll('.mermaid') as NodeListOf<HTMLElement>;
    if (mermaidDivs.length > 0) {
      console.log(`找到${mermaidDivs.length}个mermaid图表，开始渲染`);
      mermaid.init(undefined, mermaidDivs);
    }
  } catch (error) {
    console.error('渲染mermaid图表失败:', error);
  }
};

/**
 * 处理并渲染代码块
 * @param handleMarkMaps 是否处理markdown思维导图
 */
export const renderCodeBlocks = async (handleMarkMaps = true) => {
  try {
    // 导入需要的组件
    const CodeBlockModule = await import('../components/rendering/CodeBlock.vue');
    const CodeBlock = CodeBlockModule.default;
    
    // 如果需要处理思维导图，导入MarkMap组件
    let MarkMap: Component | null = null;
    if (handleMarkMaps) {
      const MarkMapModule = await import('../components/rendering/MarkMap.vue');
      MarkMap = MarkMapModule.default;
    }
    
    // 处理代码块的函数
    const processCodeBlock = (block: Element, preElement: Element, code: string, language: string) => {
      console.log(`处理代码块，语言: ${language}`);
      
      // 检查是否为mermaid语言，需要特殊处理
      if (language === 'mermaid') {
        // 检查pre元素是否已经标记为处理过
        if (preElement.hasAttribute('data-mermaid-processed')) {
          console.log('跳过已处理的mermaid代码块');
          return;
        }
        
        // 标记为已处理
        preElement.setAttribute('data-mermaid-processed', 'true');
        
        // 创建一个新的mermaid渲染容器
        const mermaidContainer = document.createElement('div');
        mermaidContainer.className = 'mermaid-container';
        
        // 创建mermaid元素
        const mermaidEl = document.createElement('div');
        const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        mermaidEl.id = mermaidId;
        mermaidEl.className = 'mermaid';
        mermaidEl.textContent = code;
        mermaidEl.setAttribute('data-original-content', code);
        
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
        return;
      }
      
      // 检查是否为markdown代码块，可能包含思维导图
      if (handleMarkMaps && (language === 'markdown' || language === 'md') && !block.closest('.markmap-content')) {
        // 首先检查是否在已包含思维导图的agent-response-paragraph中
        const agentResponseParent = block.closest('.agent-response-paragraph');
        if (agentResponseParent && (
            agentResponseParent.querySelector('.markmap-component-wrapper') || 
            agentResponseParent.hasAttribute('data-markmap-rendered') ||
            agentResponseParent.hasAttribute('data-contains-markmap')
          )) {
          console.log('跳过已包含思维导图组件的代理响应段落中的markdown代码块');
          // 标记为已处理，避免后续重复处理
          block.classList.add('markmap-processed');
          block.setAttribute('data-markmap-completed', 'true');
          if (preElement) {
            preElement.setAttribute('data-markmap-processed', 'true');
            preElement.setAttribute('data-markmap-completed', 'true');
          }
          return;
        }
        
        if (isMindMapContent(code)) {
          console.log('在markdown代码块中检测到思维导图内容');
          
          // 标记代码块为已处理
          block.classList.add('markmap-processed');
          block.setAttribute('data-markmap-completed', 'true');
          
          // 标记父元素为已处理
          if (preElement) {
            preElement.setAttribute('data-markmap-processed', 'true');
            preElement.setAttribute('data-markmap-completed', 'true');
          }
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper markmap-rendered';
          
          // 替换原始pre元素
          preElement.replaceWith(markMapContainer);
          
          // 使用Vue创建MarkMap组件
          const markMapApp = createApp({
            render() {
              return h(MarkMap as Component, {
                content: code,
                height: '400px'
              });
            }
          });
          
          // 挂载组件到DOM
          markMapApp.mount(markMapContainer);
          
          // 标记父级agent-response-paragraph为已渲染
          const agentResponseParagraph = markMapContainer.closest('.agent-response-paragraph');
          if (agentResponseParagraph) {
            agentResponseParagraph.setAttribute('data-markmap-rendered', 'true');
            agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
            console.log('标记包含思维导图的响应段落');
          }
          
          return;
        }
      }
      
      // 对于普通代码块，创建CodeBlock组件
      try {
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
          
          // 隐藏原始pre标签
          (preElement as HTMLElement).style.display = 'none';
          preElement.classList.add('replaced-by-component');
        }
      } catch (error) {
        console.error('创建CodeBlock组件失败:', error);
      }
    };
    
    // 处理普通代码块
    const codeBlocks = document.querySelectorAll('pre > code:not(.processed-code-block)');
    console.log(`找到${codeBlocks.length}个未处理的代码块`);
    
    // 创建一个Promise数组来跟踪所有异步代码块处理
    const processingPromises: Array<Promise<any>> = [];
    
    codeBlocks.forEach(block => {
      // 标记为已处理，避免重复处理
      block.classList.add('processed-code-block');
      
      // 获取代码内容和语言
      const code = block.textContent || '';
      let language = 'text';
      
      // 从class中提取语言
      const classList = block.className.split(' ');
      for (const cls of classList) {
        if (cls.startsWith('language-')) {
          language = cls.replace('language-', '');
          break;
        }
      }
      
      // 找到pre标签
      const preElement = block.parentElement;
      if (!preElement) {
        console.warn('无法找到代码块的父元素，跳过处理');
        return;
      }
      
      // 如果语言仍然是text，尝试通过内容猜测语言
      if (language === 'text') {
        try {
          // 检查是否是mermaid图表，通过内容特征判断
          if (code.trim().startsWith('graph ') || 
              code.trim().startsWith('sequenceDiagram') || 
              code.trim().startsWith('classDiagram') || 
              code.trim().startsWith('flowchart')) {
            language = 'mermaid';
            // 处理已知语言的代码块
            processCodeBlock(block, preElement, code, language);
          } else {
            // 使用highlight.js的自动检测
            const detectLanguagePromise = import('highlight.js')
              .then(module => {
                const hljs = module.default;
                try {
                  const result = hljs.highlightAuto(code);
                  language = result.language || 'text';
                  console.log(`自动检测语言结果: ${language}`);
                  
                  // 继续处理代码块
                  processCodeBlock(block, preElement, code, language);
                } catch (error) {
                  console.error('语言检测失败:', error);
                  processCodeBlock(block, preElement, code, 'text');
                }
              })
              .catch(error => {
                console.error('导入highlight.js失败:', error);
                processCodeBlock(block, preElement, code, 'text');
              });
            
            processingPromises.push(detectLanguagePromise);
          }
        } catch (error) {
          console.error('语言检测失败:', error);
          processCodeBlock(block, preElement, code, 'text');
        }
      } else {
        // 对于已知语言的代码块，直接处理
        processCodeBlock(block, preElement, code, language);
      }
    });
    
    // 等待所有异步处理完成
    await Promise.all(processingPromises);
    
    // 渲染mermaid图表
    renderMermaidDiagrams();
    
    // 处理思维导图内容（如果请求的话）
    if (handleMarkMaps) {
      // 先标记所有已包含思维导图的agent-response-paragraph
      document.querySelectorAll('.agent-response-paragraph').forEach(el => {
        if (el.querySelector('.markmap-component-wrapper')) {
          el.setAttribute('data-markmap-rendered', 'true');
          el.setAttribute('data-contains-markmap', 'true');
        }
      });
      
      const paragraphs = document.querySelectorAll('p:not(.processed-markmap):not(.markmap-processed):not([data-markmap-completed])');
      paragraphs.forEach(p => {
        // 检查是否在已经有思维导图的容器中
        const agentParent = p.closest('.agent-response-paragraph[data-contains-markmap="true"]');
        if (agentParent) {
          console.log('跳过已包含思维导图的响应段落中的段落');
          p.classList.add('processed-markmap');
          p.classList.add('markmap-processed');
          p.setAttribute('data-markmap-completed', 'true');
          return;
        }
        
        p.classList.add('processed-markmap');
        p.classList.add('markmap-processed');
        p.setAttribute('data-markmap-completed', 'true');
        const content = p.textContent || '';
        if (isMindMapContent(content)) {
          console.log('在普通段落中检测到思维导图内容');
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper markmap-rendered';
          
          // 替换原始段落元素
          p.replaceWith(markMapContainer);
          
          // 使用Vue创建MarkMap组件
          const markMapApp = createApp({
            render() {
              return h(MarkMap as Component, {
                content: content,
                height: '400px'
              });
            }
          });
          
          // 挂载组件到DOM
          markMapApp.mount(markMapContainer);
          
          // 标记父级容器
          const agentResponseParagraph = markMapContainer.closest('.agent-response-paragraph');
          if (agentResponseParagraph) {
            agentResponseParagraph.setAttribute('data-markmap-rendered', 'true');
            agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
          }
        }
      });
      
      // 处理markmap-content类的元素（预处理的思维导图内容）
      const markmapElements = document.querySelectorAll('.markmap-content:not(.processed-markmap):not(.markmap-processed):not([data-markmap-completed])');
      markmapElements.forEach(element => {
        // 检查是否在已包含思维导图的容器中
        const agentParent = element.closest('.agent-response-paragraph[data-contains-markmap="true"]');
        if (agentParent) {
          console.log('跳过已包含思维导图的响应段落中的标记元素');
          element.classList.add('processed-markmap');
          element.classList.add('markmap-processed');
          element.setAttribute('data-markmap-completed', 'true');
          return;
        }
        
        element.classList.add('processed-markmap');
        element.classList.add('markmap-processed');
        element.setAttribute('data-markmap-completed', 'true');
        try {
          // 获取编码的内容
          const encodedContent = element.getAttribute('data-content');
          if (encodedContent) {
            const content = decodeURIComponent(encodedContent);
            
            console.log('找到思维导图内容，创建MarkMap组件');
            
            // 创建MarkMap组件容器
            const markMapContainer = document.createElement('div');
            markMapContainer.className = 'markmap-component-wrapper markmap-rendered';
            
            // 替换原始元素
            element.replaceWith(markMapContainer);
            
            // 使用Vue创建MarkMap组件
            const markMapApp = createApp({
              render() {
                return h(MarkMap as Component, {
                  content: content,
                  height: '400px'
                });
              }
            });
            
            // 挂载组件到DOM
            markMapApp.mount(markMapContainer);
            
            // 标记父级容器
            const agentResponseParagraph = markMapContainer.closest('.agent-response-paragraph');
            if (agentResponseParagraph) {
              agentResponseParagraph.setAttribute('data-markmap-rendered', 'true');
              agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
            }
          }
        } catch (error) {
          console.error('处理思维导图内容失败:', error);
        }
      });
    }
    
    console.log('已处理代码块、图表和思维导图');
  } catch (error) {
    console.error('处理代码块失败:', error);
  }
};

/**
 * 确保代码块有语言标识
 */
export const ensureCodeBlocksHaveLanguage = () => {
  // 先清理废弃的代码块组件
  const oldComponents = document.querySelectorAll('.code-block-component-wrapper');
  oldComponents.forEach(comp => {
    comp.remove();
  });
  
  // 移除之前处理过的标记
  const processedBlocks = document.querySelectorAll('.processed-code-block');
  processedBlocks.forEach(block => {
    block.classList.remove('processed-code-block');
  });
  
  const processedMarkmaps = document.querySelectorAll('.processed-markmap');
  processedMarkmaps.forEach(el => {
    el.classList.remove('processed-markmap');
  });
  
  // 显示被隐藏的pre元素
  const hiddenPreElements = document.querySelectorAll('.replaced-by-component');
  hiddenPreElements.forEach(el => {
    (el as HTMLElement).style.display = '';
    el.classList.remove('replaced-by-component');
  });
  
  // 重新渲染所有代码块
  renderCodeBlocks();
};

/**
 * 实时渲染mermaid图表
 * 用于在对话过程中动态渲染新增的mermaid图表
 */
export const renderMermaidDynamically = () => {
  try {
    console.log('尝试实时渲染mermaid图表');
    
    // 首先处理可能已经被错误渲染的元素
    fixBrokenMermaidElements();
    
    // 重置特殊标记，确保即使有flow-processed标记的元素也能被渲染
    const flowProcessedElements = document.querySelectorAll('.mermaid.flow-processed:not([data-processed])');
    if (flowProcessedElements.length > 0) {
      console.log(`找到${flowProcessedElements.length}个带有flow-processed标记的mermaid元素，重置这些标记`);
      flowProcessedElements.forEach(el => {
        (el as HTMLElement).classList.remove('flow-processed');
      });
    }
    
    // 查找所有尚未渲染的mermaid图表
    const unprocessedMermaidDivs = document.querySelectorAll(
      '.mermaid:not([data-processed])'
    ) as NodeListOf<HTMLElement>;
    
    if (unprocessedMermaidDivs.length > 0) {
      console.log(`找到${unprocessedMermaidDivs.length}个未处理的mermaid图表，开始渲染`);
      
      // 标记这些元素为已处理
      unprocessedMermaidDivs.forEach(div => {
        // 确保每个mermaid元素都有一个ID (渲染需要)
        if (!div.id) {
          div.id = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        }
        
        // 确保内容为纯文本，不包含SVG等错误内容
        ensurePureTextContent(div);
      });
      
      // 用于兼容历史会话和实时对话的渲染方法
      try {
        // 先尝试使用较新的API (用于对话渲染)
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'loose',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
          fontSize: 14,
          flowchart: {
            htmlLabels: true,
            curve: 'basis',
            useMaxWidth: false // 使用真实宽度而不是最大宽度
          },
          sequence: {
            useMaxWidth: false, // 使用真实宽度而不是最大宽度
            diagramMarginX: 50, // 增加左右边距
            diagramMarginY: 10  // 增加上下边距
          }
        });
        
        // 尝试所有可能的渲染路径
        const tryRenderMethods = async () => {
          // 路径1: 尝试使用run方法（最新版本）
          try {
            if (typeof mermaid.run === 'function') {
              console.log('尝试使用mermaid.run渲染');
              await mermaid.run({
                querySelector: '.mermaid:not([data-processed])',
              });
              return true;
            }
          } catch (runError) {
            console.log('mermaid.run失败', runError);
          }
          
          // 路径2: 尝试使用init方法（传统版本）
          try {
            console.log('尝试使用mermaid.init渲染');
            mermaid.init(undefined, unprocessedMermaidDivs);
            return true;
          } catch (initError) {
            console.log('mermaid.init失败', initError);
          }
          
          // 路径3: 逐个元素渲染
          try {
            console.log('尝试逐个渲染mermaid元素');
            let anySucceeded = false;
            
            for (const div of unprocessedMermaidDivs) {
              try {
                const id = div.id;
                const content = div.textContent || '';
                
                if (content.trim() && !content.includes('<svg')) {
                  await mermaid.render(id, content);
                  anySucceeded = true;
                }
              } catch (renderError) {
                console.error(`单个mermaid元素(${div.id})渲染失败:`, renderError);
              }
            }
            
            return anySucceeded;
          } catch (individualError) {
            console.log('逐个渲染失败', individualError);
          }
          
          // 所有方法都失败
          return false;
        };
        
        // 执行渲染并检查结果
        tryRenderMethods().then(success => {
          if (!success) {
            console.error('所有mermaid渲染方法都失败');
            // 即使全部失败，也尝试检查内容并重置问题元素，以便下次渲染
            const brokenElements = document.querySelectorAll('.mermaid[data-processed]') as NodeListOf<HTMLElement>;
            brokenElements.forEach(el => {
              const svg = el.querySelector('svg');
              if (!svg || (svg.textContent && svg.textContent.includes('Error'))) {
                // 获取原始内容并重置
                const originalContent = el.getAttribute('data-original-content');
                if (originalContent) {
                  try {
                    el.innerHTML = decodeURIComponent(originalContent);
                    el.removeAttribute('data-processed');
                    el.classList.remove('mermaid-processed');
                    console.log('重置了问题mermaid元素，以备后续渲染');
                  } catch (e) {
                    console.error('重置mermaid元素失败:', e);
                  }
                }
              }
            });
          } else {
            // 渲染成功后，确保所有SVG居中显示
            setTimeout(() => {
              const renderedSvgs = document.querySelectorAll('svg[id^="mermaid-"]');
              renderedSvgs.forEach(svg => {
                // 只给SVG元素本身添加居中样式，不改变容器的text-align
                svg.setAttribute('style', 'display: block !important; margin: 0 auto !important; max-width: 100% !important; width: fit-content !important;');
                
                // 为SVG的g元素添加适当的样式，但不改变文本对齐
                const svgChildElements = svg.querySelectorAll('g');
                svgChildElements.forEach(el => {
                  const currentTransform = el.getAttribute('transform') || '';
                  if (!currentTransform.includes('translateX(-50%)')) {
                    el.setAttribute('style', 'margin: 0 auto !important;');
                  }
                });
              });
              
              // 给SVG添加mermaid-success类，标记渲染成功
              renderedSvgs.forEach(svg => {
                svg.classList.add('mermaid-success');
              });
              
              console.log('已为渲染的mermaid图表添加居中样式');
            }, 200); // 延迟执行，确保DOM已经完全更新
            
            // 添加一个额外的检查，确保所有mermaid容器都有正确的样式
            setTimeout(() => {
              const mermaidContainers = document.querySelectorAll('.mermaid-container, .mermaid-wrapper, .mermaid-block');
              mermaidContainers.forEach(container => {
                const mermaidEl = container.querySelector('.mermaid:not([data-processed])');
                if (mermaidEl && !mermaidEl.querySelector('svg')) {
                  // 如果容器中的mermaid元素没有SVG，说明可能渲染失败，尝试重渲染
                  console.log('检测到未成功渲染的mermaid元素，尝试重新渲染');
                  
                  // 重新初始化该元素
                  if (mermaidEl.id) {
                    mermaidEl.removeAttribute('data-processed');
                    mermaidEl.classList.remove('mermaid-processed');
                    
                    // 尝试使用render方法单独渲染
                    const content = mermaidEl.textContent || '';
                    if (content && !content.includes('<svg')) {
                      try {
                        mermaid.render(mermaidEl.id, content).catch(e => {
                          console.error('单独渲染mermaid元素失败:', e);
                        });
                      } catch (e) {
                        console.error('尝试渲染mermaid元素时出错:', e);
                      }
                    }
                  }
                }
              });
            }, 500);
          }
        });
      } catch (outerError) {
        console.error('mermaid渲染过程中发生错误:', outerError);
      }
    } else {
      console.log('没有找到需要渲染的mermaid图表');
    }
  } catch (error) {
    console.error('实时渲染mermaid图表失败:', error);
  }
};

/**
 * 确保mermaid元素内容为纯文本，修复可能的SVG嵌套问题
 */
const ensurePureTextContent = (element: HTMLElement) => {
  // 检查元素内容是否已经包含了SVG标签，这表明可能已经渲染过
  const content = element.innerHTML;
  if (content.includes('<svg') || content.includes('data-processed')) {
    // 获取原始代码内容（可能存储在data属性中）
    let originalContent = element.getAttribute('data-original-content');
    
    // 检查是否是URL编码的内容，需要解码
    if (originalContent && originalContent.includes('%')) {
      try {
        originalContent = decodeURIComponent(originalContent);
      } catch (e) {
        console.error('解码data-original-content失败:', e);
      }
    }
    
    if (originalContent) {
      // 如果有原始内容，重置为原始内容
      element.innerHTML = originalContent;
      console.log('已重置mermaid元素到原始内容');
    } else {
      // 如果没有原始内容，但有SVG，移除该元素的处理标记，让它可以被重新渲染
      element.removeAttribute('data-processed');
      console.log('移除了mermaid元素的处理标记');
    }
  } else {
    // 如果是纯文本内容，备份原始内容
    element.setAttribute('data-original-content', content);
  }
};

/**
 * 修复已经被错误渲染的mermaid元素
 */
const fixBrokenMermaidElements = () => {
  // 查找所有包含SVG但可能渲染错误的mermaid元素
  const processedElements = document.querySelectorAll('.mermaid[data-processed]') as NodeListOf<HTMLElement>;
  
  processedElements.forEach(el => {
    const svgElement = el.querySelector('svg');
    if (svgElement) {
      // 检查是否有明显的错误特征
      const errorText = svgElement.textContent || '';
      const hasError = errorText.includes('No diagram type detected') || 
                      errorText.includes('UnknownDiagramError') ||
                      errorText.includes('Syntax error');
      
      if (hasError) {
        console.log('检测到错误渲染的mermaid元素，尝试修复');
        
        // 移除处理标记
        el.removeAttribute('data-processed');
        el.classList.remove('mermaid-processed');
        
        // 获取原始内容
        const originalContent = el.getAttribute('data-original-content');
        if (originalContent) {
          // 重置内容
          el.innerHTML = originalContent;
          console.log('重置了错误渲染的mermaid元素');
        } else {
          // 如果没有原始内容，移除整个节点，无法修复
          if (el.parentNode) {
            el.parentNode.removeChild(el);
            console.log('移除了无法修复的mermaid元素');
          }
        }
      }
    }
  });
};

/**
 * 添加mermaid自动渲染监听
 * 用于监听DOM变化并自动渲染新增的mermaid图表和markmap思维导图
 */
export const setupMermaidAutoRender = () => {
  try {
    // 保存流式输出阶段检测到的图表状态
    let pendingMermaidRender = false;
    let pendingMarkmapRender = false;
    
    // 添加防抖控制变量，防止短时间内多次触发渲染
    let renderingInProgress = false;
    let renderTimeout: number | null = null;
    
    // 创建一个MutationObserver来监视DOM变化
    const observer = new MutationObserver((mutations) => {
      let hasMermaidContent = false;
      let hasMarkmapContent = false;
      
      // 如果渲染正在进行中，不再继续检测
      if (renderingInProgress) return;
      
      // 检查变化中是否有新增的mermaid或markmap内容
      mutations.forEach(mutation => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              const element = node as Element;
              
              // 检查mermaid内容
              const mermaidElements = element.querySelectorAll('.mermaid');
              if (mermaidElements.length > 0) {
                hasMermaidContent = true;
              }
              
              if (element.classList && element.classList.contains('mermaid')) {
                hasMermaidContent = true;
              }
              
              // 检查markmap内容
              const markmapElements = element.querySelectorAll('.markmap-content, pre > code.language-markdown, pre > code.language-md');
              if (markmapElements.length > 0) {
                hasMarkmapContent = true;
              }
              
              // 如果新增节点本身是markmap元素
              if (element.classList && 
                  (element.classList.contains('markmap-content') || 
                   element.classList.contains('language-markdown') || 
                   element.classList.contains('language-md'))) {
                hasMarkmapContent = true;
              }
            }
          });
        }
      });
      
      // 仅标记等待渲染，但不立即渲染
      if (hasMermaidContent) {
        console.log('检测到DOM变化中有新增的mermaid内容，标记等待流式输出结束后渲染');
        pendingMermaidRender = true;
      }
      
      // 仅标记等待渲染，但不立即渲染
      if (hasMarkmapContent) {
        console.log('检测到DOM变化中有新增的markmap内容，标记等待流式输出结束后渲染');
        pendingMarkmapRender = true;
      }
      
      // 不再自动调用renderPending，而是等待流式输出结束时的明确调用
    });
    
    // 开始监听整个文档
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    
    console.log('已设置自动渲染监听（等待流式输出结束后统一渲染）');
    
    // 返回observer以及触发渲染的方法，以便需要时停止监听或手动触发渲染
    return {
      disconnect: () => observer.disconnect(),
      renderPending: (force = false) => {
        // 如果已有渲染正在进行中，取消之前的延迟执行
        if (renderTimeout) {
          clearTimeout(renderTimeout);
        }
        
        // 设置渲染中状态，防止重复触发
        renderingInProgress = true;
        
        console.log('开始处理积累的渲染请求，force =', force);
        
        // 使用单一超时函数处理所有渲染
        renderTimeout = setTimeout(() => {
          try {
            if (pendingMermaidRender || force) {
              console.log('流式输出结束，开始渲染积累的mermaid图表');
              pendingMermaidRender = false;
              
              // 先给所有标记元素重置状态
              const markedElements = document.querySelectorAll('.mermaid.flow-processed, .mermaid.mermaid-processed');
              if (markedElements.length > 0) {
                markedElements.forEach(el => {
                  if (!(el as HTMLElement).hasAttribute('data-processed')) {
                    (el as HTMLElement).classList.remove('flow-processed');
                    (el as HTMLElement).classList.remove('mermaid-processed');
                  }
                });
              }
              
              // 然后执行渲染
              renderMermaidDynamically();
            }
            
            if (pendingMarkmapRender || force) {
              console.log('流式输出结束，开始渲染积累的markmap思维导图');
              pendingMarkmapRender = false;
              
              // 延迟渲染思维导图确保mermaid已完成
              setTimeout(() => {
                // 执行渲染思维导图
                renderMarkMaps();
              }, 300);
            }
          } finally {
            // 确保无论是否发生错误，都重置渲染状态
            setTimeout(() => {
              renderingInProgress = false;
              renderTimeout = null;
            }, 500); // 给一个短暂的冷却期
          }
        }, 300); // 延迟执行，避免频繁渲染
      }
    };
  } catch (error) {
    console.error('设置自动渲染监听失败:', error);
    return {
      disconnect: () => {},
      renderPending: () => {}
    };
  }
};

/**
 * 彻底清理思维导图相关的DOM元素和标记
 * 防止重复渲染和干扰
 */
export const cleanupMarkmapElements = () => {
  try {
    console.log('清理思维导图相关元素');
    
    // 1. 移除所有思维导图组件实例 - 这是最重要的部分
    const markmapWrappers = document.querySelectorAll('.markmap-component-wrapper, .markmap-rendered, .markmap-wrapper');
    if (markmapWrappers.length > 0) {
      console.log(`移除${markmapWrappers.length}个思维导图组件`);
      markmapWrappers.forEach(el => el.remove());
    }
    
    // 2. 只移除关键标记，减少DOM操作以提高性能
    const markedElements = document.querySelectorAll('[data-markmap-rendered], [data-contains-markmap]');
    if (markedElements.length > 0) {
      console.log(`清理${markedElements.length}个已标记元素`);
      markedElements.forEach(el => {
        el.removeAttribute('data-markmap-rendered');
        el.removeAttribute('data-contains-markmap');
      });
    }
    
    // 3. 重置全局锁，确保不会因为锁而阻塞渲染
    (window as any)['markmap-rendering-in-progress'] = false;
    
    console.log('思维导图元素清理完成');
  } catch (error) {
    console.error('清理思维导图元素时出错:', error);
    // 确保出错时也释放锁
    (window as any)['markmap-rendering-in-progress'] = false;
  }
};

/**
 * 专门处理MarkMap思维导图的渲染
 * 在流式输出结束后被调用
 */
export const renderMarkMaps = async () => {
  try {
    console.log('开始处理MarkMap思维导图');
    
    // 导入MarkMap组件
    const MarkMapModule = await import('../components/rendering/MarkMap.vue');
    const MarkMap = MarkMapModule.default;
    
    // 简化锁检查逻辑
    const renderLockKey = 'markmap-rendering-in-progress';
    if ((window as any)[renderLockKey]) {
      console.log('已有思维导图渲染进程，检查锁定时间');
      // 如果锁定时间超过3秒，强制释放锁
      if (Date.now() - ((window as any)['markmap-lock-time'] || 0) > 3000) {
        console.log('检测到锁定时间超过3秒，强制释放锁');
        (window as any)[renderLockKey] = false;
      } else {
        console.log('跳过本次渲染，等待现有渲染完成');
        return;
      }
    }
    
    // 设置锁，并记录时间
    (window as any)[renderLockKey] = true;
    (window as any)['markmap-lock-time'] = Date.now();
    
    // 获取已处理的元素ID集合
    const processedIds = new Set<string>(
      (window as any)['processedMarkMapElements'] || []
    );
    
    // 记录已渲染的思维导图，避免重复渲染相同内容
    const renderedMaps = new Set<string>();
    
    try {
      // 简化清理逻辑，只移除组件实例，不做大量DOM操作
      const existingMarkmaps = document.querySelectorAll('.markmap-component-wrapper, .markmap-rendered');
      if (existingMarkmaps.length > 0) {
        console.log(`移除${existingMarkmaps.length}个已存在的思维导图组件，重新渲染`);
        existingMarkmaps.forEach(el => el.remove());
      }
      
      // 查找所有待处理的思维导图内容
      const markdownBlocks = document.querySelectorAll('pre > code.language-markdown, pre > code.language-md, pre.markmap-to-process > code');
      console.log(`找到${markdownBlocks.length}个可能包含思维导图的markdown代码块`);
      
      // 跟踪处理了多少个思维导图
      let processedCount = 0;
      
      // 处理markdown代码块中的思维导图
      for (const block of markdownBlocks) {
        const code = block.textContent || '';
        const preElement = block.closest('pre');
        
        if (!preElement) {
          console.log('找不到父级pre元素，跳过');
          continue;
        }
        
        // 获取元素唯一标识
        const elementId = preElement.getAttribute('data-element-id') || 
                          block.getAttribute('data-element-id');
                          
        // 避免重复处理同一个内容
        if (elementId && renderedMaps.has(elementId)) {
          console.log(`跳过已渲染的思维导图，ID: ${elementId}`);
          continue;
        }
        
        // 使用内容的前50个字符作为内容指纹
        const contentFingerprint = code.substring(0, 50);
        if (renderedMaps.has(contentFingerprint)) {
          console.log('跳过与已渲染内容相同的思维导图');
          continue;
        }
        
        // 检查内容是否符合思维导图格式
        if (isMindMapContent(code)) {
          console.log('检测到思维导图内容，创建MarkMap组件');
          
          // 标记为已处理
          if (elementId) {
            renderedMaps.add(elementId);
          }
          renderedMaps.add(contentFingerprint);
          
          processedCount++;
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper markmap-rendered';
          if (elementId) {
            markMapContainer.setAttribute('data-element-id', elementId);
          }
          
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
          
          // 标记父级agent-response-paragraph
          const agentResponseParagraph = markMapContainer.closest('.agent-response-paragraph');
          if (agentResponseParagraph) {
            agentResponseParagraph.setAttribute('data-markmap-rendered', 'true');
            agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
            console.log('标记包含新渲染思维导图的响应段落');
          }
        }
      }
      
      // 处理普通段落中的思维导图内容
      const paragraphs = document.querySelectorAll('p');
      for (const p of paragraphs) {
        // 跳过已经被处理或替换的段落
        if (p.closest('.markmap-component-wrapper') || 
            p.closest('[data-contains-markmap="true"]')) {
          continue;
        }
        
        // 获取元素唯一标识
        const elementId = p.getAttribute('data-element-id');
        
        // 避免重复处理同一个元素
        if (elementId && renderedMaps.has(elementId)) {
          console.log(`跳过已渲染的思维导图段落，ID: ${elementId}`);
          continue;
        }
        
        const content = p.textContent || '';
        
        // 使用内容的前50个字符作为内容指纹
        const contentFingerprint = content.substring(0, 50);
        if (renderedMaps.has(contentFingerprint)) {
          console.log('跳过与已渲染内容相同的思维导图段落');
          continue;
        }
        
        // 检查内容是否符合思维导图格式
        if (isMindMapContent(content)) {
          console.log('在段落中检测到思维导图内容，创建MarkMap组件');
          
          // 标记为已处理
          if (elementId) {
            renderedMaps.add(elementId);
          }
          renderedMaps.add(contentFingerprint);
          
          processedCount++;
          
          // 创建MarkMap组件
          const markMapEl = document.createElement('div');
          markMapEl.className = 'markmap-component-wrapper markmap-rendered';
          if (elementId) {
            markMapEl.setAttribute('data-element-id', elementId);
          }
          
          // 替换原始段落
          p.replaceWith(markMapEl);
          
          // 使用创建MarkMap组件
          const markMapApp = createApp(MarkMap, {
            content: content,
            height: '400px'
          });
          
          // 挂载组件到DOM
          markMapApp.mount(markMapEl);
          
          // 标记父级agent-response-paragraph
          const agentResponseParagraph = markMapEl.closest('.agent-response-paragraph');
          if (agentResponseParagraph) {
            agentResponseParagraph.setAttribute('data-markmap-rendered', 'true');
            agentResponseParagraph.setAttribute('data-contains-markmap', 'true');
          }
        }
      }
      
      console.log(`所有MarkMap思维导图处理完成，本次共处理${processedCount}个思维导图`);
    } finally {
      // 更快地释放锁
      setTimeout(() => {
        (window as any)[renderLockKey] = false;
        console.log('思维导图渲染锁已释放');
      }, 200); // 从500ms减少到200ms
    }
  } catch (error) {
    console.error('渲染MarkMap思维导图时出错:', error);
    // 确保出错时也释放锁
    (window as any)['markmap-rendering-in-progress'] = false;
  }
};

/**
 * 统一渲染内容组件（思维导图和图表）
 * 该函数作为主入口点，处理所有类型的渲染内容
 * @param force 是否强制渲染所有元素，无视处理标记
 */
export const renderContentComponents = (force = false) => {
  console.log('开始统一渲染内容组件，force =', force);
  
  try {
    // 首先渲染代码块
    renderCodeBlocks(true);
    
    // 然后渲染图表
    renderMermaidDiagrams();
    
    // 最后渲染思维导图
    renderMarkMaps();
    
    // 如果设置了自动渲染监听，也触发一次
    const mermaidObserver = (window as any).mermaidAutoRenderObserver;
    if (mermaidObserver && typeof mermaidObserver.renderPending === 'function') {
      console.log('触发自动渲染监听器');
      mermaidObserver.renderPending(force);
    }
    
    console.log('统一渲染内容组件完成');
    return true;
  } catch (error) {
    console.error('统一渲染内容组件失败:', error);
    return false;
  }
}; 