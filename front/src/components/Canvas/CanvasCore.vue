<template>
  <div class="canvas-core" ref="canvasContainer">
    <div class="canvas-wrapper" :style="wrapperStyle">
      <div 
        ref="stageContainer" 
        class="stage-container"
        @wheel="handleWheel"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @contextmenu.prevent="handleContextMenu"
      ></div>
      
      <!-- 网格背景 -->
      <div v-if="config.grid.enabled" class="canvas-grid" :style="gridStyle"></div>
      
      <!-- 选择框 -->
      <div 
        v-if="selectionBox" 
        class="selection-box"
        :style="selectionBoxStyle"
      ></div>
    </div>
    
    <!-- 右键菜单 -->
    <div 
      v-if="contextMenu.visible" 
      class="context-menu"
      :style="contextMenuStyle"
      @click="hideContextMenu"
    >
      <div class="context-menu-item" @click="handleCopy">复制</div>
      <div class="context-menu-item" @click="handlePaste">粘贴</div>
      <div class="context-menu-item" @click="handleDelete">删除</div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-item" @click="handleBringToFront">置于顶层</div>
      <div class="context-menu-item" @click="handleSendToBack">置于底层</div>
    </div>


  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import Konva from 'konva'
import { useCanvasStore } from './stores/canvasStore'
import { useToolStore } from './stores/toolStore'
import { ElementType, type CanvasElement } from './types/canvas'
import { ToolType } from './types/tools'


// Props
interface Props {
  canvasId?: string
  width?: number
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  canvasId: '',
  width: 800,
  height: 600
})

// Emits
interface Emits {
  (e: 'canvas-updated', data: any): void
}

const emit = defineEmits<Emits>()

// 状态管理
const canvasStore = useCanvasStore()
const toolStore = useToolStore()
const { canvasData, viewport, selection, config } = canvasStore
const { currentTool, isDrawing, toolOptions } = toolStore

// 设置默认工具为矩形，方便测试
if (currentTool.value === ToolType.SELECT) {
  toolStore.setCurrentTool(ToolType.RECTANGLE)
}

// DOM引用
const canvasContainer = ref<HTMLElement>()
const stageContainer = ref<HTMLElement>()

// Konva实例
let stage: Konva.Stage | null = null
let layer: Konva.Layer | null = null
let transformer: Konva.Transformer | null = null
let connectionLayer: Konva.Layer | null = null // 连接点专用图层
let customControlLayer: Konva.Layer | null = null // 自定义控制层

// 交互状态
const isDragging = ref(false)
const isSelecting = ref(false)
const selectionBox = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0
})



// 样式计算
const wrapperStyle = computed(() => ({
  transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
  transformOrigin: '0 0'
}))

const gridStyle = computed(() => {
  if (!config.grid.enabled) return {}
  
  const size = config.grid.size * viewport.zoom
  return {
    backgroundImage: `
      linear-gradient(to right, ${config.grid.color} 1px, transparent 1px),
      linear-gradient(to bottom, ${config.grid.color} 1px, transparent 1px)
    `,
    backgroundSize: `${size}px ${size}px`,
    opacity: config.grid.opacity
  }
})

const selectionBoxStyle = computed(() => {
  if (!selectionBox.value) return {}
  
  return {
    position: 'absolute',
    left: `${selectionBox.value.x}px`,
    top: `${selectionBox.value.y}px`,
    width: `${selectionBox.value.width}px`,
    height: `${selectionBox.value.height}px`,
    border: '1.5px dashed #4285f4',
    backgroundColor: 'rgba(66, 133, 244, 0.08)',
    borderRadius: '2px',
    pointerEvents: 'none'
  }
})

const contextMenuStyle = computed(() => ({
  position: 'fixed',
  left: `${contextMenu.value.x}px`,
  top: `${contextMenu.value.y}px`,
  zIndex: 1000
}))

