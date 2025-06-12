<template>
  <div class="canvas-container">
    <!-- 画布工具栏 -->
    <div class="canvas-toolbar">
      <div class="toolbar-left">
        <!-- 选择工具 -->
        <button 
          class="tool-btn"
          :class="{ active: activeTool === 'select' }"
          @click="setTool('select')"
          title="选择工具 (V)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 1l4.5 11L8 8l3.5-1.5L1 1z"/>
          </svg>
        </button>
        
        <!-- 手型工具 -->
        <button 
          class="tool-btn"
          :class="{ active: activeTool === 'pan' }"
          @click="setTool('pan')"
          title="平移工具 (H)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.75 5.75C3.75 3.68 5.43 2 7.5 2s3.75 1.68 3.75 3.75V6c0 0.41.34.75.75.75s.75-.34.75-.75v-.25C12.75 2.68 10.57.5 7.5.5S2.25 2.68 2.25 5.75V11c0 1.24 1.01 2.25 2.25 2.25h6c1.24 0 2.25-1.01 2.25-2.25V8.5c0-.41-.34-.75-.75-.75s-.75.34-.75.75V11c0 .41-.34.75-.75.75h-6c-.41 0-.75-.34-.75-.75V5.75z"/>
          </svg>
        </button>
        
        <!-- 文字工具 -->
        <button 
          class="tool-btn"
          :class="{ active: activeTool === 'text' }"
          @click="setTool('text')"
          title="文本工具 (T)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.75 2a.75.75 0 0 1 .75-.75h7a.75.75 0 0 1 0 1.5H8.75v10.5a.75.75 0 0 1-1.5 0V2.75H4.5a.75.75 0 0 1-.75-.75z"/>
          </svg>
        </button>
        
        <!-- 连线工具 -->
        <button 
          class="tool-btn"
          :class="{ active: activeTool === 'connector' }"
          @click="setTool('connector')"
          title="连接工具 (C)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 8a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 8zM7.646 3.146a.5.5 0 0 1 .708 0l4 4a.5.5 0 0 1-.708.708L8 4.207 4.354 7.854a.5.5 0 1 1-.708-.708l4-4z"/>
          </svg>
        </button>
        
        <!-- 测试按钮 -->
        <button 
          class="tool-btn test-btn"
          @click="createTestElement"
          title="创建测试矩形"
          style="background-color: #f0f8ff; border: 1px solid #87CEEB;"
        >
          <span style="font-size: 12px;">测试</span>
        </button>
      </div>
      
      <div class="toolbar-right">
        <!-- 缩放控制 -->
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomOut" title="缩小">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M2 7h10"/>
            </svg>
          </button>
          <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
          <button class="zoom-btn" @click="zoomIn" title="放大">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M2 7h10M7 2v10"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- 画布主体 - 使用CanvasCore组件 -->
    <div class="canvas-stage" ref="stageContainer">
      <CanvasCore 
        :canvas-id="canvasId"
        :width="800"
        :height="600"
        @canvas-updated="handleCanvasUpdated"
      />
    </div>
    
    <!-- 浮动工具栏 -->
    <FloatingToolbar />
    

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useCanvasStore } from '../../stores/canvasStore'
import { useConnectionStore } from '../../stores/connectionStore'
import { ElementType } from '../../types/canvas'
import CanvasCore from '../../CanvasCore.vue'
import FloatingToolbar from '../../Toolbar/FloatingToolbar.vue'

// Props
const props = defineProps<{
  canvasId: string
  activeTool: string
  selectedElements: any[]
}>()

// Emits
const emit = defineEmits<{
  elementSelect: [elements: any[]]
  elementDeselect: []
  canvasChange: [changes: any]
}>()

// Store
const canvasStore = useCanvasStore()
const connectionStore = useConnectionStore()

// 状态
const stageContainer = ref<HTMLDivElement>()
const zoom = ref(1)


// 计算属性
const selectedElements = computed(() => canvasStore.selectedElements)

// 监听选中元素变化
watch(selectedElements, (newElements) => {
  console.log('[CanvasContainer] 选中元素变化:', newElements)
}, { immediate: true })




// 方法
const setTool = (tool: string) => {
  emit('canvasChange', { type: 'tool-change', tool })
}

const zoomIn = () => {
  const newZoom = Math.min(zoom.value * 1.2, 5)
  setZoom(newZoom)
}

const zoomOut = () => {
  const newZoom = Math.max(zoom.value / 1.2, 0.1)
  setZoom(newZoom)
}

