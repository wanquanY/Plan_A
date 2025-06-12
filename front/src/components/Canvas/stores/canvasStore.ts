import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  CanvasData, 
  CanvasElement, 
  ViewportState, 
  SelectionState,
  CanvasConfig,
  BackgroundConfig 
} from '../types/canvas'
import { ElementType } from '../types/canvas'

export const useCanvasStore = defineStore('canvas', () => {
  // 画布数据
  const canvasData = ref<CanvasData>({
    id: '',
    name: '新建画板',
    width: 1920,
    height: 1080,
    zoom: 1,
    elements: [],
    background: {
      type: 'color',
      value: '#ffffff',
      opacity: 1
    },
    createdAt: new Date(),
    updatedAt: new Date()
  })

  // 视口状态
  const viewport = ref<ViewportState>({
    x: 0,
    y: 0,
    zoom: 1,
    rotation: 0
  })

  // 选择状态
  const selection = ref<SelectionState>({
    selectedIds: [],
    isMultiSelect: false,
    selectionBounds: undefined
  })

  // 画布配置
  const config = ref<CanvasConfig>({
    width: 1920,
    height: 1080,
    background: {
      type: 'color',
      value: '#ffffff',
      opacity: 1
    },
    grid: {
      enabled: false,
      size: 20,
      color: '#e0e0e0',
      opacity: 0.5
    },
    snap: {
      enabled: true,
      threshold: 10,
      snapToGrid: false,
      snapToElements: true
    }
  })

  // 计算属性
  const selectedElements = computed(() => {
    return canvasData.value.elements.filter(element => 
      selection.value.selectedIds.includes(element.id)
    )
  })

  const hasSelection = computed(() => {
    return selection.value.selectedIds.length > 0
  })

  const isMultiSelection = computed(() => {
    return selection.value.selectedIds.length > 1
  })

  // 动作方法
  const addElement = (element: Omit<CanvasElement, 'id'>) => {
    const newElement: CanvasElement = {
      ...element,
      id: generateId(),
    }
    canvasData.value.elements.push(newElement)
    canvasData.value.updatedAt = new Date()
    return newElement.id
  }

  const removeElement = (id: string) => {
    const index = canvasData.value.elements.findIndex(el => el.id === id)
    if (index !== -1) {
      canvasData.value.elements.splice(index, 1)
      canvasData.value.updatedAt = new Date()
      // 从选择中移除
      clearSelection(id)
    }
  }

  const updateElement = (id: string, updates: Partial<CanvasElement>) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      Object.assign(element, updates)
      canvasData.value.updatedAt = new Date()
    }
  }

  // 性能优化版本：用于高频更新（如旋转、拖拽）
  // 减少响应式更新开销，适用于实时交互场景
  const updateElementSilent = (id: string, updates: Partial<CanvasElement>) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      // 直接修改属性，避免触发深度响应式更新
      for (const [key, value] of Object.entries(updates)) {
        if (key === 'style' && element.style && typeof value === 'object') {
          // 样式对象的浅拷贝更新
          Object.assign(element.style, value)
        } else {
          ;(element as any)[key] = value
        }
      }
      // 只在必要时更新时间戳（减少响应式触发）
    }
  }

  // 批量更新元素（减少响应式更新次数）
  const batchUpdateElements = (updates: Array<{ id: string; updates: Partial<CanvasElement> }>) => {
    updates.forEach(({ id, updates: elementUpdates }) => {
      const element = canvasData.value.elements.find(el => el.id === id)
      if (element) {
        Object.assign(element, elementUpdates)
      }
    })
    // 只触发一次更新时间戳
    canvasData.value.updatedAt = new Date()
  }

  const duplicateElement = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      const duplicated = {
        ...element,
        x: element.x + 20,
        y: element.y + 20,
      }
      return addElement(duplicated)
    }
    return null
  }

  const selectElement = (id: string, addToSelection = false) => {
    if (addToSelection) {
      if (!selection.value.selectedIds.includes(id)) {
        selection.value.selectedIds.push(id)
        selection.value.isMultiSelect = selection.value.selectedIds.length > 1
      }
    } else {
      selection.value.selectedIds = [id]
      selection.value.isMultiSelect = false
    }
    updateSelectionBounds()
  }

  const deselectElement = (id: string) => {
    const index = selection.value.selectedIds.indexOf(id)
    if (index !== -1) {
      selection.value.selectedIds.splice(index, 1)
      selection.value.isMultiSelect = selection.value.selectedIds.length > 1
      updateSelectionBounds()
    }
  }

  const clearSelection = (excludeId?: string) => {
    if (excludeId) {
      selection.value.selectedIds = selection.value.selectedIds.filter(id => id !== excludeId)
    } else {
      selection.value.selectedIds = []
    }
    selection.value.isMultiSelect = false
    selection.value.selectionBounds = undefined
  }

  const selectAll = () => {
    selection.value.selectedIds = canvasData.value.elements.map(el => el.id)
    selection.value.isMultiSelect = selection.value.selectedIds.length > 1
    updateSelectionBounds()
  }

  const updateSelectionBounds = () => {
    if (selection.value.selectedIds.length === 0) {
      selection.value.selectionBounds = undefined
      return
    }

    const elements = selectedElements.value
    if (elements.length === 0) return

    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity

    elements.forEach(element => {
      minX = Math.min(minX, element.x)
      minY = Math.min(minY, element.y)
      maxX = Math.max(maxX, element.x + element.width)
      maxY = Math.max(maxY, element.y + element.height)
    })

    selection.value.selectionBounds = {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    }
  }

  const setViewport = (newViewport: Partial<ViewportState>) => {
    Object.assign(viewport.value, newViewport)
  }

  const setZoom = (zoom: number) => {
    viewport.value.zoom = Math.max(0.1, Math.min(5, zoom))
    canvasData.value.zoom = viewport.value.zoom
  }

  const resetViewport = () => {
    viewport.value = {
      x: 0,
      y: 0,
      zoom: 1,
      rotation: 0
    }
  }

  const setCanvasSize = (width: number, height: number) => {
    canvasData.value.width = width
    canvasData.value.height = height
    config.value.width = width
    config.value.height = height
  }

  const setBackground = (background: BackgroundConfig) => {
    canvasData.value.background = background
    config.value.background = background
    canvasData.value.updatedAt = new Date()
  }

  const bringToFront = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      const maxZIndex = Math.max(...canvasData.value.elements.map(el => el.zIndex))
      element.zIndex = maxZIndex + 1
      canvasData.value.updatedAt = new Date()
    }
  }

  const sendToBack = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      const minZIndex = Math.min(...canvasData.value.elements.map(el => el.zIndex))
      element.zIndex = minZIndex - 1
      canvasData.value.updatedAt = new Date()
    }
  }

  // 工具函数
  const generateId = () => {
    return 'canvas_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  }

  // 导出画布数据
  const exportCanvasData = () => {
    return JSON.parse(JSON.stringify(canvasData.value))
  }

  // 导入画布数据
  const importCanvasData = (data: CanvasData) => {
    canvasData.value = data
    clearSelection()
    resetViewport()
  }

  // 清空画布
  const clearCanvas = () => {
    canvasData.value.elements = []
    clearSelection()
    canvasData.value.updatedAt = new Date()
  }

  // 更新选中元素的样式和属性
  const updateSelectedElementsStyle = (updates: Record<string, any>) => {
    selectedElements.value.forEach(element => {
      // 分离样式属性和基本属性
      const { style, ...basicUpdates } = updates
      
      // 更新基本属性
      Object.assign(element, basicUpdates)
      
      // 更新样式属性
      if (style) {
        if (!element.style) {
          element.style = {}
        }
        Object.assign(element.style, style)
      }
      
      // 处理直接的样式属性（向后兼容）
      const styleProps = ['fill', 'stroke', 'strokeWidth', 'opacity', 'rotation', 'fontSize', 'fontFamily', 'fontStyle', 'textDecoration']
      const directStyleUpdates: Record<string, any> = {}
      
      styleProps.forEach(prop => {
        if (updates[prop] !== undefined) {
          directStyleUpdates[prop] = updates[prop]
        }
      })
      
      if (Object.keys(directStyleUpdates).length > 0) {
        if (!element.style) {
          element.style = {}
        }
        Object.assign(element.style, directStyleUpdates)
      }
    })
    canvasData.value.updatedAt = new Date()
  }

  // 剪贴板相关
  let clipboard: CanvasElement[] = []
  let copiedStyle: any = null

  const copyElements = (elements: CanvasElement[]) => {
    clipboard = elements.map(el => ({ ...el }))
  }

  const pasteElements = () => {
    if (clipboard.length === 0) return []
    
    const pastedIds: string[] = []
    clipboard.forEach(element => {
      const newElement = {
        ...element,
        x: element.x + 20,
        y: element.y + 20,
      }
      const id = addElement(newElement)
      if (id) pastedIds.push(id)
    })
    
    // 选中粘贴的元素
    selection.value.selectedIds = pastedIds
    selection.value.isMultiSelect = pastedIds.length > 1
    updateSelectionBounds()
    
    return pastedIds
  }

  const duplicateElements = (elements: CanvasElement[]) => {
    const duplicatedIds: string[] = []
    elements.forEach(element => {
      const id = duplicateElement(element.id)
      if (id) duplicatedIds.push(id)
    })
    
    // 选中复制的元素
    selection.value.selectedIds = duplicatedIds
    selection.value.isMultiSelect = duplicatedIds.length > 1
    updateSelectionBounds()
    
    return duplicatedIds
  }

  const deleteElements = (ids: string[]) => {
    ids.forEach(id => removeElement(id))
  }

  // 层级操作
  const bringElementForward = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (!element) return
    
    const sortedElements = [...canvasData.value.elements].sort((a, b) => a.zIndex - b.zIndex)
    const currentIndex = sortedElements.findIndex(el => el.id === id)
    
    if (currentIndex < sortedElements.length - 1) {
      const nextElement = sortedElements[currentIndex + 1]
      const temp = element.zIndex
      element.zIndex = nextElement.zIndex
      nextElement.zIndex = temp
    }
    
    canvasData.value.updatedAt = new Date()
  }

  const sendElementBackward = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (!element) return
    
    const sortedElements = [...canvasData.value.elements].sort((a, b) => a.zIndex - b.zIndex)
    const currentIndex = sortedElements.findIndex(el => el.id === id)
    
    if (currentIndex > 0) {
      const prevElement = sortedElements[currentIndex - 1]
      const temp = element.zIndex
      element.zIndex = prevElement.zIndex
      prevElement.zIndex = temp
    }
    
    canvasData.value.updatedAt = new Date()
  }

  const bringElementToFront = (id: string) => {
    bringToFront(id)
  }

  const sendElementToBack = (id: string) => {
    sendToBack(id)
  }

  // 样式复制
  const copyStyle = (element: CanvasElement) => {
    copiedStyle = element.style ? { ...element.style } : null
  }

  const pasteStyle = (ids: string[]) => {
    if (!copiedStyle) return
    
    ids.forEach(id => {
      const element = canvasData.value.elements.find(el => el.id === id)
      if (element) {
        if (!element.style) {
          element.style = {}
        }
        Object.assign(element.style, copiedStyle)
      }
    })
    
    canvasData.value.updatedAt = new Date()
  }

  // 翻转操作
  const flipElement = (id: string, direction: 'horizontal' | 'vertical') => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (!element) return
    
    if (!element.style) {
      element.style = {}
    }
    
    if (direction === 'horizontal') {
      element.style.scaleX = (element.style.scaleX || 1) * -1
    } else {
      element.style.scaleY = (element.style.scaleY || 1) * -1
    }
    
    canvasData.value.updatedAt = new Date()
  }

  // 锁定操作
  const toggleElementLock = (id: string) => {
    const element = canvasData.value.elements.find(el => el.id === id)
    if (element) {
      element.locked = !element.locked
      canvasData.value.updatedAt = new Date()
    }
  }

  return {
    // 状态
    canvasData,
    viewport,
    selection,
    config,
    
    // 计算属性
    selectedElements,
    hasSelection,
    isMultiSelection,
    
    // 方法
    addElement,
    removeElement,
    updateElement,
    updateElementSilent,
    batchUpdateElements,
    duplicateElement,
    selectElement,
    deselectElement,
    clearSelection,
    selectAll,
    updateSelectionBounds,
    setViewport,
    setZoom,
    resetViewport,
    setCanvasSize,
    setBackground,
    bringToFront,
    sendToBack,
    exportCanvasData,
    importCanvasData,
    clearCanvas,
    updateSelectedElementsStyle,
    
    // 新增的菜单功能方法
    copyElements,
    pasteElements,
    duplicateElements,
    deleteElements,
    bringElementForward,
    sendElementBackward,
    bringElementToFront,
    sendElementToBack,
    copyStyle,
    pasteStyle,
    flipElement,
    toggleElementLock
  }
}) 