// 初始化Konva舞台
const initStage = () => {
  if (!stageContainer.value) return
  
  const containerRect = stageContainer.value.getBoundingClientRect()
  
  stage = new Konva.Stage({
    container: stageContainer.value,
    width: containerRect.width,
    height: containerRect.height,
    draggable: currentTool.value === ToolType.HAND
  })
  
  layer = new Konva.Layer()
  stage.add(layer)
  
  // 创建连接点图层
  connectionLayer = new Konva.Layer()
  stage.add(connectionLayer)
  
  // 创建变换器
  transformer = new Konva.Transformer({
    nodes: [],
    padding: 4,
    // 边框样式 - 改为实线
    borderStroke: '#4285f4',
    borderStrokeWidth: 2,
    borderDash: [], // 实线，不是虚线
    // 锚点样式 - 方形控制点
    anchorFill: '#4285f4',
    anchorStroke: '#ffffff',
    anchorStrokeWidth: 2,
    anchorSize: 8,
    anchorCornerRadius: 0, // 方形控制点，不是圆形
    // 悬停效果
    anchorStrokeEnabled: true,
    // 只启用四个角的控制点，移除边中间的控制点
    enabledAnchors: ['top-left', 'top-right', 'bottom-left', 'bottom-right'],
    // 禁用默认旋转功能
    rotateEnabled: false,
    rotateLineVisible: false,
    // 禁用翻转
    flipEnabled: false,
    // 自定义锚点样式函数
    anchorStyleFunc: (anchor) => {
      // 缩放控制点样式 - 方形
      anchor.fill('#4285f4')
      anchor.stroke('#ffffff')
      anchor.strokeWidth(2)
      anchor.cornerRadius(0) // 方形
      anchor.width(8)
      anchor.height(8)
    }
  })
  layer.add(transformer)
  
  // 创建自定义控制层
  customControlLayer = new Konva.Layer()
  stage.add(customControlLayer)
  
  // 监听变换器事件
  transformer.on('transform', () => {
    updateCustomControls()
  })
  
  transformer.on('transformend', () => {
    updateCustomControls()
  })
  
  // 监听舞台事件
  stage.on('click tap', handleStageClick)
  stage.on('dragstart', () => { isDragging.value = true })
  stage.on('dragend', () => { isDragging.value = false })
  
  // 渲染元素
  renderElements()
}

// 渲染画布元素
const renderElements = () => {
  if (!layer) return
  
  // 清除现有元素（保留transformer）
  const children = layer.children.slice()
  children.forEach(child => {
    if (child !== transformer) {
      child.destroy()
    }
  })
  
  // 渲染所有元素
  canvasData.elements.forEach(element => {
    const shape = createKonvaShape(element)
    if (shape) {
      layer!.add(shape)
    }
  })
  
  layer.batchDraw()
  updateSelection()
}

