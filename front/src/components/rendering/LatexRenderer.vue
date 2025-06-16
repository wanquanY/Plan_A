<template>
  <component 
    :is="isBlock ? 'div' : 'span'" 
    class="latex-container" 
    :class="{ 'latex-block': isBlock, 'latex-inline': !isBlock }"
  >
    <component :is="isBlock ? 'div' : 'span'" ref="mathRef" class="latex-content"></component>
    <div v-if="error" class="latex-error">
      <span class="error-icon">⚠️</span>
      <span class="error-message">{{ error }}</span>
      <div class="error-code">{{ latex }}</div>
    </div>
  </component>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
import katex from 'katex';

interface Props {
  latex: string;
  isBlock?: boolean;
  displayMode?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isBlock: false,
  displayMode: false
});

const mathRef = ref<HTMLElement | null>(null);
const error = ref<string>('');

const renderLatex = async () => {
  if (!mathRef.value || !props.latex) return;
  
  try {
    error.value = '';
    
    // 清空之前的内容
    mathRef.value.innerHTML = '';
    
    // KaTeX渲染选项
    const options = {
      displayMode: props.displayMode || props.isBlock,
      throwOnError: false,
      errorColor: '#cc0000',
      strict: false,
      trust: false,
      macros: {
        // 常用数学宏定义
        "\\RR": "\\mathbb{R}",
        "\\NN": "\\mathbb{N}",
        "\\ZZ": "\\mathbb{Z}",
        "\\QQ": "\\mathbb{Q}",
        "\\CC": "\\mathbb{C}",
        "\\vec": "\\overrightarrow{#1}",
        "\\norm": "\\left\\|#1\\right\\|",
        "\\abs": "\\left|#1\\right|",
        "\\inner": "\\langle#1,#2\\rangle"
      }
    };
    
    // 渲染LaTeX
    katex.render(props.latex, mathRef.value, options);
    
  } catch (err: any) {
    console.error('LaTeX渲染错误:', err);
    error.value = err.message || 'LaTeX渲染失败';
  }
};

// 监听props变化，重新渲染
watch(() => [props.latex, props.isBlock, props.displayMode], async () => {
  await nextTick();
  renderLatex();
}, { immediate: false });

onMounted(() => {
  renderLatex();
});
</script>

<style scoped>
.latex-container {
  position: relative;
  margin: 0;
  padding: 0;
}

.latex-inline {
  display: inline;
  vertical-align: baseline;
}

.latex-block {
  display: block;
  margin: 1em 0;
  text-align: center;
  background-color: #fafafa;
  border: 1px solid #e1e5e9;
  border-radius: 6px;
  padding: 12px;
}

.latex-content {
  color: #333;
  font-family: 'KaTeX_Main', 'Times New Roman', serif;
}

.latex-error {
  background-color: #ffebee;
  border: 1px solid #f44336;
  border-radius: 4px;
  padding: 8px 12px;
  margin: 4px 0;
  font-size: 0.875em;
  color: #d32f2f;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.error-icon {
  font-size: 1.2em;
}

.error-message {
  font-weight: 500;
}

.error-code {
  font-family: 'Courier New', monospace;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: 4px 6px;
  font-size: 0.8em;
  color: #666;
  word-break: break-all;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .latex-block {
    padding: 8px;
    margin: 0.8em 0;
  }
  
  .latex-content {
    font-size: 0.9em;
  }
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .latex-block {
    background-color: #2d2d2d;
    border-color: #444;
  }
  
  .latex-content {
    color: #e0e0e0;
  }
  
  .latex-error {
    background-color: #3e2723;
    border-color: #f44336;
  }
  
  .error-code {
    background-color: #424242;
    border-color: #666;
    color: #ccc;
  }
}
</style> 