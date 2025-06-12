<template>
  <div class="canvas-container">
    <!-- 工具栏 -->
    <div class="canvas-toolbar">
      <CanvasToolbar />
    </div>

    <!-- 主要内容区域 -->
    <div class="canvas-main">
      <!-- 左侧面板 -->
      <div class="canvas-sidebar-left" v-if="showLeftPanel">
        <a-tabs v-model:activeKey="leftActiveTab" size="small">
          <a-tab-pane key="templates" tab="模板">
            <TemplatePanel />
          </a-tab-pane>
          <a-tab-pane key="layers" tab="图层">
            <LayerPanel />
          </a-tab-pane>
        </a-tabs>
      </div>

      <!-- 画布区域 -->
      <div class="canvas-workspace">
        <CanvasCore />
      </div>

      <!-- 右侧面板 -->
      <div class="canvas-sidebar-right" v-if="showRightPanel">
        <PropertiesPanel />
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="canvas-statusbar">
      <div class="statusbar-left">
        <span>{{ elements.length }} 个元素</span>
        <span v-if="hasSelection">{{ selectedElements.length }} 个已选中</span>
      </div>
      <div class="statusbar-center">
        <span>{{ Math.round(viewport.zoom * 100) }}%</span>
      </div>
      <div class="statusbar-right">
        <a-button size="small" @click="toggleGrid">
          <template #icon>
            <BorderOutlined />
          </template>
          {{ config.grid.enabled ? '隐藏网格' : '显示网格' }}
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Tabs as ATabs, TabPane as ATabPane, Button as AButton } from 'ant-design-vue'
import { BorderOutlined } from '@ant-design/icons-vue'
import { useCanvasStore } from './stores/canvasStore'
import CanvasToolbar from './Toolbar/index.vue'
import CanvasCore from './CanvasCore.vue'
import TemplatePanel from './Panels/TemplatePanel.vue'
import LayerPanel from './Panels/LayerPanel.vue'
import PropertiesPanel from './Panels/PropertiesPanel.vue'

// 状态管理
const canvasStore = useCanvasStore()
const { canvasData, viewport, selection, config, selectedElements, hasSelection } = canvasStore

// 界面状态
const showLeftPanel = ref(true)
const showRightPanel = ref(true)
const leftActiveTab = ref('templates')

// 计算属性
const elements = computed(() => canvasData.elements)

// 方法
const toggleGrid = () => {
  config.grid.enabled = !config.grid.enabled
}

const toggleLeftPanel = () => {
  showLeftPanel.value = !showLeftPanel.value
}

const toggleRightPanel = () => {
  showRightPanel.value = !showRightPanel.value
}

// 键盘快捷键
const handleKeydown = (event: KeyboardEvent) => {
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case 'a':
        event.preventDefault()
        canvasStore.selectAll()
        break
      case 'c':
        // 复制功能
        break
      case 'v':
        // 粘贴功能
        break
      case 'z':
        if (event.shiftKey) {
          // 重做
        } else {
          // 撤销
        }
        break
    }
  } else {
    switch (event.key) {
      case 'Delete':
      case 'Backspace':
        // 删除选中元素
        break
      case 'Escape':
        canvasStore.clearSelection()
        break
    }
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.canvas-toolbar {
  height: 56px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  z-index: 100;
}

.canvas-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas-sidebar-left {
  width: 280px;
  background: white;
  border-right: 1px solid #e8e8e8;
  overflow-y: auto;
}

.canvas-workspace {
  flex: 1;
  background: #f5f5f5;
  position: relative;
  overflow: hidden;
}

.canvas-sidebar-right {
  width: 280px;
  background: white;
  border-left: 1px solid #e8e8e8;
  overflow-y: auto;
}

.canvas-statusbar {
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: white;
  border-top: 1px solid #e8e8e8;
  font-size: 12px;
  color: #666;
}

.statusbar-left {
  display: flex;
  gap: 16px;
}

.statusbar-center {
  flex: 1;
  text-align: center;
}

.statusbar-right {
  display: flex;
  gap: 8px;
}

/* 深色主题支持 */
@media (prefers-color-scheme: dark) {
  .canvas-container {
    background-color: #1a1a1a;
  }
  
  .canvas-toolbar,
  .canvas-sidebar-left,
  .canvas-sidebar-right,
  .canvas-statusbar {
    background: #262626;
    border-color: #434343;
  }
  
  .canvas-workspace {
    background: #1a1a1a;
  }
  
  .canvas-statusbar {
    color: #a6a6a6;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .canvas-sidebar-left,
  .canvas-sidebar-right {
    width: 240px;
  }
}

@media (max-width: 576px) {
  .canvas-sidebar-left,
  .canvas-sidebar-right {
    position: absolute;
    top: 0;
    bottom: 32px;
    z-index: 200;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  }
  
  .canvas-sidebar-left {
    left: 0;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  
  .canvas-sidebar-left.show {
    transform: translateX(0);
  }
  
  .canvas-sidebar-right {
    right: 0;
    transform: translateX(100%);
    transition: transform 0.3s ease;
  }
  
  .canvas-sidebar-right.show {
    transform: translateX(0);
  }
}
</style> 