import { flowchartTemplates, type FlowchartTemplate } from '../Templates/FlowchartTemplates'
import { mindmapTemplates, type MindmapTemplate } from '../Templates/MindmapTemplates'
import { commonShapes, type ShapeTemplate } from '../Templates/CommonShapes'
import type { CanvasElement } from '../types/canvas'
import { generateId } from './canvasUtils'

export type Template = FlowchartTemplate | MindmapTemplate
export type TemplateType = 'flowchart' | 'mindmap' | 'shape'

/**
 * 获取所有模板
 */
export const getAllTemplates = (): Template[] => {
  return [...flowchartTemplates, ...mindmapTemplates]
}

/**
 * 根据类型获取模板
 */
export const getTemplatesByType = (type: TemplateType): Template[] => {
  switch (type) {
    case 'flowchart':
      return flowchartTemplates
    case 'mindmap':
      return mindmapTemplates
    default:
      return []
  }
}

/**
 * 根据ID获取模板
 */
export const getTemplateById = (id: string): Template | undefined => {
  return getAllTemplates().find(template => template.id === id)
}

/**
 * 获取常用形状
 */
export const getCommonShapes = (): ShapeTemplate[] => {
  return commonShapes
}

/**
 * 根据形状ID获取形状模板
 */
export const getShapeById = (id: string): ShapeTemplate | undefined => {
  return commonShapes.find(shape => shape.id === id)
}

/**
 * 应用模板到画布
 */
export const applyTemplate = (template: Template, position?: { x: number; y: number }): CanvasElement[] => {
  const offset = position || { x: 0, y: 0 }
  
  return template.elements.map(element => ({
    ...element,
    id: generateId(),
    x: element.x + offset.x,
    y: element.y + offset.y,
    style: { ...element.style },
    data: element.data ? { ...element.data } : null
  }))
}

/**
 * 创建形状元素
 */
export const createShapeElement = (
  shapeTemplate: ShapeTemplate, 
  position: { x: number; y: number }
): CanvasElement => {
  return {
    id: generateId(),
    x: position.x,
    y: position.y,
    rotation: 0,
    zIndex: 1,
    locked: false,
    visible: true,
    ...shapeTemplate.element,
    style: { ...shapeTemplate.element.style }
  } as CanvasElement
}

/**
 * 模板搜索
 */
export const searchTemplates = (keyword: string): Template[] => {
  const lowerKeyword = keyword.toLowerCase()
  return getAllTemplates().filter(template => 
    template.name.toLowerCase().includes(lowerKeyword) ||
    template.description.toLowerCase().includes(lowerKeyword)
  )
}

/**
 * 根据分类获取模板
 */
export const getTemplatesByCategory = (category: string): Template[] => {
  return getAllTemplates().filter(template => template.category === category)
}

/**
 * 获取所有模板分类
 */
export const getTemplateCategories = (): string[] => {
  const categories = new Set<string>()
  getAllTemplates().forEach(template => {
    categories.add(template.category)
  })
  return Array.from(categories)
}

/**
 * 验证模板数据
 */
export const validateTemplate = (template: any): boolean => {
  return !!(
    template.id &&
    template.name &&
    template.elements &&
    Array.isArray(template.elements) &&
    template.elements.length > 0
  )
}

/**
 * 保存自定义模板
 */
export const saveCustomTemplate = (
  name: string,
  description: string,
  elements: CanvasElement[],
  category: string = 'custom'
): Template => {
  const template: Template = {
    id: generateId(),
    name,
    description,
    category: category as any,
    elements: elements.map(element => ({
      ...element,
      id: generateId()
    }))
  }
  
  // 这里可以保存到本地存储或发送到服务器
  // localStorage.setItem(`custom-template-${template.id}`, JSON.stringify(template))
  
  return template
} 