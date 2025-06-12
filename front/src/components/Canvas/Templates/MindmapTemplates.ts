import type { CanvasElement } from '../types/canvas'
import { ElementType } from '../types/canvas'

export interface MindmapTemplate {
  id: string
  name: string
  description: string
  category: 'basic' | 'business' | 'creative'
  elements: CanvasElement[]
  thumbnail?: string
}

export const mindmapTemplates: MindmapTemplate[] = [
  {
    id: 'basic-mindmap',
    name: '基础思维导图',
    description: '简单的中心主题思维导图',
    category: 'basic',
    elements: [
      {
        id: 'center',
        type: ElementType.ELLIPSE,
        x: 300,
        y: 200,
        width: 150,
        height: 80,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#fff2e8',
          stroke: '#fa8c16',
          strokeWidth: 3,
          opacity: 1,
          fontSize: 18,
          fontWeight: 'bold'
        },
        data: { text: '中心主题' }
      },
      {
        id: 'branch1',
        type: ElementType.RECTANGLE,
        x: 100,
        y: 100,
        width: 120,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#e6f7ff',
          stroke: '#1890ff',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '分支 1' }
      },
      {
        id: 'branch2',
        type: ElementType.RECTANGLE,
        x: 100,
        y: 300,
        width: 120,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#f6ffed',
          stroke: '#52c41a',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '分支 2' }
      },
      {
        id: 'branch3',
        type: ElementType.RECTANGLE,
        x: 550,
        y: 100,
        width: 120,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#fff1f0',
          stroke: '#ff4d4f',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '分支 3' }
      },
      {
        id: 'branch4',
        type: ElementType.RECTANGLE,
        x: 550,
        y: 300,
        width: 120,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#f9f0ff',
          stroke: '#722ed1',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '分支 4' }
      }
    ]
  }
]

export const getMindmapTemplateById = (id: string): MindmapTemplate | undefined => {
  return mindmapTemplates.find(template => template.id === id)
}

export const getMindmapTemplatesByCategory = (category: string): MindmapTemplate[] => {
  return mindmapTemplates.filter(template => template.category === category)
} 