import type { CanvasElement, Point, Size, BoundingBox } from '../types/canvas'

/**
 * 生成唯一ID
 */
export const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

/**
 * 计算元素的包围盒
 */
export const getElementBounds = (element: CanvasElement): BoundingBox => {
  return {
    x: element.x,
    y: element.y,
    width: element.width,
    height: element.height
  }
}

/**
 * 计算多个元素的包围盒
 */
export const getMultiElementBounds = (elements: CanvasElement[]): BoundingBox | null => {
  if (elements.length === 0) return null
  
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
  
  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY
  }
}

/**
 * 检查点是否在元素内
 */
export const isPointInElement = (point: Point, element: CanvasElement): boolean => {
  return point.x >= element.x &&
         point.x <= element.x + element.width &&
         point.y >= element.y &&
         point.y <= element.y + element.height
}

/**
 * 检查两个矩形是否相交
 */
export const isRectIntersect = (rect1: BoundingBox, rect2: BoundingBox): boolean => {
  return !(rect1.x + rect1.width < rect2.x ||
           rect2.x + rect2.width < rect1.x ||
           rect1.y + rect1.height < rect2.y ||
           rect2.y + rect2.height < rect1.y)
}

/**
 * 计算两点之间的距离
 */
export const getDistance = (point1: Point, point2: Point): number => {
  const dx = point1.x - point2.x
  const dy = point1.y - point2.y
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * 计算角度（弧度）
 */
export const getAngle = (point1: Point, point2: Point): number => {
  return Math.atan2(point2.y - point1.y, point2.x - point1.x)
}

/**
 * 旋转点
 */
export const rotatePoint = (point: Point, center: Point, angle: number): Point => {
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const dx = point.x - center.x
  const dy = point.y - center.y
  
  return {
    x: center.x + dx * cos - dy * sin,
    y: center.y + dx * sin + dy * cos
  }
}

/**
 * 限制值在指定范围内
 */
export const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max)
}

/**
 * 网格对齐
 */
export const snapToGrid = (value: number, gridSize: number): number => {
  return Math.round(value / gridSize) * gridSize
}

/**
 * 复制元素
 */
export const cloneElement = (element: CanvasElement): CanvasElement => {
  return {
    ...element,
    id: generateId(),
    x: element.x + 20,
    y: element.y + 20,
    style: { ...element.style },
    data: element.data ? { ...element.data } : null
  }
}

/**
 * 深拷贝对象
 */
export const deepClone = <T>(obj: T): T => {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as unknown as T
  if (typeof obj === 'object') {
    const clonedObj = {} as { [key: string]: any }
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj as T
  }
  return obj
} 