// 创建Konva形状
const createKonvaShape = (element: CanvasElement) => {
  const baseConfig = {
    id: element.id,
    x: element.x,
    y: element.y,
    width: element.width,
    height: element.height,
    rotation: element.rotation,
    fill: element.style.fill || '#ffffff',
    stroke: element.style.stroke || '#000000',
    strokeWidth: element.style.strokeWidth || 1,
    opacity: element.style.opacity || 1,
    draggable: true,
    visible: element.visible
  }
  
  let shape: Konva.Shape | null = null
  
  switch (element.type) {
    case ElementType.RECTANGLE:
      shape = new Konva.Rect(baseConfig)
      break
      
    case ElementType.CIRCLE:
      shape = new Konva.Circle({
        ...baseConfig,
        radius: Math.min(element.width, element.height) / 2
      })
      break
      
    case ElementType.ELLIPSE:
      shape = new Konva.Ellipse({
        ...baseConfig,
        radiusX: element.width / 2,
        radiusY: element.height / 2
      })
      break
      
    case ElementType.TEXT:
      shape = new Konva.Text({
        ...baseConfig,
        text: element.data?.text || '文本',
        fontSize: element.style.fontSize || 16,
        fontFamily: element.style.fontFamily || 'Arial',
        fill: element.style.fill || '#000000',
        align: element.style.textAlign || 'left',
        verticalAlign: element.style.textVerticalAlign || 'top'
      })
      break
      
    case ElementType.LINE:
      shape = new Konva.Line({
        ...baseConfig,
        points: element.data?.points || [0, 0, element.width, element.height],
        stroke: element.style.stroke || '#000000',
        strokeWidth: element.style.strokeWidth || 2
      })
      break
  }
  
  if (shape) {
    // 添加事件监听
    shape.on('click tap', (e) => {
      e.cancelBubble = true
      handleElementClick(element.id, e.evt.ctrlKey || e.evt.metaKey)
    })
    
    shape.on('dragend', () => {
      const pos = shape!.position()
      canvasStore.updateElement(element.id, { x: pos.x, y: pos.y })
      
      // 更新连接点位置
      updateConnectionPoints()
    })
    
    shape.on('transform', () => {
      const scaleX = shape!.scaleX()
      const scaleY = shape!.scaleY()
      const width = Math.max(5, shape!.width() * scaleX)
      const height = Math.max(5, shape!.height() * scaleY)
      
      canvasStore.updateElement(element.id, {
        width: width,
        height: height,
        rotation: shape!.rotation()
      })
      
      // 重置缩放
      shape!.scaleX(1)
      shape!.scaleY(1)
      
      // 更新连接点位置
      updateConnectionPoints()
    })
  }
  
  return shape
}

// 处理舞台点击
const handleStageClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
  if (e.target === stage) {
    canvasStore.clearSelection()
  }
}

// 处理元素点击
const handleElementClick = (elementId: string, multiSelect = false) => {
  canvasStore.selectElement(elementId, multiSelect)
}

// 更新选择状态
const updateSelection = () => {
  if (!transformer || !layer) return
  
  const selectedNodes = selection.selectedIds
    .map(id => layer!.findOne(`#${id}`))
    .filter(node => node) as Konva.Node[]
  
  transformer.nodes(selectedNodes)
  transformer.getLayer()?.batchDraw()
  
  // 更新连接点显示
  updateConnectionPoints()
  
  // 更新自定义控制点
  updateCustomControls()
}

// 更新连接点显示
const updateConnectionPoints = () => {
  if (!connectionLayer) return
  
  // 清除现有连接点
  connectionLayer.destroyChildren()
  
  // 为选中的元素显示连接点
  if (selection.selectedIds.length === 1) {
    const selectedId = selection.selectedIds[0]
    const element = canvasData.elements.find(el => el.id === selectedId)
    if (element) {
      createConnectionPoints(element)
    }
  }
  
  connectionLayer.batchDraw()
}

// 创建元素的连接点
const createConnectionPoints = (element: CanvasElement) => {
  if (!connectionLayer) return
  
  const { x, y, width, height } = element
  
  // 连接点位置（四条边的中点）
  const points = [
    { x: x + width / 2, y: y, position: 'top' },           // 上边中点
    { x: x + width, y: y + height / 2, position: 'right' }, // 右边中点
    { x: x + width / 2, y: y + height, position: 'bottom' }, // 下边中点
    { x: x, y: y + height / 2, position: 'left' }           // 左边中点
  ]
  
  points.forEach(point => {
    // 创建连接点圆圈
    const connectionPoint = new Konva.Circle({
      x: point.x,
      y: point.y,
      radius: 6,
      fill: '#4285f4',
      stroke: '#ffffff',
      strokeWidth: 2,
      shadowColor: '#000000',
      shadowBlur: 3,
      shadowOpacity: 0.2,
      shadowOffset: { x: 0, y: 1 },
      draggable: true,
      name: `connection-point-${point.position}`,
      // 自定义属性
      elementId: element.id,
      position: point.position
    })
    
    // 连接点事件
    connectionPoint.on('mouseenter', () => {
      connectionPoint.fill('#1565c0')
      connectionPoint.scale({ x: 1.3, y: 1.3 })
      stage!.container().style.cursor = 'crosshair'
      connectionLayer!.batchDraw()
    })
    
    connectionPoint.on('mouseleave', () => {
      connectionPoint.fill('#4285f4')
      connectionPoint.scale({ x: 1, y: 1 })
      stage!.container().style.cursor = 'default'
      connectionLayer!.batchDraw()
    })
    
    // 点击连接点创建新元素
    connectionPoint.on('click', (e) => {
      e.cancelBubble = true
      handleConnectionPointClick(element, point.position, point.x, point.y)
    })
    
    // 拖拽连接点创建连接线
    connectionPoint.on('dragstart', (e) => {
      e.cancelBubble = true
      startConnection(element, point.position, point.x, point.y)
    })
    
    connectionLayer.add(connectionPoint)
  })
}

