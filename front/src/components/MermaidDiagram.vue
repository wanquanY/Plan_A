<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue';
import mermaid from 'mermaid';

// 定义组件的属性
const props = defineProps({
  // 图表内容
  chart: {
    type: String,
    required: true
  },
  // 图表类型（flowchart、sequence、class等）
  chartType: {
    type: String,
    default: 'flowchart'
  },
  // 图表主题
  theme: {
    type: String,
    default: 'default'
  }
});

// 生成唯一ID
const mermaidId = `mermaid-diagram-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
const diagramSvg = ref('');
const isLoading = ref(true);
const isError = ref(false);
const errorMessage = ref('');
const isCopied = ref(false);

// 初始化mermaid
onMounted(() => {
  mermaid.initialize({
    startOnLoad: false,
    theme: props.theme,
    securityLevel: 'loose',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
    fontSize: 14
  });
  
  renderDiagram();
});

// 当图表内容变化时重新渲染
watch(() => props.chart, () => {
  renderDiagram();
});

// 渲染mermaid图表
const renderDiagram = async () => {
  if (!props.chart) return;
  
  isLoading.value = true;
  isError.value = false;
  
  try {
    // 使用mermaid API渲染图表
    const { svg } = await mermaid.render(mermaidId, props.chart);
    diagramSvg.value = svg;
    isLoading.value = false;
  } catch (error) {
    console.error('渲染mermaid图表失败:', error);
    isError.value = true;
    errorMessage.value = error.message || '渲染图表失败';
    isLoading.value = false;
  }
};

// 复制mermaid代码
const copyChart = () => {
  navigator.clipboard.writeText(props.chart)
    .then(() => {
      isCopied.value = true;
      setTimeout(() => {
        isCopied.value = false;
      }, 2000);
    })
    .catch(err => {
      console.error('复制失败:', err);
    });
};

// 组件卸载时清理资源
onUnmounted(() => {
  // 这里不需要清理mermaidObserver，因为该组件没有使用它
  // 如果将来需要，可以在这里添加相关清理代码
});
</script>

<template>
  <div class="mermaid-wrapper">
    <!-- 加载中状态 -->
    <div v-if="isLoading" class="mermaid-loading">
      <div class="spinner"></div>
      <span>正在渲染图表...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="isError" class="mermaid-error">
      <div class="error-icon">!</div>
      <div class="error-message">
        <p>渲染图表失败</p>
        <small>{{ errorMessage }}</small>
      </div>
    </div>
    
    <!-- 渲染成功状态 -->
    <div v-else class="mermaid-content" v-html="diagramSvg"></div>
    
    <!-- 复制按钮 -->
    <div 
      class="code-copy-button" 
      :class="{ 'copied': isCopied }" 
      :title="isCopied ? '已复制!' : '复制图表代码'" 
      @click="copyChart"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.mermaid-wrapper {
  margin: 0.6em 0;
  position: relative;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 15px;
  overflow: auto;
  border: 1px solid #eaecef;
  min-height: 100px;
}

.mermaid-content {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  text-align: center;
}

/* 加载状态样式 */
.mermaid-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  min-height: 150px;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #1677ff;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误状态样式 */
.mermaid-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background-color: #fff5f5;
  border: 1px solid #ffccc7;
  border-radius: 4px;
  color: #f5222d;
}

.error-icon {
  font-size: 24px;
  font-weight: bold;
  margin-right: 10px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: #f5222d;
  color: white;
}

.error-message p {
  margin: 0;
  font-weight: 500;
}

.error-message small {
  display: block;
  margin-top: 4px;
  color: #666;
}

/* 复制按钮样式 */
.code-copy-button {
  position: absolute;
  right: 5px;
  top: 5px;
  background-color: rgba(246, 248, 250, 0.8);
  border-radius: 4px;
  padding: 4px 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease, background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border: 1px solid #eaecef;
  color: #666;
}

.mermaid-wrapper:hover .code-copy-button {
  opacity: 1;
}

.code-copy-button:hover {
  background-color: #f0f0f0;
  color: #0366d6;
}

.code-copy-button.copied {
  background-color: #dcffe4;
  color: #28a745;
  opacity: 1;
}

.code-copy-button svg {
  width: 16px;
  height: 16px;
}

/* 让SVG响应式 */
:deep(svg) {
  max-width: 100%;
  height: auto;
}
</style> 