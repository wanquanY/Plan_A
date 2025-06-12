<template>
  <Teleport to="body">
    <div
      v-if="showToolbar"
      :style="{
        position: 'fixed',
        left: `${toolbarPosition.x}px`,
        top: `${toolbarPosition.y}px`,
        zIndex: 9999
      }"
      class="floating-toolbar"
      @click.stop
    >
      <!-- 简略工具栏 -->
      <div class="toolbar-main">
        <!-- 元素类型选择 -->
        <a-dropdown :trigger="['click']" placement="top">
          <div class="toolbar-item shape-selector" title="元素类型">
            <span class="shape-icon">{{ getShapeIcon(currentElementType) }}</span>
            <span class="dropdown-arrow">▼</span>
          </div>
          <template #overlay>
            <a-menu @click="handleShapeMenuClick">
              <a-menu-item key="rectangle">
                <span class="menu-shape-icon">▭</span> 矩形
              </a-menu-item>
              <a-menu-item key="circle">
                <span class="menu-shape-icon">●</span> 圆形
              </a-menu-item>
              <a-menu-item key="diamond">
                <span class="menu-shape-icon">◆</span> 菱形
              </a-menu-item>
              <a-menu-item key="text">
                <span class="menu-shape-icon">T</span> 文本
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>

        <!-- 填充色 -->
        <a-dropdown :trigger="['click']" placement="top">
          <div class="toolbar-item fill-color" title="填充色">
            <div 
              class="color-display" 
              :style="{ backgroundColor: fillColor }"
            ></div>
            <span class="dropdown-arrow">▼</span>
          </div>
          <template #overlay>
            <div class="color-palette">
              <div class="color-grid">
                <div
                  v-for="color in fillColorPresets"
                  :key="color"
                  class="color-option"
                  :style="{ backgroundColor: color }"
                  @click="setFillColor(color)"
                  :class="{ active: fillColor === color }"
                ></div>
              </div>
              <div class="custom-color">
                <input
                  type="color"
                  v-model="fillColor"
                  @change="handleFillColorChange"
                  class="color-input"
                />
                <span>自定义颜色</span>
              </div>
            </div>
          </template>
        </a-dropdown>

        <!-- 边框 -->
        <a-dropdown :trigger="['click']" placement="top">
          <div class="toolbar-item stroke-style" title="边框">
            <div class="stroke-display">
              <div 
                class="stroke-preview"
                :style="{ 
                  borderColor: strokeColor,
                  borderWidth: `${strokeWidth}px`,
                  borderStyle: strokeWidth > 0 ? 'solid' : 'none'
                }"
              ></div>
            </div>
            <span class="dropdown-arrow">▼</span>
          </div>
          <template #overlay>
            <div class="stroke-palette">
              <div class="stroke-width-section">
                <div class="section-title">边框粗细</div>
                <div class="stroke-widths">
                  <div
                    v-for="width in [0, 1, 2, 3, 4, 5]"
                    :key="width"
                    class="stroke-width-option"
                    @click="setStrokeWidth(width)"
                    :class="{ active: strokeWidth === width }"
                  >
                    <div 
                      class="width-preview"
                      :style="{ height: `${Math.max(width, 1)}px`, backgroundColor: strokeColor }"
                    ></div>
                    <span>{{ width === 0 ? '无' : `${width}px` }}</span>
                  </div>
                </div>
              </div>
              <div class="stroke-color-section">
                <div class="section-title">边框颜色</div>
                <div class="color-grid">
                  <div
                    v-for="color in fillColorPresets"
                    :key="color"
                    class="color-option"
                    :style="{ backgroundColor: color }"
                    @click="setStrokeColor(color)"
                    :class="{ active: strokeColor === color }"
                  ></div>
                </div>
              </div>
            </div>
          </template>
        </a-dropdown>

        <!-- 更多选项 -->
        <a-dropdown :trigger="['click']" placement="topRight">
          <div class="toolbar-item more-btn" title="更多选项">
            <span class="icon">⋯</span>
          </div>
          <template #overlay>
            <a-menu class="context-menu" @click="handleMenuClick">
              <a-menu-item key="copy">
                <span class="menu-icon">📋</span>
                <span class="menu-text">复制</span>
                <span class="menu-shortcut">⌘ + C</span>
              </a-menu-item>
              
              <a-menu-item key="paste">
                <span class="menu-icon">📋</span>
                <span class="menu-text">粘贴</span>
                <span class="menu-shortcut">⌘ + V</span>
              </a-menu-item>
              
              <a-menu-item key="duplicate">
                <span class="menu-icon">📄</span>
                <span class="menu-text">创建副本</span>
                <span class="menu-shortcut">⌘ + D</span>
              </a-menu-item>
              
              <a-menu-divider />
              
              <a-sub-menu key="layer" title="层级">
                <template #title>
                  <span class="menu-icon">📚</span>
                  <span class="menu-text">层级</span>
                  <span class="menu-arrow">▶</span>
                </template>
                <a-menu-item key="bring-forward">
                  <span class="submenu-text">上移一层</span>
                  <span class="menu-shortcut">⌘ + ↑</span>
                </a-menu-item>
                <a-menu-item key="send-backward">
                  <span class="submenu-text">下移一层</span>
                  <span class="menu-shortcut">⌘ + ↓</span>
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="bring-to-front">
                  <span class="submenu-text">置于顶层</span>
                  <span class="menu-shortcut">⌘ + Shift + ↑</span>
                </a-menu-item>
                <a-menu-item key="send-to-back">
                  <span class="submenu-text">置于底层</span>
                  <span class="menu-shortcut">⌘ + Shift + ↓</span>
                </a-menu-item>
              </a-sub-menu>
              
              <a-menu-item key="copy-style">
                <span class="menu-icon">🎨</span>
                <span class="menu-text">复制样式</span>
                <span class="menu-shortcut">⌘ + ⌥ + C</span>
              </a-menu-item>
              
              <a-menu-divider />
              
              <a-menu-item key="flip-horizontal">
                <span class="menu-icon">↔️</span>
                <span class="menu-text">水平翻转</span>
                <span class="menu-shortcut">Shift + H</span>
              </a-menu-item>
              
              <a-menu-item key="flip-vertical">
                <span class="menu-icon">↕️</span>
                <span class="menu-text">垂直翻转</span>
                <span class="menu-shortcut">Shift + V</span>
              </a-menu-item>
              
              <a-menu-divider />
              
              <a-menu-item key="lock">
                <span class="menu-icon">🔒</span>
                <span class="menu-text">锁定</span>
                <span class="menu-shortcut">⌘ + ⌥ + L</span>
              </a-menu-item>
              
              <a-menu-item key="properties">
                <span class="menu-icon">⚙️</span>
                <span class="menu-text">属性</span>
                <span class="menu-shortcut">⌘ + ⌥ + I</span>
              </a-menu-item>
              
              <a-menu-divider />
              
              <a-menu-item key="delete" class="danger-item">
                <span class="menu-icon">🗑️</span>
                <span class="menu-text">删除</span>
                <span class="menu-shortcut">⌫</span>
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>


  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useCanvasStore } from '../stores/canvasStore'