// 处理连接点点击
const handleConnectionPointClick = (sourceElement: CanvasElement, position: string, x: number, y: number) => {
  // 计算新元素的位置
  const offset = 120 // 新元素与原元素的距离
  let newX = x
  let newY = y
  
  switch (position) {
    case 'top':
      newY = y - offset - 60 // 60是新元素的高度
      newX = x - 50 // 50是新元素宽度的一半
      break
    case 'right':
      newX = x + offset
      newY = y - 30 // 30是新元素高度的一半
      break
    case 'bottom':
      newY = y + offset
      newX = x - 50
      break
    case 'left':
      newX = x - offset - 100 // 100是新元素的宽度
      newY = y - 30
      break
  }
  
  // 创建新元素
  const newElement = {
    type: sourceElement.type, // 创建相同类型的元素
    x: newX,
    y: newY,
    width: 100,
    height: 60,
    rotation: 0,
    zIndex: canvasData.elements.length,
    locked: false,
    visible: true,
    style: {
      fill: sourceElement.style.fill || '#ffffff',
      stroke: sourceElement.style.stroke || '#4285f4',
      strokeWidth: sourceElement.style.strokeWidth || 2,
      opacity: sourceElement.style.opacity || 1
    },
    data: sourceElement.type === ElementType.TEXT ? { text: '新文本' } : {}
  }
  
  // 添加新元素
  canvasStore.addElement(newElement)
  
  // TODO: 创建连接线（需要连接系统支持）
  console.log('创建新元素并连接:', { sourceElement: sourceElement.id, newElement, position })
}

// 开始连接操作
const startConnection = (sourceElement: CanvasElement, position: string, x: number, y: number) => {
  console.log('开始连接操作:', { sourceElement: sourceElement.id, position, x, y })
  // TODO: 实现拖拽连接功能
}

// 鼠标事件处理
const handleMouseDown = (e: MouseEvent) => {
  if (currentTool.value === ToolType.SELECT && e.button === 0) {
    startSelection(e)
  } else if (currentTool.value !== ToolType.HAND && currentTool.value !== ToolType.SELECT) {
    startDrawing(e)
  }
}

const handleMouseMove = (e: MouseEvent) => {
  if (isSelecting.value) {
    updateSelectionBox(e)
  } else if (isDrawing.value) {
    updateDrawing(e)
  }
}

const handleMouseUp = (e: MouseEvent) => {
  if (isSelecting.value) {
    endSelection(e)
  } else if (isDrawing.value) {
    endDrawing(e)
  }
}

// 选择框操作
const startSelection = (e: MouseEvent) => {
  const rect = stageContainer.value!.getBoundingClientRect()
  const startX = e.clientX - rect.left
  const startY = e.clientY - rect.top
  
  isSelecting.value = true
  selectionBox.value = {
    x: startX,
    y: startY,
    width: 0,
    height: 0
  }
}

const updateSelectionBox = (e: MouseEvent) => {
  if (!selectionBox.value) return
  
  const rect = stageContainer.value!.getBoundingClientRect()
  const currentX = e.clientX - rect.left
  const currentY = e.clientY - rect.top
  
  selectionBox.value.width = currentX - selectionBox.value.x
  selectionBox.value.height = currentY - selectionBox.value.y
}

