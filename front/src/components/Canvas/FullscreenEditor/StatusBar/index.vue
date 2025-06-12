<template>
  <div class="status-bar">
    <!-- 左侧状态信息 -->
    <div class="status-left">
      <!-- 光标位置 -->
      <div class="status-item">
        <span class="status-label">坐标:</span>
        <span class="status-value">{{ cursorPosition.x }}, {{ cursorPosition.y }}</span>
      </div>
      
      <!-- 选中元素数量 -->
      <div class="status-item" v-if="selectedCount > 0">
        <span class="status-label">已选择:</span>
        <span class="status-value">{{ selectedCount }} 个元素</span>
      </div>
      
      <!-- 画布尺寸 -->
      <div class="status-item">
        <span class="status-label">画布:</span>
        <span class="status-value">{{ canvasSize.width }} × {{ canvasSize.height }}</span>
      </div>
    </div>
    
    <!-- 中央快捷操作 -->
    <div class="status-center">
      <!-- 网格切换 -->
      <button 
        class="status-btn"
        :class="{ active: showGrid }"
        @click="toggleGrid"
        title="切换网格显示"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <path d="M1 3h12v1H1V3zm0 3h12v1H1V6zm0 3h12v1H1V9zm0 3h12v1H1v-1z"/>
          <path d="M3 1v12h1V1H3zm3 0v12h1V1H7zm3 0v12h1V1h-1zm3 0v12h1V1h-1z"/>
        </svg>
        <span>网格</span>
      </button>
      
      <!-- 对齐辅助线 -->
      <button 
        class="status-btn"
        :class="{ active: showSnapGuides }"
        @click="toggleSnapGuides"
        title="切换对齐辅助线"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1" fill="none"/>
          <circle cx="7" cy="7" r="2" fill="currentColor"/>
        </svg>
        <span>对齐</span>
      </button>
      
      <!-- 标尺 -->
      <button 
        class="status-btn"
        :class="{ active: showRulers }"
        @click="toggleRulers"
        title="切换标尺显示"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <path d="M1 1h12v2H1V1zm0 4h12v1H1V5zm0 3h12v1H1V8zm0 3h12v2H1v-2z"/>
          <path d="M2 3v1m2-1v1m2-1v1m2-1v1m2-1v1m2-1v1"/>
        </svg>
        <span>标尺</span>
      </button>
    </div>
    
    <!-- 右侧缩放控制 -->
    <div class="status-right">
      <!-- 缩放预设 -->
      <div class="zoom-presets">
        <button 
          v-for="preset in zoomPresets"
          :key="preset.value"
          class="zoom-preset"
          :class="{ active: isZoomActive(preset.value) }"
          @click="setZoom(preset.value)"
        >
          {{ preset.label }}
        </button>
      </div>
      
      <!-- 缩放滑块 -->
      <div class="zoom-slider-container">
        <button class="zoom-btn" @click="zoomOut" title="缩小">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M2 6h8"/>
          </svg>
        </button>
        
        <div class="zoom-slider">
          <input 
            type="range" 
            :value="zoomLevel" 
            min="10" 
            max="500" 
            step="10"
            @input="handleZoomSlider"
            class="slider"
          />
        </div>
        
        <button class="zoom-btn" @click="zoomIn" title="放大">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M6 2v8M2 6h8"/>
          </svg>
        </button>
      </div>
      
      <!-- 缩放百分比 -->
      <div class="zoom-percentage">
        <span>{{ zoomLevel }}%</span>
      </div>
      
      <!-- 适合窗口 -->
      <button class="status-btn" @click="fitToWindow" title="适合窗口">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
          <path d="M1 1h4v1H2v3H1V1zm8 0h4v4h-1V2h-3V1zM1 9v4h4v-1H2V9H1zm12 0v3h-3v1h4V9h-1z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Props
const props = defineProps<{
  zoomLevel: number
  cursorPosition: { x: number; y: number }
  selectedCount: number
}>()

// Emits
const emit = defineEmits<{
  zoomChange: [zoom: number]
}>()

// 状态
const showGrid = ref(true)
const showSnapGuides = ref(true)
const showRulers = ref(false)

// 画布尺寸（模拟数据）
const canvasSize = ref({
  width: 1920,
  height: 1080
})

// 缩放预设值
const zoomPresets = [
  { label: '25%', value: 25 },
  { label: '50%', value: 50 },
  { label: '100%', value: 100 },
  { label: '150%', value: 150 },
  { label: '200%', value: 200 }
]

// 计算属性
const isZoomActive = (value: number) => {
  return Math.abs(props.zoomLevel - value) < 5
}

// 方法
const toggleGrid = () => {
  showGrid.value = !showGrid.value
  console.log('切换网格显示:', showGrid.value)
  // TODO: 实际切换网格显示逻辑
}

const toggleSnapGuides = () => {
  showSnapGuides.value = !showSnapGuides.value
  console.log('切换对齐辅助线:', showSnapGuides.value)
  // TODO: 实际切换对齐辅助线逻辑
}

const toggleRulers = () => {
  showRulers.value = !showRulers.value
  console.log('切换标尺显示:', showRulers.value)
  // TODO: 实际切换标尺显示逻辑
}

const setZoom = (zoom: number) => {
  emit('zoomChange', zoom)
}

const zoomIn = () => {
  const newZoom = Math.min(props.zoomLevel + 25, 500)
  emit('zoomChange', newZoom)
}

const zoomOut = () => {
  const newZoom = Math.max(props.zoomLevel - 25, 10)
  emit('zoomChange', newZoom)
}

const handleZoomSlider = (event: Event) => {
  const target = event.target as HTMLInputElement
  const zoom = parseInt(target.value)
  emit('zoomChange', zoom)
}

const fitToWindow = () => {
  console.log('适合窗口')
  // TODO: 计算适合窗口的缩放比例
  emit('zoomChange', 100)
}
</script>

<style scoped>
.status-bar {
  height: 32px;
  background-color: #f8f9fa;
  border-top: 1px solid #e1e4e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 12px;
  color: #656d76;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-label {
  color: #656d76;
}

.status-value {
  color: #24292f;
  font-weight: 500;
}

.status-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 6px;
  border: none;
  border-radius: 4px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 11px;
}

.status-btn:hover {
  background-color: #e1e4e8;
  color: #24292f;
}

.status-btn.active {
  background-color: #1890ff;
  color: #ffffff;
}

.zoom-presets {
  display: flex;
  align-items: center;
  gap: 2px;
}

.zoom-preset {
  height: 24px;
  padding: 0 6px;
  border: none;
  border-radius: 3px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 11px;
}

.zoom-preset:hover {
  background-color: #e1e4e8;
  color: #24292f;
}

.zoom-preset.active {
  background-color: #1890ff;
  color: #ffffff;
}

.zoom-slider-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 3px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.zoom-btn:hover {
  background-color: #e1e4e8;
  color: #24292f;
}

.zoom-slider {
  width: 80px;
}

.slider {
  width: 100%;
  height: 3px;
  background: #e1e4e8;
  outline: none;
  border-radius: 2px;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  appearance: none;
  width: 12px;
  height: 12px;
  background: #1890ff;
  border-radius: 50%;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: #1890ff;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.zoom-percentage {
  min-width: 35px;
  text-align: center;
  color: #24292f;
  font-weight: 500;
}
</style> 