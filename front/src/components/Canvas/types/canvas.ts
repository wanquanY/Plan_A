// 画布相关类型定义

export interface CanvasData {
  id: string
  name: string
  width: number
  height: number
  zoom: number
  elements: CanvasElement[]
  background: BackgroundConfig
  createdAt: Date
  updatedAt: Date
}

export interface CanvasElement {
  id: string
  type: ElementType
  x: number
  y: number
  width: number
  height: number
  rotation: number
  zIndex: number
  locked: boolean
  visible: boolean
  style: ElementStyle
  data: any // 元素特定数据
}

export interface BackgroundConfig {
  type: 'color' | 'image' | 'pattern'
  value: string
  opacity: number
}

export interface ElementStyle {
  fill?: string
  stroke?: string
  strokeWidth?: number
  strokeDashArray?: number[]
  opacity?: number
  fontFamily?: string
  fontSize?: number
  fontWeight?: string | number
  fontStyle?: 'normal' | 'italic'
  textDecoration?: 'none' | 'underline' | 'overline' | 'line-through'
  textAlign?: 'left' | 'center' | 'right'
  textVerticalAlign?: 'top' | 'middle' | 'bottom'
  scaleX?: number
  scaleY?: number
}

export enum ElementType {
  RECTANGLE = 'rectangle',
  CIRCLE = 'circle',
  ELLIPSE = 'ellipse',
  TRIANGLE = 'triangle',
  POLYGON = 'polygon',
  LINE = 'line',
  ARROW = 'arrow',
  CONNECTOR = 'connector',
  TEXT = 'text',
  IMAGE = 'image',
  GROUP = 'group',
  PATH = 'path'
}

export interface ViewportState {
  x: number
  y: number
  zoom: number
  rotation: number
}

export interface CanvasConfig {
  width: number
  height: number
  background: BackgroundConfig
  grid: GridConfig
  snap: SnapConfig
}

export interface GridConfig {
  enabled: boolean
  size: number
  color: string
  opacity: number
}

export interface SnapConfig {
  enabled: boolean
  threshold: number
  snapToGrid: boolean
  snapToElements: boolean
}

export interface SelectionState {
  selectedIds: string[]
  isMultiSelect: boolean
  selectionBounds?: BoundingBox
}

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface CanvasHistory {
  index: number
  states: CanvasData[]
  maxStates: number
}

export interface Point {
  x: number
  y: number
}

export interface Size {
  width: number
  height: number
} 