const endSelection = (e: MouseEvent) => {
  if (!selectionBox.value) return
  
  // 查找选择框内的元素
  const box = selectionBox.value
  const elementsInBox = canvasData.elements.filter(element => {
    return element.x >= box.x && 
           element.y >= box.y &&
           element.x + element.width <= box.x + box.width &&
           element.y + element.height <= box.y + box.height
  })
  
  if (elementsInBox.length > 0) {
    canvasStore.clearSelection()
    elementsInBox.forEach(element => {
      canvasStore.selectElement(element.id, true)
    })
  }
  
  isSelecting.value = false
  selectionBox.value = null
}

// 绘制操作
const startDrawing = (e: MouseEvent) => {
  const rect = stageContainer.value!.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  // 对于简单点击创建（如矩形），直接创建元素
  if (currentTool.value === ToolType.RECTANGLE || 
      currentTool.value === ToolType.CIRCLE || 
      currentTool.value === ToolType.TEXT) {
    createElementAtPoint({ x, y })
    return
  }
  
  toolStore.startDrawing({ x, y })
}

const updateDrawing = (e: MouseEvent) => {
  // 绘制过程中的更新逻辑
}

const endDrawing = (e: MouseEvent) => {
  const rect = stageContainer.value!.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  toolStore.endDrawing({ x, y })
  
  // 根据工具类型创建元素（对于需要拖拽的工具）
  createElementFromTool({ x, y })
}

// 在指定点创建元素（点击创建）
const createElementAtPoint = (point: { x: number; y: number }) => {
  let elementType: ElementType
  let defaultWidth = 100
  let defaultHeight = 100
  
  switch (currentTool.value) {
    case ToolType.RECTANGLE:
      elementType = ElementType.RECTANGLE
      break
    case ToolType.CIRCLE:
      elementType = ElementType.CIRCLE
      break
    case ToolType.TEXT:
      elementType = ElementType.TEXT
      defaultWidth = 120
      defaultHeight = 30
      break
    default:
      return
  }
  
  const newElement = {
    type: elementType,
    x: point.x - defaultWidth / 2, // 以点击点为中心
    y: point.y - defaultHeight / 2,
    width: defaultWidth,
    height: defaultHeight,
    rotation: 0,
    zIndex: canvasData.elements.length,
    locked: false,
    visible: true,
    style: {
      fill: toolOptions.fillColor || '#ffffff',
      stroke: toolOptions.strokeColor || '#000000',
      strokeWidth: toolOptions.strokeWidth || 1,
      opacity: toolOptions.opacity || 1
    },
    data: elementType === ElementType.TEXT ? { text: '新文本' } : {}
  }
  
  const elementId = canvasStore.addElement(newElement)
  
  // 创建后自动选中新元素
  canvasStore.clearSelection()
  canvasStore.selectElement(elementId, false)
}

// 根据工具创建元素（拖拽创建）
const createElementFromTool = (endPoint: { x: number; y: number }) => {
  const startPoint = toolStore.drawingState.startPoint
  if (!startPoint) return
  
  const width = Math.abs(endPoint.x - startPoint.x)
  const height = Math.abs(endPoint.y - startPoint.y)
  const x = Math.min(startPoint.x, endPoint.x)
  const y = Math.min(startPoint.y, endPoint.y)
  
  if (width < 5 || height < 5) return // 最小尺寸检查
  
  let elementType: ElementType
  switch (currentTool.value) {
    case ToolType.RECTANGLE:
      elementType = ElementType.RECTANGLE
      break
    case ToolType.CIRCLE:
      elementType = ElementType.CIRCLE
      break
    case ToolType.TEXT:
      elementType = ElementType.TEXT
      break
    default:
      return
  }
  
  const newElement = {
    type: elementType,
    x,
    y,
    width,
    height,
    rotation: 0,
    zIndex: canvasData.elements.length,
    locked: false,
    visible: true,
    style: {
      fill: toolOptions.fillColor || '#ffffff',
      stroke: toolOptions.strokeColor || '#000000',
      strokeWidth: toolOptions.strokeWidth || 1,
      opacity: toolOptions.opacity || 1
    },
    data: elementType === ElementType.TEXT ? { text: '新文本' } : {}
  }
  
  const elementId = canvasStore.addElement(newElement)
  
  // 创建后自动选中新元素
  canvasStore.clearSelection()
  canvasStore.selectElement(elementId, false)
}

