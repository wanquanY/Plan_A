<template>
  <div class="mermaid-renderer">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import mermaid from 'mermaid';

// 在组件挂载时初始化并渲染mermaid图表
let mermaidObserver = null;
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
      curve: 'basis'
    }
  });
  
  // 立即渲染当前页面中的所有mermaid图表
  renderAllMermaidDiagrams();
  
  // 创建MutationObserver来监听DOM变化并渲染新增的mermaid图表
  mermaidObserver = new MutationObserver(mutations => {
    let shouldRenderMermaid = false;
    
    mutations.forEach(mutation => {
      if (mutation.type === 'childList' && mutation.addedNodes.length) {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.classList?.contains('mermaid') || 
                node.querySelector?.('.mermaid, code.language-mermaid, pre > code')) {
              shouldRenderMermaid = true;
            }
          }
        });
      }
    });
    
    if (shouldRenderMermaid) {
      setTimeout(() => {
        renderAllMermaidDiagrams();
      }, 100);
    }
  });
  
  // 开始监听整个文档的变化
  mermaidObserver.observe(document.body, {
    childList: true,
    subtree: true
  });
});

// 在组件卸载时清理observer
onUnmounted(() => {
  if (mermaidObserver) {
    mermaidObserver.disconnect();
    mermaidObserver = null;
  }
});

// 渲染所有mermaid图表
const renderAllMermaidDiagrams = async () => {
  try {
    console.log('MermaidRenderer: 尝试渲染所有Mermaid图表...');
    
    // 查找所有未处理的代码块
    const preElements = document.querySelectorAll('pre:not(.mermaid-processed)');
    let processedCount = 0;
    
    for (const preElement of preElements) {
      // 查找内部的代码块
      const codeElement = preElement.querySelector('code');
      if (!codeElement) continue;
      
      // 获取代码内容
      const code = codeElement.textContent || '';
      
      // 检查是否是mermaid图表
      if (code.trim().startsWith('flowchart') || 
          code.trim().startsWith('graph') || 
          code.trim().includes('-->') ||
          code.trim().includes('->') ||
          /[A-Z]\s*-+>\s*[A-Z]/i.test(code)) {
        
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
      
      // 渲染所有mermaid图表
      await mermaid.run({
        querySelector: '.mermaid',
      });
    }
  } catch (error) {
    console.error('MermaidRenderer: 渲染Mermaid图表失败:', error);
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

/* 全局样式，确保所有mermaid图表居中 */
:global(svg[id^="mermaid-"]) {
  display: block !important;
  margin: 0 auto !important;
}
</style> 