import type { CanvasElement, ElementStyle } from '@/types/canvas'

const canvasStore = useCanvasStore()

console.log('[FloatingToolbar] CanvasStore实例:', canvasStore)

// 响应式数据
const selectedElements = computed(() => {
  const elements = canvasStore.selectedElements || []
  console.log('[FloatingToolbar] computed selectedElements:', elements)
  return elements
})
const showToolbar = ref(false)
const toolbarPosition = ref({ x: 0, y: 0 })

// 当前选中元素的样式
const currentElementType = ref('rectangle')
const fillColor = ref('#1890ff')
const strokeColor = ref('#000000')
const strokeWidth = ref(1)

// 颜色预设
const fillColorPresets = [
  '#1890ff', '#52c41a', '#faad14', '#f5222d', 
  '#722ed1', '#13c2c2', '#eb2f96', '#666666',
  '#ffffff', '#000000'
]

// 详细面板状态

// 监听选中元素变化
watch(selectedElements, (newElements) => {
  console.log('[FloatingToolbar] 选中元素变化:', newElements)
  console.log('[FloatingToolbar] 元素数量:', newElements?.length || 0)
  console.log('[FloatingToolbar] showToolbar当前值:', showToolbar.value)
  
  if (newElements && newElements.length > 0) {
    console.log('[FloatingToolbar] 设置显示工具栏')
    showToolbar.value = true
    updateToolbarPosition()
    updateFormFromSelectedElement()
  } else {
    console.log('[FloatingToolbar] 设置隐藏工具栏')
    showToolbar.value = false
  }
  
  console.log('[FloatingToolbar] showToolbar更新后值:', showToolbar.value)
}, { immediate: true, deep: true })