// 缩放处理
const handleWheel = (e: WheelEvent) => {
  e.preventDefault()
  
  const scaleBy = 1.1
  const stage = e.target as HTMLElement
  const rect = stage.getBoundingClientRect()
  
  const pointer = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
  
  const mousePointTo = {
    x: (pointer.x - viewport.x) / viewport.zoom,
    y: (pointer.y - viewport.y) / viewport.zoom
  }
  
  const newZoom = e.deltaY > 0 ? viewport.zoom / scaleBy : viewport.zoom * scaleBy
  const clampedZoom = Math.max(0.1, Math.min(5, newZoom))
  
  const newPos = {
    x: pointer.x - mousePointTo.x * clampedZoom,
    y: pointer.y - mousePointTo.y * clampedZoom
  }
  
  canvasStore.setZoom(clampedZoom)
  canvasStore.setViewport(newPos)
}

// 右键菜单
const handleContextMenu = (e: MouseEvent) => {
  e.preventDefault()
  contextMenu.value = {
    visible: true,
    x: e.clientX,
    y: e.clientY
  }
}

const hideContextMenu = () => {
  contextMenu.value.visible = false
}

const handleCopy = () => {
  // 复制功能
  hideContextMenu()
}

const handlePaste = () => {
  // 粘贴功能
  hideContextMenu()
}

const handleDelete = () => {
  selection.selectedIds.forEach(id => {
    canvasStore.removeElement(id)
  })
  hideContextMenu()
}

const handleBringToFront = () => {
  selection.selectedIds.forEach(id => {
    canvasStore.bringToFront(id)
  })
  hideContextMenu()
}

const handleSendToBack = () => {
  selection.selectedIds.forEach(id => {
    canvasStore.sendToBack(id)
  })
  hideContextMenu()
}

// 响应式调整
const handleResize = () => {
  if (!stage || !stageContainer.value) return
  
  const containerRect = stageContainer.value.getBoundingClientRect()
  stage.width(containerRect.width)
  stage.height(containerRect.height)
  stage.batchDraw()
}

// 监听器
watch(() => canvasData.elements, renderElements, { deep: true })
watch(() => selection.selectedIds, updateSelection)
watch(() => currentTool.value, (newTool) => {
  if (stage) {
    stage.draggable(newTool === ToolType.HAND)
  }
})



// 生命周期
onMounted(() => {
  nextTick(() => {
    initStage()
    window.addEventListener('resize', handleResize)
    document.addEventListener('click', hideContextMenu)
  })
})

onUnmounted(() => {
  if (stage) {
    stage.destroy()
  }
  if (connectionLayer) {
    connectionLayer.destroy()
  }
  if (customControlLayer) {
    customControlLayer.destroy()
  }
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', hideContextMenu)
})

// 更新自定义控制点
const updateCustomControls = () => {
  if (!customControlLayer) return
  
  // 清除现有自定义控制点
  customControlLayer.destroyChildren()
  
  // 为选中的元素显示自定义旋转控制点
  if (selection.selectedIds.length === 1) {
    const selectedId = selection.selectedIds[0]
    const selectedNode = layer?.findOne(`#${selectedId}`)
    if (selectedNode) {
      createCustomRotateControl(selectedNode)
    }
  }
  
  customControlLayer.batchDraw()
}

