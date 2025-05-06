<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { Markmap } from 'markmap-view';
import { Transformer } from 'markmap-lib';

// 定义组件的属性
const props = defineProps({
  // 思维导图的markdown内容
  content: {
    type: String,
    required: true
  },
  // 思维导图高度
  height: {
    type: String,
    default: '400px'
  },
  // 思维导图配置项
  options: {
    type: Object,
    default: () => ({})
  }
});

// 用于存储markmap实例
const markmap = ref(null);
// 用于存储转换后的数据
const transformedData = ref(null);
// SVG容器的引用
const svgRef = ref(null);
// 状态控制
const isLoading = ref(true);
const isError = ref(false);
const errorMessage = ref('');
const isCopied = ref(false);

// 初始化transformer
const transformer = new Transformer();

// 在组件挂载后初始化markmap
onMounted(() => {
  if (svgRef.value) {
    try {
      renderMarkmap();
    } catch (error) {
      console.error('初始化思维导图失败:', error);
      isError.value = true;
      errorMessage.value = error.message || '初始化思维导图失败';
    }
  }
});

// 当内容变化时重新渲染
watch(() => props.content, () => {
  renderMarkmap();
});

// 渲染思维导图
const renderMarkmap = async () => {
  if (!svgRef.value) return;
  
  isLoading.value = true;
  isError.value = false;
  
  try {
    // 转换markdown为思维导图数据
    const { root, features } = transformer.transform(props.content);
    transformedData.value = { root, features };
    
    // 清空现有的SVG内容
    svgRef.value.innerHTML = '';
    
    // 创建新的markmap实例
    const mm = Markmap.create(svgRef.value, {
      fontSize: 16,
      nodeFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
      linkShape: 'diagonal',
      color: d => d.children ? '#1677ff' : '#333',
      ...props.options
    }, transformedData.value.root);
    
    markmap.value = mm;
    isLoading.value = false;
  } catch (error) {
    console.error('渲染思维导图失败:', error);
    isError.value = true;
    errorMessage.value = error.message || '渲染思维导图失败';
    isLoading.value = false;
  }
};

// 复制思维导图内容
const copyContent = () => {
  navigator.clipboard.writeText(props.content)
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

// 以合适的尺寸重新适应SVG大小
const fitMap = () => {
  if (markmap.value) {
    markmap.value.fit();
  }
};
</script>

<template>
  <div class="markmap-wrapper">
    <!-- 加载中状态 -->
    <div v-if="isLoading" class="markmap-loading">
      <div class="spinner"></div>
      <span>正在渲染思维导图...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="isError" class="markmap-error">
      <div class="error-icon">!</div>
      <div class="error-message">
        <p>渲染思维导图失败</p>
        <small>{{ errorMessage }}</small>
      </div>
    </div>
    
    <!-- 渲染成功状态 - SVG容器 -->
    <svg ref="svgRef" :style="{ height: height }" class="markmap-svg"></svg>
    
    <!-- 工具栏 - 只留一个按钮 -->
    <button class="fit-button" @click="fitMap" title="适配大小">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 3 21 3 21 9"></polyline>
        <polyline points="9 21 3 21 3 15"></polyline>
        <line x1="21" y1="3" x2="14" y2="10"></line>
        <line x1="3" y1="21" x2="10" y2="14"></line>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.markmap-wrapper {
  margin: 0.6em 0;
  position: relative;
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 5px;
  overflow: hidden;
  border: 1px solid #eaecef;
  min-height: 100px;
}

.markmap-svg {
  width: 100%;
  min-height: 400px;
  outline: none;
}

/* 移除工具栏，直接定位按钮 */
.fit-button {
  position: absolute;
  top: 5px;
  right: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: rgba(246, 248, 250, 0.8);
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease, background-color 0.2s ease;
  border: 1px solid #eaecef;
  color: #666;
  margin: 0;
  z-index: 10;
}

.markmap-wrapper:hover .fit-button {
  opacity: 1;
}

.fit-button:hover {
  background-color: #f0f0f0;
  color: #0366d6;
}

/* 加载状态样式 */
.markmap-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #666;
}

.spinner {
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top: 3px solid #3498db;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 错误状态样式 */
.markmap-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #e74c3c;
  padding: 20px;
  text-align: center;
}

.error-icon {
  font-size: 24px;
  font-weight: bold;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #fff0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
}

.error-message {
  text-align: left;
}

.error-message p {
  margin: 0 0 5px 0;
  font-weight: bold;
}

.error-message small {
  color: #777;
}
</style> 