// 更新工具栏位置
const updateToolbarPosition = () => {
  console.log('[FloatingToolbar] 开始更新工具栏位置')
  
  if (!selectedElements.value || selectedElements.value.length === 0) {
    console.log('[FloatingToolbar] 没有选中元素，跳过位置更新')
    return
  }
  
  try {
    const element = selectedElements.value[0]
    console.log('[FloatingToolbar] 选中元素:', element)
    
    if (!element) {
      console.log('[FloatingToolbar] 元素为空，跳过位置更新')
      return
    }
    
    // 尝试多种可能的画布容器选择器
    const selectors = [
      '.konva-stage-container',
      '.canvas-stage', 
      '.canvas-container',
      '[data-testid="canvas-stage"]',
      '.konva-content',
      'canvas'
    ]
    
    let canvasContainer = null
    let canvasRect = null
    
    for (const selector of selectors) {
      const container = document.querySelector(selector)
      console.log(`[FloatingToolbar] 尝试选择器 ${selector}:`, container)
      if (container) {
        canvasContainer = container
        canvasRect = container.getBoundingClientRect()
        console.log(`[FloatingToolbar] 找到容器 ${selector}, 位置:`, canvasRect)
        break
      }
    }
    
    if (!canvasContainer || !canvasRect) {
      console.log('[FloatingToolbar] 没有找到任何画布容器，使用默认位置')
      toolbarPosition.value = { x: 100, y: 100 }
      return
    }
    
    // 获取画布的视口状态（缩放、平移）
    const viewport = canvasStore.viewport || { x: 0, y: 0, zoom: 1 }
    console.log('[FloatingToolbar] 画布视口状态:', viewport)
    
    // 计算元素在画布中的实际位置（考虑视口变换）
    const elementCanvasX = (element.x || 0) * viewport.zoom + viewport.x
    const elementCanvasY = (element.y || 0) * viewport.zoom + viewport.y
    const elementWidth = (element.width || 100) * viewport.zoom
    const elementHeight = (element.height || 100) * viewport.zoom
    
    console.log('[FloatingToolbar] 元素画布位置:', { 
      x: elementCanvasX, 
      y: elementCanvasY, 
      width: elementWidth, 
      height: elementHeight 
    })
    
    // 转换为屏幕坐标
    const elementScreenX = canvasRect.left + elementCanvasX
    const elementScreenY = canvasRect.top + elementCanvasY
    
    console.log('[FloatingToolbar] 元素屏幕位置:', { 
      x: elementScreenX, 
      y: elementScreenY 
    })
    
    // 工具栏尺寸
    const toolbarWidth = 300  // 减小宽度
    const toolbarHeight = 50
    const margin = 8
    
    // 计算工具栏位置 - 放在元素右上角附近
    let x = elementScreenX + elementWidth + margin
    let y = elementScreenY - margin
    
    // 边界检查和调整
    const windowWidth = window.innerWidth
    const windowHeight = window.innerHeight
    
    // 水平边界调整 - 如果右侧没有空间，放到左侧
    if (x + toolbarWidth > windowWidth - margin) {
      x = elementScreenX - toolbarWidth - margin
    }
    
    // 确保不超出左边界
    x = Math.max(margin, x)
    
    // 垂直边界调整 - 如果上方没有空间，稍微下移
    if (y < margin) {
      y = elementScreenY + margin
    }
    
    // 确保不超出窗口底部
    if (y + toolbarHeight > windowHeight - margin) {
      y = elementScreenY + elementHeight - toolbarHeight - margin
    }
    
    toolbarPosition.value = { x, y }
    
    console.log('[FloatingToolbar] 最终工具栏位置:', toolbarPosition.value)
  } catch (error) {
    console.error('[FloatingToolbar] 位置计算错误:', error)
    // 错误时使用安全位置
    toolbarPosition.value = { x: 100, y: 100 }
  }
}

// 从选中元素更新表单
const updateFormFromSelectedElement = () => {
  if (!selectedElements.value || selectedElements.value.length === 0) return
  
  const element = selectedElements.value[0]
  if (!element) return
  
  // 更新简略工具栏
  currentElementType.value = element.type || 'rectangle'
  fillColor.value = element.style?.fill || '#1890ff'
  strokeColor.value = element.style?.stroke || '#000000'
  strokeWidth.value = element.style?.strokeWidth || 1
}

// 获取形状图标
const getShapeIcon = (type: string) => {
  const icons = {
    rectangle: '▭',
    circle: '●',
    diamond: '◆',
    text: 'T'
  }
  return icons[type as keyof typeof icons] || '▭'
}

// 处理形状菜单点击
const handleShapeMenuClick = ({ key }: { key: string }) => {
  currentElementType.value = key
  updateSelectedElementsStyle({ type: key })
}

// 处理元素类型改变
const handleElementTypeChange = (newType: string) => {
  updateSelectedElementsStyle({ type: newType })
}

