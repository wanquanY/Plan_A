<template>
  <div class="outline-container" :class="{ 'collapsed': collapsed }">
    <div class="outline-header">
      <h3>大纲</h3>
    </div>
    <div class="outline-content">
      <div v-if="headings.length === 0" class="outline-empty">
        文档中没有标题
      </div>
      <div v-else class="outline-list">
        <div 
          v-for="heading in headings" 
          :key="heading.id" 
          class="outline-item"
          :class="[`level-${heading.level}`, { 'active': heading.id === activeHeadingId }]"
          @click="scrollToHeading(heading.id)"
        >
          {{ heading.text }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue';

const props = defineProps({
  editorRef: {
    type: Object,
    required: true
  }
});

// 状态变量
const collapsed = ref(false);
const headings = ref<Array<{ id: string; text: string; level: number; element: HTMLElement }>>([]);
const activeHeadingId = ref('');
let observer: IntersectionObserver | null = null;

// 切换折叠状态
const toggleCollapse = () => {
  collapsed.value = !collapsed.value;
};

// 从编辑器内容中提取标题
const extractHeadings = () => {
  if (!props.editorRef || !props.editorRef.editorRef) return;
  
  const editorElement = props.editorRef.editorRef;
  const headingElements = editorElement.querySelectorAll('h1, h2, h3, h4, h5, h6');
  
  const newHeadings: Array<{ id: string; text: string; level: number; element: HTMLElement }> = [];
  
  headingElements.forEach((heading, index) => {
    const headingElement = heading as HTMLElement;
    const level = parseInt(headingElement.tagName.charAt(1));
    const text = headingElement.textContent || `标题 ${index + 1}`;
    const id = `heading-${index}`;
    
    // 为每个标题设置ID，便于导航
    headingElement.id = id;
    
    newHeadings.push({
      id,
      text,
      level,
      element: headingElement
    });
  });
  
  headings.value = newHeadings;
  setupIntersectionObserver();
};

// 滚动到指定标题
const scrollToHeading = (id: string) => {
  const element = document.getElementById(id);
  if (element) {
    // 获取标题元素的位置
    const rect = element.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    // 计算需要滚动到的位置（标题位置减去工具栏高度的偏移）
    const offsetTop = rect.top + scrollTop - 80; // 减去工具栏高度和一些额外空间
    
    // 使用平滑滚动
    window.scrollTo({
      top: offsetTop,
      behavior: 'smooth'
    });
    
    // 设置活动标题
    activeHeadingId.value = id;
  }
};

// 设置标题可见性观察器，用于自动更新活动标题
const setupIntersectionObserver = () => {
  // 如果已有观察器则先移除
  if (observer) {
    observer.disconnect();
  }
  
  // 创建新的观察器
  observer = new IntersectionObserver(
    (entries) => {
      // 找到当前可见的标题
      const visibleHeadings = entries
        .filter(entry => entry.isIntersecting)
        .map(entry => entry.target.id);
      
      if (visibleHeadings.length > 0) {
        // 更新活动标题为第一个可见的标题
        activeHeadingId.value = visibleHeadings[0];
      }
    },
    {
      root: null, // 使用viewport作为root，适应全局滚动
      rootMargin: '0px',
      threshold: 0.5
    }
  );
  
  // 观察所有标题元素
  headings.value.forEach(heading => {
    const element = document.getElementById(heading.id);
    if (element) {
      observer.observe(element);
    }
  });
};

// 监听编辑器内容变化
const setupContentChangeListener = () => {
  if (!props.editorRef || !props.editorRef.editorRef) return;
  
  const editorElement = props.editorRef.editorRef;
  
  // 使用MutationObserver监听DOM变化
  const mutationObserver = new MutationObserver(() => {
    // 内容变化时更新大纲
    extractHeadings();
  });
  
  mutationObserver.observe(editorElement, {
    childList: true,
    subtree: true,
    characterData: true
  });
  
  // 组件卸载时清理
  return () => {
    mutationObserver.disconnect();
    if (observer) {
      observer.disconnect();
    }
  };
};

// 组件挂载后初始化
onMounted(() => {
  nextTick(() => {
    extractHeadings();
    const cleanup = setupContentChangeListener();
    
    // 组件卸载时清理
    return cleanup;
  });
});

// 当编辑器引用更新时重新提取标题
watch(() => props.editorRef, () => {
  nextTick(() => {
    extractHeadings();
  });
}, { deep: true });

// 暴露方法给父组件
defineExpose({
  toggleCollapse
});
</script>

<style>
.outline-container {
  width: 250px;
  background: #f5f7fa;
  border-right: 1px solid #e0e0e0;
  height: calc(100vh - 60px); /* 减去工具栏高度 */
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  position: sticky;
  top: 60px; /* 与工具栏底部对齐 */
  z-index: 90;
  align-self: flex-start;
  flex-shrink: 0;
}

.outline-container.collapsed {
  width: 0;
  border-right: none;
  overflow: hidden;
}

.outline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid #e0e0e0;
  background: #ffffff;
  position: sticky;
  top: 0;
  z-index: 1;
}

.outline-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.outline-toggle-btn {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
}

.outline-toggle-btn:hover {
  background: #f0f0f0;
}

.outline-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
  max-height: calc(100vh - 110px); /* 减去工具栏和大纲标题高度 */
}

.outline-empty {
  padding: 15px;
  color: #999;
  text-align: center;
  font-size: 14px;
}

.outline-list {
  display: flex;
  flex-direction: column;
}

.outline-item {
  padding: 6px 15px;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.outline-item:hover {
  background: #e8f0fe;
}

.outline-item.active {
  background: #e8f0fe;
  border-left-color: #1890ff;
  color: #1890ff;
}

.outline-item.level-1 {
  padding-left: 15px;
  font-weight: 500;
}

.outline-item.level-2 {
  padding-left: 30px;
}

.outline-item.level-3 {
  padding-left: 45px;
}

.outline-item.level-4 {
  padding-left: 60px;
}

.outline-item.level-5 {
  padding-left: 75px;
}

.outline-item.level-6 {
  padding-left: 90px;
}

/* 折叠状态样式 */
.outline-container.collapsed .outline-header,
.outline-container.collapsed .outline-content {
  display: none;
}

.outline-container.collapsed .outline-toggle-btn {
  margin: 0 auto;
  transform: rotate(180deg);
}
</style> 