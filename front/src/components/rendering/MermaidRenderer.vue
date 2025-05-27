<template>
  <div class="mermaid-renderer">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import mermaid from 'mermaid';
import { renderMermaidDynamically, setupMermaidAutoRender } from '../../services/renderService';
import { isMermaidContent } from '../../services/markdownService';

// 在组件挂载时初始化并渲染mermaid图表
let mermaidObserver = null;
let errorCheckInterval = null; // 声明错误检查定时器

onMounted(() => {
  // 初始化mermaid配置
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
    fontSize: 14,
    flowchart: {
      htmlLabels: true,
      curve: 'basis',
      useMaxWidth: false
    },
    sequence: {
      useMaxWidth: false,
      diagramMarginX: 50,
      diagramMarginY: 10
    }
  });
  
  // 立即渲染当前页面中的所有mermaid图表
  renderAllMermaidDiagrams();
  
  // 使用renderService中的自动渲染监听功能
  mermaidObserver = setupMermaidAutoRender();
  
  // 添加防错定时器，每30秒检查一次是否有失败的mermaid渲染，并尝试修复
  errorCheckInterval = setInterval(() => {
    const errorElements = document.querySelectorAll('.mermaid svg:not(.mermaid-success)');
    if (errorElements.length > 0) {
      console.log(`检测到${errorElements.length}个可能渲染失败的mermaid元素，尝试修复`);
      // 导入修复函数
      import('../../services/renderService').then(({ renderMermaidDynamically }) => {
        renderMermaidDynamically();
      });
    }
  }, 30000);
});

// 在组件卸载时清理observer和定时器
onUnmounted(() => {
  console.log('MermaidRenderer: 组件卸载，开始清理资源');
  
  try {
    if (mermaidObserver) {
      if (typeof mermaidObserver.disconnect === 'function') {
        mermaidObserver.disconnect();
      }
      mermaidObserver = null;
    }
    
    if (errorCheckInterval) {
      clearInterval(errorCheckInterval);
      errorCheckInterval = null;
    }
    
    console.log('MermaidRenderer: 资源清理完成');
  } catch (error) {
    console.error('MermaidRenderer: 清理资源时出错:', error);
  }
});

// 渲染所有mermaid图表
const renderAllMermaidDiagrams = async () => {
  try {
    console.log('MermaidRenderer: 尝试渲染所有Mermaid图表...');
    
    // 处理已存在的mermaid标记元素
    processMermaidElements();
    
    // 查找所有未处理的代码块
    const preElements = document.querySelectorAll('pre:not(.mermaid-processed)');
    let processedCount = 0;
    
    for (const preElement of preElements) {
      // 查找内部的代码块
      const codeElement = preElement.querySelector('code');
      if (!codeElement) continue;
      
      // 获取代码内容
      const code = codeElement.textContent || '';
      
      // 使用markdownService中的函数检查是否是mermaid图表
      if (isMermaidContent(code)) {
        // 标记为已处理
        preElement.classList.add('mermaid-processed');
        
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
        processedCount++;
      }
    }
    
    if (processedCount > 0) {
      console.log(`MermaidRenderer: 处理了${processedCount}个mermaid代码块`);
    }
    
    // 延迟渲染确保DOM完全更新
    setTimeout(() => {
      // 使用renderService中的动态渲染函数
      renderMermaidDynamically();
      
      // 再次确保所有渲染的SVG居中显示
      setTimeout(() => {
        const renderedSvgs = document.querySelectorAll('svg[id^="mermaid-"]');
        renderedSvgs.forEach(svg => {
          // 只给SVG元素本身添加居中样式
          svg.setAttribute('style', 'display: block !important; margin: 0 auto !important; max-width: 100% !important; width: fit-content !important;');
          
          // 为SVG的g元素添加适当的样式
          const svgChildElements = svg.querySelectorAll('g');
          svgChildElements.forEach(el => {
            const currentTransform = el.getAttribute('transform') || '';
            if (!currentTransform.includes('translateX(-50%)')) {
              el.setAttribute('style', 'margin: 0 auto !important;');
            }
          });
        });
        console.log('已确保所有mermaid图表居中显示');
      }, 300);
    }, 100);
  } catch (error) {
    console.error('MermaidRenderer: 渲染Mermaid图表失败:', error);
  }
};

// 处理已有的mermaid元素
const processMermaidElements = () => {
  try {
    // 首先尝试查找所有.mermaid元素但不包括已经创建过的.mermaid-container中的元素
    const mermaidElements = document.querySelectorAll('.mermaid:not(.mermaid-processed)');
    let processedCount = 0;
    
    mermaidElements.forEach(mermaidEl => {
      // 跳过已经在mermaid容器中的元素
      if (mermaidEl.closest('.mermaid-container')) {
        return;
      }
      
      // 标记为已处理
      mermaidEl.classList.add('mermaid-processed');
      
      // 检查是否需要包装
      const needsWrapping = !mermaidEl.closest('.mermaid-block');
      
      if (needsWrapping) {
        const code = mermaidEl.textContent || '';
        
        // 创建mermaid容器
        const mermaidContainer = document.createElement('div');
        mermaidContainer.className = 'mermaid-container';
        
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
        
        // 确保mermaid元素有ID
        if (!mermaidEl.id) {
          mermaidEl.id = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        }
        
        // 克隆原始元素
        const clonedEl = mermaidEl.cloneNode(true);
        mermaidContainer.appendChild(clonedEl);
        mermaidContainer.appendChild(copyButton);
        
        // 替换原始元素
        mermaidEl.replaceWith(mermaidContainer);
        processedCount++;
      }
    });
    
    if (processedCount > 0) {
      console.log(`MermaidRenderer: 处理了${processedCount}个已有mermaid元素`);
    }
  } catch (error) {
    console.error('处理已有mermaid元素失败:', error);
  }
};

// 暴露渲染方法
defineExpose({
  renderAllMermaidDiagrams
});
</script>

<style scoped>
:deep(.mermaid-container) {
  margin: 1em 0;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 15px;
  border: 1px solid #eaecef;
  position: relative;
}

:deep(.mermaid) {
  display: block !important;
  overflow: visible;
  max-width: 100%;
  margin: 0 auto;
}

:deep(.mermaid svg) {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100%;
  width: fit-content !important;
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

/* 全局样式，确保所有mermaid图表居中 */
:global(svg[id^="mermaid-"]) {
  display: block !important;
  margin: 0 auto !important;
  max-width: 100% !important;
  width: fit-content !important;
}

:global(svg[id^="mermaid-"] > *) {
  margin: 0 auto !important;
}
</style> 