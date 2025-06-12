<template>
  <div 
    v-if="visible" 
    class="canvas-fullscreen-modal"
    @click="handleBackdropClick"
  >
    <div class="canvas-fullscreen-backdrop"></div>
    <div 
      class="canvas-fullscreen-container"
      @click.stop
    >
      <div class="canvas-fullscreen-header">
        <div class="canvas-fullscreen-title">
          <span>画板编辑</span>
          <small style="color: #666; margin-left: 8px;">ID: {{ canvasId }}</small>
        </div>
        <div class="canvas-fullscreen-actions">
          <button @click="saveCanvas" class="canvas-action-btn canvas-save-btn">保存</button>
          <button @click="closeModal" class="canvas-action-btn canvas-close-btn">关闭</button>
        </div>
      </div>
      
      <div class="canvas-fullscreen-toolbar">
        <div class="canvas-tool-group">
          <button 
            v-for="tool in tools" 
            :key="tool.id"
            class="canvas-tool-btn" 
            :class="{ active: currentTool === tool.id }"
            :data-tool="tool.id"
            @click="setTool(tool.id)"
            v-html="tool.icon"
          ></button>
        </div>
        
        <div class="canvas-tool-divider"></div>
        
        <div class="canvas-color-group">
          <div class="canvas-color-picker" @click="showColorPicker = !showColorPicker">
            <div class="canvas-current-color" :style="{ background: currentColor }"></div>
          </div>
          <div class="canvas-stroke-width">
            <input 
              type="range" 
              min="1" 
              max="5" 
              v-model="strokeWidth"
              class="canvas-stroke-slider"
            >
          </div>
        </div>
      </div>
      
      <div class="canvas-fullscreen-content">
        <div class="canvas-fullscreen-workspace">
          <div class="canvas-drawing-area" ref="drawingArea" :id="`canvas-drawing-${canvasId}`">
            <div class="canvas-grid-bg"></div>
            <canvas 
              ref="canvas"
              :width="canvasWidth"
              :height="canvasHeight"
              @mousedown="handleMouseDown"
              @mousemove="handleMouseMove"
              @mouseup="handleMouseUp"
            ></canvas>
            <div v-if="!hasDrawn" class="canvas-welcome-hint">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style="margin-bottom: 16px;">
                <rect x="8" y="8" width="32" height="32" rx="4" stroke="currentColor" stroke-width="2" fill="none"/>
                <circle cx="16" cy="16" r="2" fill="currentColor"/>
                <path d="M14 24L20 18L26 24L32 18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <h3 style="margin: 0 0 8px 0; font-size: 16px;">开始绘制</h3>
              <p style="margin: 0; font-size: 14px; color: #666;">选择工具并在画布上绘制</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  canvasId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'save']);

// 工具定义
const tools = [
  { 
    id: 'select', 
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M1 1L6 6L4.5 7.5L1 4V1Z" fill="currentColor"/>
      <path d="M6 6L15 1L10 10L6 6Z" fill="currentColor"/>
    </svg>` 
  },
  { 
    id: 'rectangle', 
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="3" width="12" height="10" stroke="currentColor" stroke-width="1.5" fill="none"/>
    </svg>` 
  },
  { 
    id: 'circle', 
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/>
    </svg>` 
  },
  { 
    id: 'line', 
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M2 14L14 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>` 
  },
  { 
    id: 'text', 
    icon: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M4 3V4H6V13H7V4H9V3H4Z" fill="currentColor"/>
    </svg>` 
  }
];

// 状态
const canvas = ref<HTMLCanvasElement | null>(null);
const drawingArea = ref<HTMLElement | null>(null);
const currentTool = ref('select');
const currentColor = ref('#000000');
const strokeWidth = ref(2);
const showColorPicker = ref(false);
const hasDrawn = ref(false);
const isDrawing = ref(false);

// 画布尺寸
const canvasWidth = computed(() => drawingArea.value?.offsetWidth || 800);
const canvasHeight = computed(() => drawingArea.value?.offsetHeight || 600);

// 绘图状态
const drawingState = ref({
  startX: 0,
  startY: 0,
  currentPath: [] as Array<{x: number, y: number}>
});

// 设置工具
const setTool = (tool: string) => {
  currentTool.value = tool;
  console.log('选择工具:', tool);
};

// 处理鼠标事件
const handleMouseDown = (e: MouseEvent) => {
  if (!canvas.value || currentTool.value === 'select') return;
  
  const rect = canvas.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  
  isDrawing.value = true;
  hasDrawn.value = true;
  drawingState.value.startX = x;
  drawingState.value.startY = y;
  
  const ctx = canvas.value.getContext('2d')!;
  ctx.strokeStyle = currentColor.value;
  ctx.lineWidth = strokeWidth.value;
  ctx.lineCap = 'round';
  
  if (currentTool.value === 'line') {
    ctx.beginPath();
    ctx.moveTo(x, y);
    drawingState.value.currentPath = [{x, y}];
  }
};

const handleMouseMove = (e: MouseEvent) => {
  if (!canvas.value || !isDrawing.value || currentTool.value === 'select') return;
  
  const rect = canvas.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  
  const ctx = canvas.value.getContext('2d')!;
  
  if (currentTool.value === 'line') {
    drawingState.value.currentPath.push({x, y});
    ctx.lineTo(x, y);
    ctx.stroke();
  }
};

const handleMouseUp = (e: MouseEvent) => {
  if (!canvas.value || !isDrawing.value || currentTool.value === 'select') return;
  
  const rect = canvas.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  
  const ctx = canvas.value.getContext('2d')!;
  
  switch (currentTool.value) {
    case 'rectangle':
      drawRectangle(
        drawingState.value.startX, 
        drawingState.value.startY, 
        x - drawingState.value.startX, 
        y - drawingState.value.startY
      );
      break;
    case 'circle':
      drawCircle(
        drawingState.value.startX, 
        drawingState.value.startY, 
        Math.sqrt(Math.pow(x - drawingState.value.startX, 2) + Math.pow(y - drawingState.value.startY, 2))
      );
      break;
  }
  
  isDrawing.value = false;
  drawingState.value.currentPath = [];
};

const drawRectangle = (x: number, y: number, width: number, height: number) => {
  if (!canvas.value) return;
  const ctx = canvas.value.getContext('2d')!;
  ctx.strokeRect(x, y, width, height);
};

const drawCircle = (centerX: number, centerY: number, radius: number) => {
  if (!canvas.value) return;
  const ctx = canvas.value.getContext('2d')!;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
  ctx.stroke();
};

// 事件处理
const handleBackdropClick = () => {
  closeModal();
};

const closeModal = () => {
  document.body.style.overflow = '';
  emit('close');
};

const saveCanvas = () => {
  console.log('保存画板:', props.canvasId);
  // TODO: 实现保存逻辑
  emit('save', props.canvasId);
};

// 键盘事件处理
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    closeModal();
  }
};

onMounted(() => {
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', handleKeyDown);
  
  nextTick(() => {
    if (canvas.value && drawingArea.value) {
      canvas.value.width = drawingArea.value.offsetWidth;
      canvas.value.height = drawingArea.value.offsetHeight;
    }
  });
});

onUnmounted(() => {
  document.body.style.overflow = '';
  document.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped>
/* 样式已经在global.css中定义 */
canvas {
  display: block;
  cursor: crosshair;
}

.canvas-drawing-area {
  position: relative;
}

.canvas-drawing-area canvas {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}
</style> 