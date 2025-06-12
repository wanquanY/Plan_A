import type { CanvasElement } from '../types/canvas'
import { ElementType } from '../types/canvas'

export interface ShapeTemplate {
  id: string
  name: string
  description: string
  category: 'basic' | 'arrow' | 'special'
  element: Partial<CanvasElement>
}

export const commonShapes: ShapeTemplate[] = [
  {
    id: 'rectangle',
    name: '矩形',
    description: '基础矩形形状',
    category: 'basic',
    element: {
      type: ElementType.RECTANGLE,
      width: 120,
      height: 80,
      style: {
        fill: '#ffffff',
        stroke: '#000000',
        strokeWidth: 1,
        opacity: 1
      }
    }
  },
  {
    id: 'circle',
    name: '圆形',
    description: '基础圆形形状',
    category: 'basic',
    element: {
      type: ElementType.CIRCLE,
      width: 100,
      height: 100,
      style: {
        fill: '#ffffff',
        stroke: '#000000',
        strokeWidth: 1,
        opacity: 1
      }
    }
  },
  {
    id: 'ellipse',
    name: '椭圆',
    description: '基础椭圆形状',
    category: 'basic',
    element: {
      type: ElementType.ELLIPSE,
      width: 140,
      height: 80,
      style: {
        fill: '#ffffff',
        stroke: '#000000',
        strokeWidth: 1,
        opacity: 1
      }
    }
  },
  {
    id: 'triangle',
    name: '三角形',
    description: '基础三角形形状',
    category: 'basic',
    element: {
      type: ElementType.TRIANGLE,
      width: 100,
      height: 100,
      style: {
        fill: '#ffffff',
        stroke: '#000000',
        strokeWidth: 1,
        opacity: 1
      }
    }
  },
  {
    id: 'line',
    name: '直线',
    description: '基础直线',
    category: 'arrow',
    element: {
      type: ElementType.LINE,
      width: 100,
      height: 0,
      style: {
        stroke: '#000000',
        strokeWidth: 2,
        opacity: 1
      }
    }
  },
  {
    id: 'arrow',
    name: '箭头',
    description: '带箭头的直线',
    category: 'arrow',
    element: {
      type: ElementType.ARROW,
      width: 100,
      height: 0,
      style: {
        stroke: '#000000',
        strokeWidth: 2,
        opacity: 1
      }
    }
  }
]

export const getShapeTemplateById = (id: string): ShapeTemplate | undefined => {
  return commonShapes.find(shape => shape.id === id)
}

export const getShapeTemplatesByCategory = (category: string): ShapeTemplate[] => {
  return commonShapes.filter(shape => shape.category === category)
} 