const setZoom = (newZoom: number) => {
  zoom.value = newZoom
  canvasStore.setZoom(newZoom)
  emit('canvasChange', { type: 'zoom-change', zoom: newZoom })
}

const clearSelection = () => {
  canvasStore.clearSelection()
  emit('elementDeselect')
}

// 测试功能：创建一个矩形并选中它
const createTestElement = () => {
  console.log('[CanvasContainer] 创建测试元素')
  const elementId = canvasStore.addElement({
    type: ElementType.RECTANGLE,
    x: 100,
    y: 100,
    width: 150,
    height: 100,
    rotation: 0,
    zIndex: 0,
    locked: false,
    visible: true,
    style: {
      fill: '#87CEEB',
      stroke: '#4682B4',
      strokeWidth: 2,
      opacity: 1
    },
    data: {}
  })
  
  // 选中这个元素
  setTimeout(() => {
    console.log('[CanvasContainer] 选中测试元素:', elementId)
    canvasStore.selectElement(elementId)
  }, 100)
}



const duplicateElement = () => {
  selectedElements.value.forEach(element => {
    canvasStore.duplicateElement(element.id)
  })
}

const deleteElement = () => {
  selectedElements.value.forEach(element => {
    canvasStore.removeElement(element.id)
    // 同时清理相关连接
    connectionStore.removeConnectionsForElement(element.id)
  })
  clearSelection()
}

const bringToFront = () => {
  selectedElements.value.forEach(element => {
    canvasStore.bringToFront(element.id)
  })
}

const sendToBack = () => {
  selectedElements.value.forEach(element => {
    canvasStore.sendToBack(element.id)
  })
}

const handleCanvasUpdated = (data: any) => {
  emit('canvasChange', data)
}

// 添加形状到画布
const addShape = (shapeData: any) => {
  canvasStore.addElement({
    type: shapeData.type,
    x: 100,
    y: 100,
    width: 100,
    height: 60,
    rotation: 0,
    zIndex: 0,
    locked: false,
    visible: true,
    style: {
      fill: 'rgba(135, 206, 235, 0.8)',
      stroke: '#87CEEB',
      strokeWidth: 2
    },
    data: {}
  })
}

const toggleGrid = () => {
  canvasStore.config.grid.enabled = !canvasStore.config.grid.enabled
}

// 窗口变化时的处理（浮动工具栏现在自管理位置）
const handleWindowResize = () => {
  // 浮动工具栏会自动处理位置更新
}

const handleWindowScroll = () => {
  // 浮动工具栏会自动处理位置更新
}

// 生命周期
onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
  window.addEventListener('scroll', handleWindowScroll, true)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  window.removeEventListener('scroll', handleWindowScroll, true)
})

// 暴露方法给父组件
defineExpose({
  setZoom,
  zoomIn,
  zoomOut,
  zoomReset: () => setZoom(1),
  addShape,
  toggleGrid,
  getCanvasData: () => canvasStore.exportCanvasData(),
  clearCanvas: () => canvasStore.clearCanvas()
})
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #ffffff;
}

.canvas-toolbar {
  height: 48px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e1e4e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 6px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tool-btn:hover {
  background-color: #e1e4e8;
  color: #24292f;
}

.tool-btn.active {
  background-color: #1890ff;
  color: #ffffff;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  padding: 4px 8px;
}

.zoom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background-color: transparent;
  color: #656d76;
  cursor: pointer;
  transition: all 0.15s ease;
}

.zoom-btn:hover {
  background-color: #f6f8fa;
  color: #24292f;
}

.zoom-level {
  font-size: 13px;
  color: #24292f;
  min-width: 40px;
  text-align: center;
}

.canvas-stage {
  flex: 1;
  position: relative;
  overflow: hidden;
  background-color: #ffffff;
}

.canvas-stage canvas {
  transition: cursor 0.1s ease;
}

.canvas-stage.connecting {
  cursor: crosshair !important;
}

.context-menu {
  position: fixed;
  background-color: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 8px 0;
  min-width: 140px;
  z-index: 1000;
}

.context-item {
  width: 100%;
  height: 32px;
  padding: 0 16px;
  border: none;
  background-color: transparent;
  color: #24292f;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.15s ease;
  font-size: 14px;
}

.context-item:hover {
  background-color: #f6f8fa;
}

.context-divider {
  height: 1px;
  background-color: #d0d7de;
  margin: 4px 0;
}




</style> 