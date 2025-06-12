import type { CanvasData } from '../types/canvas'

/**
 * 导出为PNG格式
 */
export const exportToPNG = (canvasData: CanvasData, options?: ExportOptions): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    try {
      const canvas = createCanvasFromData(canvasData, options)
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('Failed to create PNG blob'))
        }
      }, 'image/png')
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * 导出为SVG格式
 */
export const exportToSVG = (canvasData: CanvasData, options?: ExportOptions): string => {
  const { width, height } = getExportDimensions(canvasData, options)
  
  let svgContent = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`
  
  // 添加背景
  if (canvasData.background?.type === 'color') {
    svgContent += `<rect width="100%" height="100%" fill="${canvasData.background.value}"/>`
  }
  
  // 添加元素
  canvasData.elements
    .filter(element => element.visible)
    .sort((a, b) => a.zIndex - b.zIndex)
    .forEach(element => {
      svgContent += elementToSVG(element)
    })
  
  svgContent += '</svg>'
  return svgContent
}

/**
 * 导出为PDF格式
 */
export const exportToPDF = async (canvasData: CanvasData, options?: ExportOptions): Promise<Blob> => {
  // 这里需要使用第三方库如 jsPDF
  // 目前返回一个placeholder
  const svgString = exportToSVG(canvasData, options)
  const blob = new Blob([svgString], { type: 'image/svg+xml' })
  return blob
}

/**
 * 下载文件
 */
export const downloadFile = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 导出选项接口
 */
export interface ExportOptions {
  width?: number
  height?: number
  scale?: number
  quality?: number
  backgroundColor?: string
  includeBackground?: boolean
}

/**
 * 获取导出尺寸
 */
const getExportDimensions = (canvasData: CanvasData, options?: ExportOptions) => {
  const scale = options?.scale || 1
  return {
    width: (options?.width || canvasData.width) * scale,
    height: (options?.height || canvasData.height) * scale
  }
}

/**
 * 从画布数据创建Canvas元素
 */
const createCanvasFromData = (canvasData: CanvasData, options?: ExportOptions): HTMLCanvasElement => {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  const { width, height } = getExportDimensions(canvasData, options)
  
  canvas.width = width
  canvas.height = height
  
  // 设置背景
  if (options?.includeBackground !== false && canvasData.background?.type === 'color') {
    ctx.fillStyle = canvasData.background.value
    ctx.fillRect(0, 0, width, height)
  }
  
  // 渲染元素（这里需要具体的渲染逻辑）
  // 暂时留空，实际项目中需要根据元素类型进行具体渲染
  
  return canvas
}

/**
 * 将元素转换为SVG字符串
 */
const elementToSVG = (element: any): string => {
  const { x, y, width, height, style, type, data } = element
  
  switch (type) {
    case 'rectangle':
      return `<rect x="${x}" y="${y}" width="${width}" height="${height}" 
               fill="${style.fill || '#ffffff'}" 
               stroke="${style.stroke || '#000000'}" 
               stroke-width="${style.strokeWidth || 1}" 
               opacity="${style.opacity || 1}"/>`
    
    case 'circle':
      const r = Math.min(width, height) / 2
      const cx = x + width / 2
      const cy = y + height / 2
      return `<circle cx="${cx}" cy="${cy}" r="${r}" 
               fill="${style.fill || '#ffffff'}" 
               stroke="${style.stroke || '#000000'}" 
               stroke-width="${style.strokeWidth || 1}" 
               opacity="${style.opacity || 1}"/>`
    
    case 'ellipse':
      const rx = width / 2
      const ry = height / 2
      const centerX = x + width / 2
      const centerY = y + height / 2
      return `<ellipse cx="${centerX}" cy="${centerY}" rx="${rx}" ry="${ry}" 
               fill="${style.fill || '#ffffff'}" 
               stroke="${style.stroke || '#000000'}" 
               stroke-width="${style.strokeWidth || 1}" 
               opacity="${style.opacity || 1}"/>`
    
    case 'text':
      return `<text x="${x}" y="${y + (style.fontSize || 16)}" 
               font-size="${style.fontSize || 16}" 
               font-family="${style.fontFamily || 'Arial'}" 
               fill="${style.stroke || '#000000'}" 
               opacity="${style.opacity || 1}">
               ${data?.text || ''}
               </text>`
    
    case 'line':
      return `<line x1="${x}" y1="${y}" x2="${x + width}" y2="${y + height}" 
               stroke="${style.stroke || '#000000'}" 
               stroke-width="${style.strokeWidth || 1}" 
               opacity="${style.opacity || 1}"/>`
    
    default:
      return ''
  }
} 