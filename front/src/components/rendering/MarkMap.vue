<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';
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
      // 直接渲染思维导图，不检查全局状态
      console.log('直接渲染思维导图，不检查全局状态');
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
    // 等待DOM更新
    await nextTick();
    
    // 验证SVG容器尺寸
    const svgElement = svgRef.value;
    const containerRect = svgElement.getBoundingClientRect();
    
    console.log('SVG容器尺寸检查:', {
      width: containerRect.width,
      height: containerRect.height,
      clientWidth: svgElement.clientWidth,
      clientHeight: svgElement.clientHeight
    });
    
    // 如果尺寸无效，等待一段时间再重试
    if (containerRect.width <= 0 || containerRect.height <= 0) {
      console.warn('SVG容器尺寸无效，等待DOM完全渲染...');
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const retryRect = svgElement.getBoundingClientRect();
      if (retryRect.width <= 0 || retryRect.height <= 0) {
        console.error('SVG容器尺寸仍然无效:', retryRect);
        throw new Error(`SVG容器尺寸无效: ${retryRect.width}x${retryRect.height}`);
      }
    }
    
    // 转换markdown为思维导图数据
    const { root, features } = transformer.transform(props.content);
    transformedData.value = { root, features };
    
    if (!root) {
      throw new Error('无法解析思维导图内容');
    }
    
    // 清空现有的SVG内容
    svgRef.value.innerHTML = '';
    
    // 创建新的markmap实例 - 优化配置提高性能
    const mm = Markmap.create(svgRef.value, {
      fontSize: 16,
      nodeFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
      linkShape: 'diagonal',
      color: d => d.children ? '#1677ff' : '#333',
      duration: 200, // 减少动画时间
      maxWidth: 500, // 节点最大宽度
      ...props.options
    }, transformedData.value.root);
    
    // 保存实例引用
    markmap.value = mm;
    
    if (!mm) {
      throw new Error('创建markmap实例失败');
    }
    
    console.log('Markmap实例创建成功');
    
    // 检查SVG状态后再尝试适配 - 添加更严格的验证
    if (mm && typeof mm.fit === 'function') {
      try {
        const svgRect = svgRef.value.getBoundingClientRect();
        
        // 验证尺寸是否为有效数字
        if (svgRect.width > 0 && svgRect.height > 0 && 
            !isNaN(svgRect.width) && !isNaN(svgRect.height) &&
            isFinite(svgRect.width) && isFinite(svgRect.height)) {
          
          console.log('执行首次fit，SVG尺寸:', svgRect);
          mm.fit();
          console.log('首次fit执行成功');
        } else {
          console.warn('SVG尺寸包含无效值，跳过首次fit:', svgRect);
        }
      } catch (fitError) {
        console.warn('首次适配失败，将在延迟后重试:', fitError);
        // 不抛出错误，继续执行
      }
    }
    
    // 短延迟后再次适配并设置完成状态
    setTimeout(() => {
      try {
        // 再次检查SVG状态并适配视图
        if (mm && typeof mm.fit === 'function' && svgRef.value) {
          const svgRect = svgRef.value.getBoundingClientRect();
          
          // 更严格的验证
          if (svgRect.width > 0 && svgRect.height > 0 && 
              !isNaN(svgRect.width) && !isNaN(svgRect.height) &&
              isFinite(svgRect.width) && isFinite(svgRect.height)) {
            
            console.log('执行延迟fit，SVG尺寸:', svgRect);
            mm.fit();
            console.log('延迟fit执行成功');
          } else {
            console.warn('延迟fit时SVG尺寸包含无效值:', svgRect);
          }
        }
        isLoading.value = false;
        console.log('思维导图渲染完成');
      } catch (e) {
        console.error('思维导图适配失败:', e);
        isLoading.value = false;
        // 即使fit失败，也不设置错误状态，因为图表可能已经渲染成功
      }
    }, 300); // 增加延迟时间，确保DOM完全渲染
    
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
  if (markmap.value && svgRef.value) {
    try {
      const svgRect = svgRef.value.getBoundingClientRect();
      
      // 验证尺寸是否为有效数字
      if (svgRect.width > 0 && svgRect.height > 0 && 
          !isNaN(svgRect.width) && !isNaN(svgRect.height) &&
          isFinite(svgRect.width) && isFinite(svgRect.height)) {
        
        console.log('手动fit，SVG尺寸:', svgRect);
        markmap.value.fit();
        console.log('手动fit执行成功');
      } else {
        console.warn('手动fit时SVG尺寸包含无效值:', svgRect);
      }
    } catch (error) {
      console.error('手动适配思维导图失败:', error);
    }
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