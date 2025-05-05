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
    const CodeBlockModule = await import('../components/CodeBlock.vue');
    const CodeBlock = CodeBlockModule.default;
    
    // 如果需要处理思维导图，导入MarkMap组件
    let MarkMap: Component | null = null;
    if (handleMarkMaps) {
      const MarkMapModule = await import('../components/MarkMap.vue');
      MarkMap = MarkMapModule.default;
    }
    
    // 处理代码块的函数
    const processCodeBlock = (block: Element, preElement: Element, code: string, language: string) => {
      console.log(`处理代码块，语言: ${language}`);
      
      // 检查是否为mermaid语言，需要特殊处理
      if (language === 'mermaid') {
        return; // mermaid图表已由mermaid库处理
      }
      
      // 检查是否为markdown代码块，可能包含思维导图
      if (handleMarkMaps && (language === 'markdown' || language === 'md') && !block.closest('.markmap-content')) {
        if (isMindMapContent(code)) {
          console.log('在markdown代码块中检测到思维导图内容');
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper';
          
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
      const paragraphs = document.querySelectorAll('p:not(.processed-markmap)');
      paragraphs.forEach(p => {
        p.classList.add('processed-markmap');
        const content = p.textContent || '';
        if (isMindMapContent(content)) {
          console.log('在普通段落中检测到思维导图内容');
          
          // 创建MarkMap组件容器
          const markMapContainer = document.createElement('div');
          markMapContainer.className = 'markmap-component-wrapper';
          
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
        }
      });
      
      // 处理markmap-content类的元素（预处理的思维导图内容）
      const markmapElements = document.querySelectorAll('.markmap-content:not(.processed-markmap)');
      markmapElements.forEach(element => {
        element.classList.add('processed-markmap');
        try {
          // 获取编码的内容
          const encodedContent = element.getAttribute('data-content');
          if (encodedContent) {
            const content = decodeURIComponent(encodedContent);
            
            console.log('找到思维导图内容，创建MarkMap组件');
            
            // 创建MarkMap组件容器
            const markMapContainer = document.createElement('div');
            markMapContainer.className = 'markmap-component-wrapper';
            
            // 替换原始pre元素
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
    
    // 查找所有尚未渲染的mermaid图表
    const unprocessedMermaidDivs = document.querySelectorAll('.mermaid:not(.mermaid-processed):not([data-processed])') as NodeListOf<HTMLElement>;
    
    if (unprocessedMermaidDivs.length > 0) {
      console.log(`找到${unprocessedMermaidDivs.length}个未处理的mermaid图表，开始渲染`);
      
      // 标记这些元素为已处理
      unprocessedMermaidDivs.forEach(div => {
        div.classList.add('mermaid-processed');
        
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
                const mermaidEl = container.querySelector('.mermaid');
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
 * 用于监听DOM变化并自动渲染新增的mermaid图表
 */
export const setupMermaidAutoRender = () => {
  try {
    // 创建一个MutationObserver来监视DOM变化
    const observer = new MutationObserver((mutations) => {
      let hasMermaidContent = false;
      
      // 检查变化中是否有新增的mermaid内容
      mutations.forEach(mutation => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              const element = node as Element;
              // 直接检查新增节点
              const mermaidElements = element.querySelectorAll('.mermaid:not(.mermaid-processed)');
              if (mermaidElements.length > 0) {
                hasMermaidContent = true;
              }
              
              // 如果新增节点本身就是mermaid元素
              if (element.classList && element.classList.contains('mermaid') && 
                  !element.classList.contains('mermaid-processed')) {
                hasMermaidContent = true;
              }
            }
          });
        }
      });
      
      // 如果检测到新的mermaid内容，触发渲染
      if (hasMermaidContent) {
        console.log('检测到DOM变化中有新增的mermaid内容，触发渲染');
        // 使用setTimeout允许DOM完全更新
        setTimeout(() => {
          renderMermaidDynamically();
        }, 100);
      }
    });
    
    // 开始监听整个文档
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    
    console.log('已设置mermaid自动渲染监听');
    
    // 返回observer以便需要时停止监听
    return observer;
  } catch (error) {
    console.error('设置mermaid自动渲染监听失败:', error);
    return null;
  }
}; 