import { ElementType } from './canvas'

/**
 * 基础元素接口
 */
export interface BaseElement {
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
}

/**
 * 形状元素数据
 */
export interface ShapeElementData {
  cornerRadius?: number // 圆角半径（矩形专用）
  points?: string // 多边形点坐标
}

/**
 * 文本元素数据
 */
export interface TextElementData {
  text: string
  placeholder?: string
  autoSize?: boolean
  maxWidth?: number
  lineHeight?: number
}

/**
 * 图片元素数据
 */
export interface ImageElementData {
  src: string
  originalWidth?: number
  originalHeight?: number
  maintainAspectRatio?: boolean
  crop?: {
    x: number
    y: number
    width: number
    height: number
  }
}

/**
 * 路径元素数据
 */
export interface PathElementData {
  path: string // SVG路径字符串
  strokeLinecap?: 'butt' | 'round' | 'square'
  strokeLinejoin?: 'miter' | 'round' | 'bevel'
}

/**
 * 连接线元素数据
 */
export interface ConnectorElementData {
  startElementId?: string
  endElementId?: string
  startPoint: { x: number; y: number }
  endPoint: { x: number; y: number }
  controlPoints?: { x: number; y: number }[]
  lineType: 'straight' | 'curved' | 'orthogonal'
  arrowStart?: boolean
  arrowEnd?: boolean
}

/**
 * 组合元素数据
 */
export interface GroupElementData {
  childIds: string[]
  expanded?: boolean
}

/**
 * 元素联合类型
 */
export type ElementData = 
  | ShapeElementData
  | TextElementData
  | ImageElementData
  | PathElementData
  | ConnectorElementData
  | GroupElementData
  | Record<string, any>

/**
 * 元素样式扩展
 */
export interface ExtendedElementStyle {
  // 边框样式
  borderStyle?: 'solid' | 'dashed' | 'dotted'
  borderRadius?: number
  
  // 阴影效果
  shadowColor?: string
  shadowBlur?: number
  shadowOffsetX?: number
  shadowOffsetY?: number
  
  // 渐变填充
  gradientType?: 'linear' | 'radial'
  gradientStops?: Array<{
    offset: number
    color: string
  }>
  gradientDirection?: number // 角度
  
  // 文本样式
  fontStyle?: 'normal' | 'italic'
  fontWeight?: 'normal' | 'bold' | number
  textDecoration?: 'none' | 'underline' | 'overline' | 'line-through'
  letterSpacing?: number
  lineHeight?: number
  
  // 动画相关
  animationType?: 'none' | 'fade' | 'slide' | 'bounce'
  animationDuration?: number
  animationDelay?: number
}

/**
 * 元素变换状态
 */
export interface ElementTransform {
  x: number
  y: number
  scaleX: number
  scaleY: number
  rotation: number
  skewX: number
  skewY: number
}

/**
 * 元素选择状态
 */
export interface ElementSelection {
  id: string
  isSelected: boolean
  isHovered: boolean
  isFocused: boolean
  handles: Array<{
    type: 'resize' | 'rotate' | 'move'
    position: { x: number; y: number }
    cursor: string
  }>
}

/**
 * 元素事件数据
 */
export interface ElementEvent {
  type: 'click' | 'doubleclick' | 'mouseenter' | 'mouseleave' | 'drag' | 'resize' | 'rotate'
  elementId: string
  target: BaseElement
  originalEvent: Event
  position: { x: number; y: number }
  delta?: { x: number; y: number }
}

/**
 * 元素操作历史
 */
export interface ElementOperation {
  type: 'create' | 'update' | 'delete' | 'move' | 'resize' | 'rotate'
  elementId: string
  oldData?: any
  newData?: any
  timestamp: number
} 