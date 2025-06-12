// 连接管理工具类
import type { CanvasElement, Point } from '../types/canvas'

export interface Connection {
  id: string
  fromElementId: string
  toElementId: string
  fromAnchor: AnchorPosition
  toAnchor: AnchorPosition
  style: ConnectionStyle
}

export interface ConnectionStyle {
  stroke: string
  strokeWidth: number
  dashArray?: number[]
  arrowType: 'none' | 'end' | 'start' | 'both'
}

export type AnchorPosition = 'top' | 'right' | 'bottom' | 'left' | 'center'

export interface AnchorPoint {
  position: AnchorPosition
  point: Point
  element: CanvasElement
}

// 计算元素的锚点
export const getElementAnchorPoints = (element: CanvasElement): Record<AnchorPosition, Point> => {
  const x = element.x
  const y = element.y
  const width = element.width
  const height = element.height
  
  return {
    top: { x: x + width / 2, y },
    right: { x: x + width, y: y + height / 2 },
    bottom: { x: x + width / 2, y: y + height },
    left: { x, y: y + height / 2 },
    center: { x: x + width / 2, y: y + height / 2 }
  }
}

// 计算两个元素之间的最佳连接锚点
export const calculateBestAnchorPoints = (
  fromElement: CanvasElement, 
  toElement: CanvasElement
): { from: AnchorPosition, to: AnchorPosition } => {
  const fromCenter = {
    x: fromElement.x + fromElement.width / 2,
    y: fromElement.y + fromElement.height / 2
  }
  const toCenter = {
    x: toElement.x + toElement.width / 2,
    y: toElement.y + toElement.height / 2
  }
  
  const deltaX = toCenter.x - fromCenter.x
  const deltaY = toCenter.y - fromCenter.y
  
  // 基于角度确定最佳连接点
  const angle = Math.atan2(deltaY, deltaX)
  const normalizedAngle = (angle + Math.PI * 2) % (Math.PI * 2)
  
  let fromAnchor: AnchorPosition
  let toAnchor: AnchorPosition
  
  if (normalizedAngle < Math.PI / 4 || normalizedAngle >= 7 * Math.PI / 4) {
    // 右方向
    fromAnchor = 'right'
    toAnchor = 'left'
  } else if (normalizedAngle < 3 * Math.PI / 4) {
    // 下方向
    fromAnchor = 'bottom'
    toAnchor = 'top'
  } else if (normalizedAngle < 5 * Math.PI / 4) {
    // 左方向
    fromAnchor = 'left'
    toAnchor = 'right'
  } else {
    // 上方向
    fromAnchor = 'top'
    toAnchor = 'bottom'
  }
  
  return { from: fromAnchor, to: toAnchor }
}

// 根据连接信息计算连接线路径
export const calculateConnectionPath = (
  fromElement: CanvasElement,
  toElement: CanvasElement,
  fromAnchor: AnchorPosition,
  toAnchor: AnchorPosition
): string => {
  const fromPoints = getElementAnchorPoints(fromElement)
  const toPoints = getElementAnchorPoints(toElement)
  
  const startPoint = fromPoints[fromAnchor]
  const endPoint = toPoints[toAnchor]
  
  // 简单的直线连接，后续可以扩展为贝塞尔曲线等
  return `M ${startPoint.x} ${startPoint.y} L ${endPoint.x} ${endPoint.y}`
}

// 计算箭头的旋转角度
export const calculateArrowRotation = (
  startPoint: Point,
  endPoint: Point
): number => {
  const deltaX = endPoint.x - startPoint.x
  const deltaY = endPoint.y - startPoint.y
  return Math.atan2(deltaY, deltaX) * 180 / Math.PI
}

// 检查两个元素是否可以连接
export const canConnect = (
  fromElement: CanvasElement,
  toElement: CanvasElement
): boolean => {
  // 基本检查：不同元素，都可见，都没有锁定
  return fromElement.id !== toElement.id &&
         fromElement.visible && toElement.visible &&
         !fromElement.locked && !toElement.locked
}

// 生成连接ID
export const generateConnectionId = (): string => {
  return 'conn_' + Math.random().toString(36).substr(2, 9)
} 