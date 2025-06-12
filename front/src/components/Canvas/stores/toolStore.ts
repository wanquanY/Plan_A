import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { 
  ToolType,
  ToolCategory,
  type Tool, 
  type ToolOptions, 
  type DrawingState,
  type ToolbarTab 
} from '../types/tools'

export const useToolStore = defineStore('tool', () => {
  // 当前工具
  const currentTool = ref<ToolType>(ToolType.SELECT)
  
  // 工具选项
  const toolOptions = ref<ToolOptions>({
    strokeWidth: 2,
    strokeColor: '#000000',
    fillColor: '#ffffff',
    fontSize: 16,
    fontFamily: 'Arial',
    opacity: 1,
    lineDash: [],
    arrowStyle: {
      start: false,
      end: true,
      size: 10
    }
  })
  
  // 绘制状态
  const drawingState = ref<DrawingState>({
    isDrawing: false,
    startPoint: null,
    currentTool: ToolType.SELECT,
    toolOptions: {}
  })
  
  // 工具定义
  const tools = ref<Tool[]>([
    {
      type: ToolType.SELECT,
      name: '选择',
      icon: 'cursor',
      cursor: 'default'
    },
    {
      type: ToolType.HAND,
      name: '拖拽',
      icon: 'drag',
      cursor: 'grab'
    },
    {
      type: ToolType.RECTANGLE,
      name: '矩形',
      icon: 'border',
      cursor: 'crosshair'
    },
    {
      type: ToolType.CIRCLE,
      name: '圆形',
      icon: 'border-radius',
      cursor: 'crosshair'
    },
    {
      type: ToolType.TRIANGLE,
      name: '三角形',
      icon: 'caret-up',
      cursor: 'crosshair'
    },
    {
      type: ToolType.LINE,
      name: '直线',
      icon: 'minus',
      cursor: 'crosshair'
    },
    {
      type: ToolType.ARROW,
      name: '箭头',
      icon: 'arrow-right',
      cursor: 'crosshair'
    },
    {
      type: ToolType.TEXT,
      name: '文本',
      icon: 'font-size',
      cursor: 'text'
    },
    {
      type: ToolType.PEN,
      name: '画笔',
      icon: 'edit',
      cursor: 'crosshair'
    },
    {
      type: ToolType.ERASER,
      name: '橡皮擦',
      icon: 'delete',
      cursor: 'crosshair'
    }
  ])
  
  // 工具栏标签页
  const toolbarTabs = ref<ToolbarTab[]>([
    {
      category: ToolCategory.BASIC,
      name: '基础',
      icon: 'appstore',
      tools: [ToolType.SELECT, ToolType.HAND]
    },
    {
      category: ToolCategory.SHAPES,
      name: '形状',
      icon: 'border',
      tools: [ToolType.RECTANGLE, ToolType.CIRCLE, ToolType.TRIANGLE]
    },
    {
      category: ToolCategory.LINES,
      name: '线条',
      icon: 'minus',
      tools: [ToolType.LINE, ToolType.ARROW]
    },
    {
      category: ToolCategory.TEXT,
      name: '文本',
      icon: 'font-size',
      tools: [ToolType.TEXT]
    },
    {
      category: ToolCategory.DRAWING,
      name: '绘制',
      icon: 'edit',
      tools: [ToolType.PEN, ToolType.ERASER]
    }
  ])
  
  const activeTab = ref<ToolCategory>(ToolCategory.BASIC)
  
  // 计算属性
  const currentToolInfo = computed(() => {
    return tools.value.find(tool => tool.type === currentTool.value)
  })
  
  const isDrawing = computed(() => {
    return drawingState.value.isDrawing
  })
  
  const activeTabTools = computed(() => {
    const tab = toolbarTabs.value.find(tab => tab.category === activeTab.value)
    return tab ? tab.tools.map(toolType => 
      tools.value.find(tool => tool.type === toolType)
    ).filter(Boolean) : []
  })
  
  // 动作方法
  const setCurrentTool = (toolType: ToolType) => {
    currentTool.value = toolType
    drawingState.value.currentTool = toolType
    
    // 根据工具类型设置默认选项
    updateToolOptionsForTool(toolType)
  }
  
  const updateToolOptionsForTool = (toolType: ToolType) => {
    switch (toolType) {
      case ToolType.PEN:
        toolOptions.value.strokeWidth = 3
        toolOptions.value.strokeColor = '#000000'
        break
      case ToolType.TEXT:
        toolOptions.value.fontSize = 16
        toolOptions.value.fontFamily = 'Arial'
        toolOptions.value.fillColor = '#000000'
        break
      case ToolType.ARROW:
        toolOptions.value.arrowStyle = {
          start: false,
          end: true,
          size: 10
        }
        break
    }
  }
  
  const setToolOptions = (options: Partial<ToolOptions>) => {
    Object.assign(toolOptions.value, options)
  }
  
  const setActiveTab = (tab: ToolCategory) => {
    activeTab.value = tab
  }
  
  const startDrawing = (point: { x: number; y: number }) => {
    drawingState.value = {
      isDrawing: true,
      startPoint: point,
      currentTool: currentTool.value,
      toolOptions: { ...toolOptions.value }
    }
  }
  
  const endDrawing = (point: { x: number; y: number }) => {
    drawingState.value.isDrawing = false
    // 保持起始点以便创建元素
  }
  
  const cancelDrawing = () => {
    drawingState.value = {
      isDrawing: false,
      startPoint: null,
      currentTool: currentTool.value,
      toolOptions: {}
    }
  }
  
  // 快捷键映射
  const keyboardShortcuts = ref<Record<string, ToolType>>({
    'v': ToolType.SELECT,
    'h': ToolType.HAND,
    'r': ToolType.RECTANGLE,
    'o': ToolType.CIRCLE,
    't': ToolType.TEXT,
    'l': ToolType.LINE,
    'p': ToolType.PEN,
    'e': ToolType.ERASER
  })
  
  const handleKeyboardShortcut = (key: string) => {
    const toolType = keyboardShortcuts.value[key.toLowerCase()]
    if (toolType) {
      setCurrentTool(toolType)
      return true
    }
    return false
  }
  
  // 工具预设
  const toolPresets = ref({
    pen: [
      { name: '细笔', strokeWidth: 1 },
      { name: '中笔', strokeWidth: 3 },
      { name: '粗笔', strokeWidth: 6 },
      { name: '超粗笔', strokeWidth: 12 }
    ],
    text: [
      { name: '小号', fontSize: 12 },
      { name: '正常', fontSize: 16 },
      { name: '大号', fontSize: 24 },
      { name: '标题', fontSize: 32 }
    ],
    stroke: [
      { name: '细线', strokeWidth: 1 },
      { name: '中线', strokeWidth: 2 },
      { name: '粗线', strokeWidth: 4 },
      { name: '超粗线', strokeWidth: 8 }
    ]
  })
  
  const applyPreset = (category: string, preset: any) => {
    Object.assign(toolOptions.value, preset)
  }
  
  // 颜色预设
  const colorPresets = ref([
    '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
    '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080',
    '#008000', '#FFC0CB', '#A52A2A', '#808080', '#000080'
  ])
  
  const setStrokeColor = (color: string) => {
    toolOptions.value.strokeColor = color
  }
  
  const setFillColor = (color: string) => {
    toolOptions.value.fillColor = color
  }
  
  // 历史记录
  const recentTools = ref<ToolType[]>([])
  const maxRecentTools = 5
  
  const addToRecentTools = (toolType: ToolType) => {
    const index = recentTools.value.indexOf(toolType)
    if (index > -1) {
      recentTools.value.splice(index, 1)
    }
    recentTools.value.unshift(toolType)
    
    if (recentTools.value.length > maxRecentTools) {
      recentTools.value.pop()
    }
  }
  
  // 监听工具切换
  watch(currentTool, (newTool) => {
    addToRecentTools(newTool)
  })
  
  return {
    // 状态
    currentTool,
    toolOptions,
    drawingState,
    tools,
    toolbarTabs,
    activeTab,
    keyboardShortcuts,
    toolPresets,
    colorPresets,
    recentTools,
    
    // 计算属性
    currentToolInfo,
    isDrawing,
    activeTabTools,
    
    // 方法
    setCurrentTool,
    setToolOptions,
    setActiveTab,
    startDrawing,
    endDrawing,
    cancelDrawing,
    handleKeyboardShortcut,
    applyPreset,
    setStrokeColor,
    setFillColor,
    addToRecentTools
  }
}) 