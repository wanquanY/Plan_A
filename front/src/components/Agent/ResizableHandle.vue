<template>
  <div 
    class="resizable-handle"
    @mousedown="startResize"
    @touchstart="startResize"
  >
    <div class="handle-line"></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits(['resize']);

const isResizing = ref(false);
const startX = ref(0);
const startWidth = ref(0);

const startResize = (event: MouseEvent | TouchEvent) => {
  event.preventDefault();
  isResizing.value = true;
  
  const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0].clientX;
  startX.value = clientX;
  
  // 获取当前侧边栏宽度
  const sidebar = document.querySelector('.sidebar-wrapper') as HTMLElement;
  if (sidebar) {
    startWidth.value = sidebar.offsetWidth;
  }
  
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
  document.addEventListener('touchmove', handleResize);
  document.addEventListener('touchend', stopResize);
  
  // 添加全局样式防止选择文本
  document.body.style.userSelect = 'none';
  document.body.style.cursor = 'col-resize';
};

const handleResize = (event: MouseEvent | TouchEvent) => {
  if (!isResizing.value) return;
  
  const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0].clientX;
  const deltaX = startX.value - clientX; // 注意：向左拖动是正值
  const newWidth = startWidth.value + deltaX;
  
  // 限制最小和最大宽度
  const minWidth = 300;
  const maxWidth = 600;
  const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
  
  emit('resize', constrainedWidth);
};

const stopResize = () => {
  isResizing.value = false;
  
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
  document.removeEventListener('touchmove', handleResize);
  document.removeEventListener('touchend', stopResize);
  
  // 恢复全局样式
  document.body.style.userSelect = '';
  document.body.style.cursor = '';
};
</script>

<style scoped>
.resizable-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: background-color 0.2s ease;
}

.resizable-handle:hover {
  background-color: rgba(59, 130, 246, 0.1);
}

.handle-line {
  width: 2px;
  height: 40px;
  background-color: #d1d5db;
  border-radius: 1px;
  transition: all 0.2s ease;
  opacity: 0;
}

.resizable-handle:hover .handle-line {
  opacity: 1;
  background-color: #3b82f6;
}

.resizable-handle:active .handle-line {
  background-color: #2563eb;
  height: 60px;
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .resizable-handle {
    width: 12px;
  }
  
  .handle-line {
    opacity: 0.3;
    width: 3px;
  }
  
  .resizable-handle:active .handle-line {
    opacity: 1;
  }
}
</style> 