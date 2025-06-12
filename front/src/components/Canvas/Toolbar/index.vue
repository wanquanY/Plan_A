<template>
  <div class="canvas-toolbar">
    <div class="toolbar-section">
      <!-- 基本工具 -->
      <div class="tool-group">
        <a-button-group>
          <a-button 
            :type="currentTool === 'select' ? 'primary' : 'default'"
            @click="setTool('select')"
            title="选择工具"
          >
            <template #icon><SelectOutlined /></template>
          </a-button>
          <a-button 
            :type="currentTool === 'hand' ? 'primary' : 'default'"
            @click="setTool('hand')"
            title="拖拽工具"
          >
            <template #icon><DragOutlined /></template>
          </a-button>
        </a-button-group>
      </div>

      <!-- 形状工具 -->
      <div class="tool-group">
        <ShapeTools />
      </div>

      <!-- 绘制工具 -->
      <div class="tool-group">
        <DrawingTools />
      </div>

      <!-- 文本工具 -->
      <div class="tool-group">
        <a-button 
          :type="currentTool === 'text' ? 'primary' : 'default'"
          @click="setTool('text')"
          title="文本工具"
        >
          <template #icon><FontSizeOutlined /></template>
          文本
        </a-button>
      </div>
    </div>

    <div class="toolbar-section">
      <!-- 缩放控制 -->
      <div class="tool-group">
        <a-button @click="zoomOut" title="缩小">
          <template #icon><ZoomOutOutlined /></template>
        </a-button>
        <span class="zoom-display">{{ Math.round(viewport.zoom * 100) }}%</span>
        <a-button @click="zoomIn" title="放大">
          <template #icon><ZoomInOutlined /></template>
        </a-button>
        <a-button @click="resetZoom" title="重置缩放">
          <template #icon><AimOutlined /></template>
        </a-button>
      </div>
    </div>

    <div class="toolbar-section">
      <!-- 操作按钮 -->
      <div class="tool-group">
        <a-button @click="undo" :disabled="!canUndo" title="撤销">
          <template #icon><UndoOutlined /></template>
        </a-button>
        <a-button @click="redo" :disabled="!canRedo" title="重做">
          <template #icon><RedoOutlined /></template>
        </a-button>
      </div>

      <!-- 导出和保存 -->
      <div class="tool-group">
        <a-button @click="saveCanvas" type="primary">
          <template #icon><SaveOutlined /></template>
          保存
        </a-button>
        <a-dropdown>
          <a-button>
            <template #icon><ExportOutlined /></template>
            导出 <DownOutlined />
          </a-button>
          <template #overlay>
            <a-menu @click="handleExport">
              <a-menu-item key="png">导出为 PNG</a-menu-item>
              <a-menu-item key="svg">导出为 SVG</a-menu-item>
              <a-menu-item key="pdf">导出为 PDF</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <!-- 样式面板 -->
    <StylePanel v-if="hasSelection" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { 
  Button as AButton, 
  ButtonGroup as AButtonGroup,
  Dropdown as ADropdown,
  Menu as AMenu,
  MenuItem as AMenuItem
} from 'ant-design-vue'
import {
  SelectOutlined,
  DragOutlined,
  FontSizeOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  AimOutlined,
  UndoOutlined,
  RedoOutlined,
  SaveOutlined,
  ExportOutlined,
  DownOutlined
} from '@ant-design/icons-vue'
import { useCanvasStore } from '../stores/canvasStore'
import ShapeTools from './ShapeTools.vue'
import DrawingTools from './DrawingTools.vue'
import StylePanel from './StylePanel.vue'

const canvasStore = useCanvasStore()
const { currentTool, viewport, hasSelection, canUndo, canRedo } = canvasStore

const setTool = (tool: string) => {
  canvasStore.setCurrentTool(tool)
}

const zoomIn = () => {
  canvasStore.zoomIn()
}

const zoomOut = () => {
  canvasStore.zoomOut()
}

const resetZoom = () => {
  canvasStore.resetZoom()
}

const undo = () => {
  canvasStore.undo()
}

const redo = () => {
  canvasStore.redo()
}

const saveCanvas = () => {
  canvasStore.saveCanvas()
}

const handleExport = ({ key }: { key: string }) => {
  canvasStore.exportCanvas(key)
}
</script>

<style scoped>
.canvas-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  height: 56px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-display {
  margin: 0 8px;
  font-size: 12px;
  color: #666;
  min-width: 40px;
  text-align: center;
}
</style> 