// 创建自定义旋转控制点
const createCustomRotateControl = (node: Konva.Node) => {
  if (!customControlLayer) return
  
  // 获取变换器的边界
  const box = transformer!.getClientRect()
  
  // 计算旋转中心
  const centerX = box.x + box.width / 2
  const centerY = box.y + box.height / 2
  
  // 计算左下角到中心的相对位置
  const offsetX = -box.width / 2 - 20  // 左下角外侧20px
  const offsetY = box.height / 2 + 20   // 左下角外侧20px
  
  // 根据当前旋转角度计算控制点的实际位置
  const nodeRotation = node.rotation() * Math.PI / 180
  const rotateX = centerX + offsetX * Math.cos(nodeRotation) - offsetY * Math.sin(nodeRotation)
  const rotateY = centerY + offsetX * Math.sin(nodeRotation) + offsetY * Math.cos(nodeRotation)
  
  // 创建旋转控制点背景圆圈
  const rotateControl = new Konva.Circle({
    x: rotateX,
    y: rotateY,
    radius: 8,
    fill: '#4285f4',
    stroke: '#ffffff',
    strokeWidth: 2,
    shadowColor: '#000000',
    shadowBlur: 3,
    shadowOpacity: 0.2,
    shadowOffset: { x: 0, y: 1 },
    draggable: true,
    name: 'custom-rotate-control'
  })
  
  // 创建旋转箭头图标
  const arrowGroup = new Konva.Group({
    x: rotateX,
    y: rotateY,
    rotation: node.rotation(), // 跟随节点旋转
    listening: false
  })
  
  // 双向箭头 - 上半部分
  const arrow1 = new Konva.Path({
    x: 0,
    y: 0,
    data: 'M-3,-1 L0,-4 L3,-1 M0,-4 L0,0',
    stroke: '#ffffff',
    strokeWidth: 1,
    fill: '#ffffff',
    listening: false
  })
  
  // 双向箭头 - 下半部分
  const arrow2 = new Konva.Path({
    x: 0,
    y: 0,
    data: 'M-3,1 L0,4 L3,1 M0,4 L0,0',
    stroke: '#ffffff',
    strokeWidth: 1,
    fill: '#ffffff',
    listening: false
  })
  
  arrowGroup.add(arrow1)
  arrowGroup.add(arrow2)
  
  // 悬停效果
  rotateControl.on('mouseenter', () => {
    rotateControl.fill('#1565c0')
    rotateControl.radius(10)
    stage!.container().style.cursor = 'grab'
    customControlLayer!.batchDraw()
  })
  
  rotateControl.on('mouseleave', () => {
    rotateControl.fill('#4285f4')
    rotateControl.radius(8)
    stage!.container().style.cursor = 'default'
    customControlLayer!.batchDraw()
  })
  
  // 旋转逻辑 - 优化性能版本
  let isDragging = false
  let startAngle = 0
  let initialRotation = 0
  let animationId: number | null = null
  let lastUpdateTime = 0
  const UPDATE_THROTTLE = 16 // 约60fps的更新频率
  
  rotateControl.on('dragstart', (e) => {
    e.cancelBubble = true
    isDragging = true
    
    // 记录初始旋转角度
    initialRotation = node.rotation()
    
    // 计算初始角度
    const dx = rotateControl.x() - centerX
    const dy = rotateControl.y() - centerY
    startAngle = Math.atan2(dy, dx)
    
    stage!.container().style.cursor = 'grabbing'
  })
  
  rotateControl.on('dragmove', (e) => {
    if (!isDragging) return
    e.cancelBubble = true
    
    const currentTime = Date.now()
    
    // 节流：限制更新频率，提升性能
    if (currentTime - lastUpdateTime < UPDATE_THROTTLE) return
    
    // 取消之前的动画帧
    if (animationId) {
      cancelAnimationFrame(animationId)
    }
    
    // 使用 requestAnimationFrame 优化性能
    animationId = requestAnimationFrame(() => {
      // 计算当前鼠标位置相对于旋转中心的角度
      const dx = rotateControl.x() - centerX
      const dy = rotateControl.y() - centerY
      const currentAngle = Math.atan2(dy, dx)
      
      // 计算角度差（转换为度数）
      let angleDiff = (currentAngle - startAngle) * 180 / Math.PI
      
      // 计算新的旋转角度
      let newRotation = initialRotation + angleDiff
      
      // 应用旋转（不要角度吸附，保持丝滑）
      node.rotation(newRotation)
      
      // 同时旋转箭头图标
      arrowGroup.rotation(newRotation)
      
      // 只重绘主图层，使用更高效的重绘方法
      layer!.batchDraw()
      
      // 重置动画ID
      animationId = null
      lastUpdateTime = currentTime
    })
  })
  
  rotateControl.on('dragend', (e) => {
    e.cancelBubble = true
    isDragging = false
    stage!.container().style.cursor = 'default'
    
    // 确保取消待处理的动画帧
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }
    
    // 拖拽结束后才更新状态和变换器
    const finalRotation = node.rotation()
    
    // 更新变换器
    transformer!.forceUpdate()
    
    // 批量更新元素数据（减少响应式更新）
    canvasStore.updateElement(node.id(), {
      rotation: finalRotation
    })
    
    // 直接更新控制点位置，不使用延时
    updateCustomControlsPosition(node, finalRotation)
  })
  
  // 点击旋转（每次点击旋转15度）
  rotateControl.on('click', (e) => {
    if (isDragging) return
    e.cancelBubble = true
    
    const currentRotation = node.rotation()
    const newRotation = currentRotation + 15
    
    node.rotation(newRotation)
    transformer!.forceUpdate()
    
    canvasStore.updateElement(node.id(), {
      rotation: newRotation
    })
    
    layer!.batchDraw()
    
    // 直接更新控制点位置
    updateCustomControlsPosition(node, newRotation)
  })
  
  // 添加到自定义控制层
  customControlLayer.add(rotateControl)
  customControlLayer.add(arrowGroup)
}