// 处理填充色改变
const handleFillColorChange = () => {
  updateSelectedElementsStyle({ fill: fillColor.value })
}

// 设置填充色（预设颜色）
const setFillColor = (color: string) => {
  fillColor.value = color
  updateSelectedElementsStyle({ fill: color })
}

// 处理边框色改变
const handleStrokeColorChange = () => {
  updateSelectedElementsStyle({ stroke: strokeColor.value })
}

// 设置边框宽度
const setStrokeWidth = (width: number) => {
  strokeWidth.value = width
  updateSelectedElementsStyle({ strokeWidth: width })
}

// 设置边框颜色
const setStrokeColor = (color: string) => {
  strokeColor.value = color
  updateSelectedElementsStyle({ stroke: color })
}

// 处理边框粗细改变
const handleStrokeWidthChange = () => {
  updateSelectedElementsStyle({ strokeWidth: strokeWidth.value })
}

// 更新选中元素样式
const updateSelectedElementsStyle = (styleUpdates: Partial<ElementStyle & { type?: string }>) => {
  if (!selectedElements.value || selectedElements.value.length === 0) return
  
  try {
    canvasStore.updateSelectedElementsStyle(styleUpdates)
    console.log('[FloatingToolbar] 更新样式:', styleUpdates)
  } catch (error) {
    console.error('[FloatingToolbar] 样式更新错误:', error)
  }
}

// 处理右键菜单点击
const handleMenuClick = ({ key }: { key: string }) => {
  console.log('[FloatingToolbar] 菜单点击:', key)
  
  if (!selectedElements.value || selectedElements.value.length === 0) {
    console.log('[FloatingToolbar] 没有选中元素')
    return
  }

  switch (key) {
    case 'copy':
      handleCopy()
      break
    case 'paste':
      handlePaste()
      break
    case 'duplicate':
      handleDuplicate()
      break
    case 'bring-forward':
      handleBringForward()
      break
    case 'send-backward':
      handleSendBackward()
      break
    case 'bring-to-front':
      handleBringToFront()
      break
    case 'send-to-back':
      handleSendToBack()
      break
    case 'copy-style':
      handleCopyStyle()
      break
    case 'flip-horizontal':
      handleFlipHorizontal()
      break
    case 'flip-vertical':
      handleFlipVertical()
      break
    case 'lock':
      handleLock()
      break
    case 'properties':
      handleShowProperties()
      break
    case 'delete':
      handleDelete()
      break
    default:
      console.log('[FloatingToolbar] 未知菜单项:', key)
  }
}

// 菜单功能实现
const handleCopy = () => {
  canvasStore.copyElements(selectedElements.value)
  console.log('[FloatingToolbar] 复制元素')
}

const handlePaste = () => {
  canvasStore.pasteElements()
  console.log('[FloatingToolbar] 粘贴元素')
}

const handleDuplicate = () => {
  canvasStore.duplicateElements(selectedElements.value)
  console.log('[FloatingToolbar] 创建副本')
}

const handleBringForward = () => {
  selectedElements.value.forEach(element => {
    canvasStore.bringElementForward(element.id)
  })
  console.log('[FloatingToolbar] 上移一层')
}

const handleSendBackward = () => {
  selectedElements.value.forEach(element => {
    canvasStore.sendElementBackward(element.id)
  })
  console.log('[FloatingToolbar] 下移一层')
}

const handleBringToFront = () => {
  selectedElements.value.forEach(element => {
    canvasStore.bringElementToFront(element.id)
  })
  console.log('[FloatingToolbar] 置于顶层')
}

const handleSendToBack = () => {
  selectedElements.value.forEach(element => {
    canvasStore.sendElementToBack(element.id)
  })
  console.log('[FloatingToolbar] 置于底层')
}

const handleCopyStyle = () => {
  if (selectedElements.value.length > 0) {
    canvasStore.copyStyle(selectedElements.value[0])
    console.log('[FloatingToolbar] 复制样式')
  }
}

const handleFlipHorizontal = () => {
  selectedElements.value.forEach(element => {
    canvasStore.flipElement(element.id, 'horizontal')
  })
  console.log('[FloatingToolbar] 水平翻转')
}

const handleFlipVertical = () => {
  selectedElements.value.forEach(element => {
    canvasStore.flipElement(element.id, 'vertical')
  })
  console.log('[FloatingToolbar] 垂直翻转')
}

const handleLock = () => {
  selectedElements.value.forEach(element => {
    canvasStore.toggleElementLock(element.id)
  })
  console.log('[FloatingToolbar] 切换锁定状态')
}

const handleShowProperties = () => {
  console.log('[FloatingToolbar] 显示属性面板')
  // 这里可以触发显示属性面板的事件或导航
}

