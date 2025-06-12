// 工具相关类型定义

export enum ToolType {
  SELECT = 'select',
  RECTANGLE = 'rectangle',
  CIRCLE = 'circle',
  TRIANGLE = 'triangle',
  LINE = 'line',
  ARROW = 'arrow',
  TEXT = 'text',
  PEN = 'pen',
  ERASER = 'eraser',
  HAND = 'hand',
  ZOOM = 'zoom'
}

export interface Tool {
  type: ToolType
  name: string
  icon: string
  cursor: string
  options?: ToolOptions
}

export interface ToolOptions {
  strokeWidth?: number
  strokeColor?: string
  fillColor?: string
  fontSize?: number
  fontFamily?: string
  opacity?: number
  lineDash?: number[]
  arrowStyle?: ArrowStyle
}

export interface ArrowStyle {
  start: boolean
  end: boolean
  size: number
}

export interface DrawingState {
  isDrawing: boolean
  startPoint: Point | null
  currentTool: ToolType
  toolOptions: ToolOptions
}

export interface SelectionTool {
  isSelecting: boolean
  selectionBox: SelectionBox | null
}

export interface SelectionBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Point {
  x: number
  y: number
}

export interface PenState {
  isDrawing: boolean
  points: Point[]
  pressure?: number[]
}

export interface EraserState {
  isErasing: boolean
  eraserSize: number
}

export interface ToolbarConfig {
  tools: Tool[]
  activeTab: ToolCategory
}

export enum ToolCategory {
  BASIC = 'basic',
  SHAPES = 'shapes',
  LINES = 'lines',
  TEXT = 'text',
  DRAWING = 'drawing'
}

export interface ToolbarTab {
  category: ToolCategory
  name: string
  icon: string
  tools: ToolType[]
} 