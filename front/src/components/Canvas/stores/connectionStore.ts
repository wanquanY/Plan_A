import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useCanvasStore } from './canvasStore'
import { ElementType } from '../types/canvas'
import type { Connection, AnchorPosition, ConnectionStyle } from '../utils/connectionUtils'
import { 
  calculateBestAnchorPoints,
  calculateConnectionPath,
  canConnect,
  generateConnectionId,
  getElementAnchorPoints
} from '../utils/connectionUtils'

export const useConnectionStore = defineStore('connection', () => {
  const canvasStore = useCanvasStore()
  
  // 连接数据
  const connections = ref<Connection[]>([])
  
  // 临时连接状态（拖拽时）
  const tempConnection = ref<{
    fromElementId: string
    fromAnchor: AnchorPosition
    currentPoint: { x: number, y: number }
    isActive: boolean
  } | null>(null)
  
  // 计算属性
  const getConnectionsByElementId = computed(() => {
    return (elementId: string) => {
      return connections.value.filter(conn => 
        conn.fromElementId === elementId || conn.toElementId === elementId
      )
    }
  })
  
  // 方法
  const startConnection = (elementId: string, anchor: AnchorPosition) => {
    const element = canvasStore.canvasData.elements.find(el => el.id === elementId)
    if (!element) return
    
    const anchorPoints = getElementAnchorPoints(element)
    const startPoint = anchorPoints[anchor]
    
    tempConnection.value = {
      fromElementId: elementId,
      fromAnchor: anchor,
      currentPoint: startPoint,
      isActive: true
    }
  }
  
  const updateTempConnection = (point: { x: number, y: number }) => {
    if (tempConnection.value) {
      tempConnection.value.currentPoint = point
    }
  }
  
  const endConnection = (targetElementId?: string): boolean => {
    if (!tempConnection.value) return false
    
    const fromElement = canvasStore.canvasData.elements.find(
      el => el.id === tempConnection.value!.fromElementId
    )
    
    if (!fromElement) {
      tempConnection.value = null
      return false
    }
    
    // 如果有目标元素，创建连接
    if (targetElementId) {
      const toElement = canvasStore.canvasData.elements.find(el => el.id === targetElementId)
      
      if (toElement && canConnect(fromElement, toElement)) {
        createConnection(
          tempConnection.value.fromElementId,
          targetElementId,
          tempConnection.value.fromAnchor
        )
        tempConnection.value = null
        return true
      }
    } else {
      // 创建新元素并连接
      const newElementId = createNewElementAtPoint(tempConnection.value.currentPoint)
      if (newElementId) {
        createConnection(
          tempConnection.value.fromElementId,
          newElementId,
          tempConnection.value.fromAnchor
        )
        tempConnection.value = null
        return true
      }
    }
    
    tempConnection.value = null
    return false
  }
  
  const createConnection = (
    fromElementId: string, 
    toElementId: string, 
    fromAnchor?: AnchorPosition
  ) => {
    const fromElement = canvasStore.canvasData.elements.find(el => el.id === fromElementId)
    const toElement = canvasStore.canvasData.elements.find(el => el.id === toElementId)
    
    if (!fromElement || !toElement || !canConnect(fromElement, toElement)) {
      return null
    }
    
    // 检查是否已存在连接
    const existingConnection = connections.value.find(conn =>
      (conn.fromElementId === fromElementId && conn.toElementId === toElementId) ||
      (conn.fromElementId === toElementId && conn.toElementId === fromElementId)
    )
    
    if (existingConnection) {
      return null
    }
    
    // 计算最佳锚点
    const anchors = fromAnchor 
      ? { from: fromAnchor, to: calculateBestAnchorPoints(fromElement, toElement).to }
      : calculateBestAnchorPoints(fromElement, toElement)
    
    const connection: Connection = {
      id: generateConnectionId(),
      fromElementId,
      toElementId,
      fromAnchor: anchors.from,
      toAnchor: anchors.to,
      style: {
        stroke: '#666666',
        strokeWidth: 2,
        arrowType: 'end'
      }
    }
    
    connections.value.push(connection)
    
    // 将连接信息作为连接线元素添加到画布
    addConnectionAsElement(connection)
    
    return connection.id
  }
  
  const removeConnection = (connectionId: string) => {
    const index = connections.value.findIndex(conn => conn.id === connectionId)
    if (index !== -1) {
      const connection = connections.value[index]
      connections.value.splice(index, 1)
      
      // 从画布中移除对应的连接线元素
      removeConnectionElement(connection)
    }
  }
  
  const updateConnection = (connectionId: string, updates: Partial<Connection>) => {
    const connection = connections.value.find(conn => conn.id === connectionId)
    if (connection) {
      Object.assign(connection, updates)
      updateConnectionElement(connection)
    }
  }
  
  // 当元素移动时更新相关连接
  const updateConnectionsForElement = (elementId: string) => {
    const relatedConnections = getConnectionsByElementId.value(elementId)
    relatedConnections.forEach(connection => {
      updateConnectionElement(connection)
    })
  }
  
  // 当元素删除时清理相关连接
  const removeConnectionsForElement = (elementId: string) => {
    const relatedConnections = getConnectionsByElementId.value(elementId)
    relatedConnections.forEach(connection => {
      removeConnection(connection.id)
    })
  }
  
  // 将连接添加为画布元素
  const addConnectionAsElement = (connection: Connection) => {
    const fromElement = canvasStore.canvasData.elements.find(el => el.id === connection.fromElementId)
    const toElement = canvasStore.canvasData.elements.find(el => el.id === connection.toElementId)
    
    if (!fromElement || !toElement) return
    
    const path = calculateConnectionPath(
      fromElement, 
      toElement, 
      connection.fromAnchor, 
      connection.toAnchor
    )
    
    canvasStore.addElement({
      type: ElementType.PATH,
      x: 0,
      y: 0,
      width: 0,
      height: 0,
      rotation: 0,
      zIndex: -1, // 连接线在元素下方
      locked: false,
      visible: true,
      style: {
        stroke: connection.style.stroke,
        strokeWidth: connection.style.strokeWidth,
        fill: 'none'
      },
      data: {
        path,
        connectionId: connection.id,
        isConnection: true
      }
    })
  }
  
  // 更新连接线元素
  const updateConnectionElement = (connection: Connection) => {
    const fromElement = canvasStore.canvasData.elements.find(el => el.id === connection.fromElementId)
    const toElement = canvasStore.canvasData.elements.find(el => el.id === connection.toElementId)
    const connectionElement = canvasStore.canvasData.elements.find(
      el => el.data?.connectionId === connection.id
    )
    
    if (!fromElement || !toElement || !connectionElement) return
    
    const path = calculateConnectionPath(
      fromElement, 
      toElement, 
      connection.fromAnchor, 
      connection.toAnchor
    )
    
    canvasStore.updateElement(connectionElement.id, {
      data: {
        ...connectionElement.data,
        path
      },
      style: {
        ...connectionElement.style,
        stroke: connection.style.stroke,
        strokeWidth: connection.style.strokeWidth
      }
    })
  }
  
  // 移除连接线元素
  const removeConnectionElement = (connection: Connection) => {
    const connectionElement = canvasStore.canvasData.elements.find(
      el => el.data?.connectionId === connection.id
    )
    
    if (connectionElement) {
      canvasStore.removeElement(connectionElement.id)
    }
  }
  
  // 创建新元素在指定位置
  const createNewElementAtPoint = (point: { x: number, y: number }): string | null => {
    return canvasStore.addElement({
      type: ElementType.RECTANGLE,
      x: point.x - 50,
      y: point.y - 30,
      width: 100,
      height: 60,
      rotation: 0,
      zIndex: 0,
      locked: false,
      visible: true,
      style: {
        fill: 'rgba(135, 206, 235, 0.8)',
        stroke: '#87CEEB',
        strokeWidth: 2
      },
      data: {}
    })
  }
  
  const cancelTempConnection = () => {
    tempConnection.value = null
  }
  
  return {
    connections,
    tempConnection,
    getConnectionsByElementId,
    startConnection,
    updateTempConnection,
    endConnection,
    createConnection,
    removeConnection,
    updateConnection,
    updateConnectionsForElement,
    removeConnectionsForElement,
    cancelTempConnection
  }
}) 