import type { CanvasElement } from '../types/canvas'
import { ElementType } from '../types/canvas'

export interface FlowchartTemplate {
  id: string
  name: string
  description: string
  category: 'basic' | 'business' | 'system'
  elements: CanvasElement[]
  thumbnail?: string
}

export const flowchartTemplates: FlowchartTemplate[] = [
  {
    id: 'basic-process',
    name: '基础流程',
    description: '简单的开始-处理-结束流程',
    category: 'basic',
    elements: [
      {
        id: '1',
        type: ElementType.ELLIPSE,
        x: 100,
        y: 50,
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
        data: { text: '开始' }
      },
      {
        id: '2',
        type: ElementType.RECTANGLE,
        x: 100,
        y: 150,
        width: 120,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#fff2e8',
          stroke: '#fa8c16',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '处理步骤' }
      },
      {
        id: '3',
        type: ElementType.ELLIPSE,
        x: 100,
        y: 250,
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
        data: { text: '结束' }
      }
    ]
  },
  {
    id: 'decision-flow',
    name: '决策流程',
    description: '包含决策节点的流程图',
    category: 'business',
    elements: [
      {
        id: '1',
        type: ElementType.ELLIPSE,
        x: 200,
        y: 50,
        width: 100,
        height: 50,
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
        data: { text: '开始' }
      },
      {
        id: '2',
        type: ElementType.RECTANGLE,
        x: 175,
        y: 150,
        width: 150,
        height: 60,
        rotation: 0,
        zIndex: 1,
        locked: false,
        visible: true,
        style: {
          fill: '#fff2e8',
          stroke: '#fa8c16',
          strokeWidth: 2,
          opacity: 1
        },
        data: { text: '输入数据' }
      },
      {
        id: '3',
        type: ElementType.TRIANGLE,
        x: 200,
        y: 250,
        width: 100,
        height: 80,
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
        data: { text: '是否有效?' }
      }
    ]
  }
]

export const getFlowchartTemplateById = (id: string): FlowchartTemplate | undefined => {
  return flowchartTemplates.find(template => template.id === id)
}

export const getFlowchartTemplatesByCategory = (category: string): FlowchartTemplate[] => {
  return flowchartTemplates.filter(template => template.category === category)
} 