// 优化：直接更新控制点位置，避免重新创建
const updateCustomControlsPosition = (node: Konva.Node, rotation: number) => {
  if (!customControlLayer) return
  
  const rotateControl = customControlLayer.findOne('[name="custom-rotate-control"]') as Konva.Circle
  const arrowGroup = customControlLayer.children.find(child => 
    child instanceof Konva.Group && child.listening() === false
  ) as Konva.Group
  
  if (!rotateControl || !arrowGroup) return
  
  // 重新计算控制点位置
  const box = transformer!.getClientRect()
  const centerX = box.x + box.width / 2
  const centerY = box.y + box.height / 2
  
  const offsetX = -box.width / 2 - 20
  const offsetY = box.height / 2 + 20
  
  const nodeRotation = rotation * Math.PI / 180
  const rotateX = centerX + offsetX * Math.cos(nodeRotation) - offsetY * Math.sin(nodeRotation)
  const rotateY = centerY + offsetX * Math.sin(nodeRotation) + offsetY * Math.cos(nodeRotation)
  
  // 更新位置
  rotateControl.position({ x: rotateX, y: rotateY })
  arrowGroup.position({ x: rotateX, y: rotateY })
  arrowGroup.rotation(rotation)
  
  // 重绘控制层
  customControlLayer.batchDraw()
}
</script>

<style scoped>
.canvas-core {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  cursor: crosshair;
}

.canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.stage-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #ffffff;
}

.canvas-grid {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.selection-box {
  border: 1px dashed #1890ff;
  background-color: rgba(24, 144, 255, 0.1);
  pointer-events: none;
}

.context-menu {
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.08);
  padding: 4px 0;
  min-width: 120px;
}

.context-menu-item {
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #262626;
  transition: background-color 0.3s;
}

.context-menu-item:hover {
  background-color: #f5f5f5;
}

.context-menu-divider {
  height: 1px;
  background-color: #f0f0f0;
  margin: 4px 0;
}

/* 工具相关光标 */
.canvas-core[data-tool="select"] {
  cursor: default;
}

.canvas-core[data-tool="hand"] {
  cursor: grab;
}

.canvas-core[data-tool="hand"]:active {
  cursor: grabbing;
}

.canvas-core[data-tool="text"] {
  cursor: text;
}

.canvas-core[data-tool="pen"] {
  cursor: crosshair;
}
</style> 