const handleDelete = () => {
  canvasStore.deleteElements(selectedElements.value.map(el => el.id))
  console.log('[FloatingToolbar] 删除元素')
}



// 窗口大小变化时更新位置
const handleResize = () => {
  if (showToolbar.value) {
    updateToolbarPosition()
  }
}

// 滚动时更新位置
const handleScroll = () => {
  if (showToolbar.value) {
    updateToolbarPosition()
  }
}

// 生命周期
onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('scroll', handleScroll, true)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('scroll', handleScroll, true)
})
</script>

<style scoped>
.floating-toolbar {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.08);
  user-select: none;
  overflow: hidden;
}

.toolbar-main {
  display: flex;
  align-items: center;
  padding: 4px;
  gap: 1px;
}

.toolbar-item {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 4px 6px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  background: transparent;
}

.toolbar-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.toolbar-item:active {
  background: rgba(0, 0, 0, 0.08);
}

/* 形状选择器 */
.shape-selector {
  gap: 4px;
}

.shape-icon {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.dropdown-arrow {
  font-size: 10px;
  color: #666;
  margin-left: 2px;
}

/* 填充色显示 */
.fill-color {
  gap: 4px;
}

.color-display {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.15);
}

/* 边框样式显示 */
.stroke-style {
  gap: 4px;
}

.stroke-display {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stroke-preview {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: transparent;
}

/* 图标按钮 */
.more-btn .icon {
  font-size: 16px;
  color: #333;
}

/* 下拉面板样式 */
.color-palette {
  padding: 12px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 200px;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

.color-option {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.15s ease;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.active {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.custom-color {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.color-input {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.custom-color span {
  font-size: 12px;
  color: #666;
}

/* 边框面板 */
.stroke-palette {
  padding: 12px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 180px;
}

.section-title {
  font-size: 12px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.stroke-width-section {
  margin-bottom: 16px;
}

.stroke-widths {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stroke-width-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.stroke-width-option:hover {
  background: rgba(0, 0, 0, 0.04);
}

.stroke-width-option.active {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.width-preview {
  width: 30px;
  border-radius: 2px;
}

.stroke-width-option span {
  font-size: 12px;
}

.stroke-color-section .color-grid {
  margin-bottom: 0;
}

/* 菜单项样式 */
.menu-shape-icon {
  margin-right: 8px;
  font-weight: 500;
}

/* 右键菜单样式 */
:deep(.context-menu) {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 6px 0;
  min-width: 220px;
}

:deep(.context-menu .ant-menu-item) {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  margin: 0;
  height: auto;
  line-height: 1.4;
  border-radius: 0;
  transition: all 0.15s ease;
  color: #333;
  font-size: 13px;
}

:deep(.context-menu .ant-menu-item:hover) {
  background: rgba(24, 144, 255, 0.06);
  color: #1890ff;
}

:deep(.context-menu .ant-menu-item.danger-item) {
  color: #ff4d4f;
}

:deep(.context-menu .ant-menu-item.danger-item:hover) {
  background: rgba(255, 77, 79, 0.06);
  color: #ff4d4f;
}

:deep(.context-menu .ant-menu-divider) {
  margin: 6px 0;
  background: #f0f0f0;
}

:deep(.context-menu .ant-menu-submenu-title) {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  margin: 0;
  height: auto;
  line-height: 1.4;
  color: #333;
  font-size: 13px;
}

:deep(.context-menu .ant-menu-submenu-title:hover) {
  background: rgba(24, 144, 255, 0.06);
  color: #1890ff;
}

.menu-icon {
  font-size: 14px;
  margin-right: 10px;
  width: 16px;
  display: inline-block;
}

.menu-text {
  flex: 1;
  margin-right: 8px;
}

.menu-shortcut {
  font-size: 11px;
  color: #999;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
}

.menu-arrow {
  font-size: 10px;
  color: #999;
  margin-left: auto;
}

.submenu-text {
  flex: 1;
  margin-right: 8px;
}

/* 层级子菜单样式 */
:deep(.context-menu .ant-menu-submenu-popup) {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

:deep(.context-menu .ant-menu-submenu-popup .ant-menu-item) {
  padding: 8px 16px;
  margin: 0;
  color: #333;
  font-size: 13px;
}

:deep(.context-menu .ant-menu-submenu-popup .ant-menu-item:hover) {
  background: rgba(24, 144, 255, 0.06);
  color: #1890ff;
}



/* 响应式调整 */
@media (max-width: 768px) {
  .toolbar-main {
    flex-wrap: wrap;
    max-width: 300px;
  }
  
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style> 