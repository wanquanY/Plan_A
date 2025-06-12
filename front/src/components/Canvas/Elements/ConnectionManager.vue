<template>
  <g class="connection-manager">
    <!-- 连接锚点 -->
    <ConnectionAnchor
      v-for="anchor in visibleAnchors"
      :key="`${anchor.elementId}-${anchor.position}`"
      :position="anchor.point"
      :anchor-position="anchor.position"
      :element-id="anchor.elementId"
      :visible="true"
      :is-hover="hoveredAnchor?.elementId === anchor.elementId && hoveredAnchor?.position === anchor.position"
      :is-active="activeAnchor?.elementId === anchor.elementId && activeAnchor?.position === anchor.position"
      @start-connection="handleStartConnection"
      @hover="handleAnchorHover"
      @leave="handleAnchorLeave"
    />
    
    <!-- 临时连接线 -->
    <g v-if="tempConnection" class="temp-connection">
      <path
        :d="tempConnectionPath"
        stroke="#1890ff"
        stroke-width="2"
        stroke-dasharray="5,5"
        fill="none"
        opacity="0.8"
      />
      <circle
        :cx="tempConnection.currentPoint.x"
        :cy="tempConnection.currentPoint.y"
        r="4"
        fill="#1890ff"
        stroke="#ffffff"
        stroke-width="2"
      />
    </g>
  </g>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCanvasStore } from '../stores/canvasStore'
import { useConnectionStore } from '../stores/connectionStore'
import ConnectionAnchor from './ConnectionAnchor.vue'
import { getElementAnchorPoints } from '../utils/connectionUtils'
import type { AnchorPosition } from '../utils/connectionUtils'

const canvasStore = useCanvasStore()
const connectionStore = useConnectionStore()

const hoveredAnchor = ref<{ elementId: string, position: AnchorPosition } | null>(null)
const activeAnchor = ref<{ elementId: string, position: AnchorPosition } | null>(null)

// 计算显示的锚点
const visibleAnchors = computed(() => {
  const anchors: Array<{
    elementId: string
    position: AnchorPosition
    point: { x: number, y: number }
  }> = []
  
  // 只为选中的元素显示锚点
  canvasStore.selectedElements.forEach(element => {
    if (element.type !== 'path' && !element.data?.isConnection) {
      const anchorPoints = getElementAnchorPoints(element)
      
      Object.entries(anchorPoints).forEach(([position, point]) => {
        if (position !== 'center') { // 不显示中心锚点
          anchors.push({
            elementId: element.id,
            position: position as AnchorPosition,
            point
          })
        }
      })
    }
  })
  
  return anchors
})

// 计算临时连接线路径
const tempConnectionPath = computed(() => {
  if (!connectionStore.tempConnection) return ''
  
  const fromElement = canvasStore.canvasData.elements.find(
    el => el.id === connectionStore.tempConnection!.fromElementId
  )
  
  if (!fromElement) return ''
  
  const anchorPoints = getElementAnchorPoints(fromElement)
  const startPoint = anchorPoints[connectionStore.tempConnection.fromAnchor]
  const endPoint = connectionStore.tempConnection.currentPoint
  
  return `M ${startPoint.x} ${startPoint.y} L ${endPoint.x} ${endPoint.y}`
})

const tempConnection = computed(() => connectionStore.tempConnection)

// 事件处理
const handleStartConnection = (elementId: string, anchor: AnchorPosition) => {
  activeAnchor.value = { elementId, position: anchor }
  connectionStore.startConnection(elementId, anchor)
  
  // 添加全局鼠标事件监听
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleAnchorHover = (elementId: string, anchor: AnchorPosition) => {
  hoveredAnchor.value = { elementId, position: anchor }
}

const handleAnchorLeave = () => {
  hoveredAnchor.value = null
}

const handleMouseMove = (e: MouseEvent) => {
  if (connectionStore.tempConnection) {
    // 将屏幕坐标转换为画布坐标
    const canvas = document.querySelector('svg')
    if (canvas) {
      const rect = canvas.getBoundingClientRect()
      const point = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      }
      connectionStore.updateTempConnection(point)
    }
  }
}

const handleMouseUp = (e: MouseEvent) => {
  if (connectionStore.tempConnection) {
    // 检查是否在另一个元素上结束
    const target = e.target as SVGElement
    const elementId = findElementIdFromTarget(target)
    
    let success = false
    if (elementId && elementId !== connectionStore.tempConnection.fromElementId) {
      success = connectionStore.endConnection(elementId)
    } else {
      // 在空白区域创建新元素
      success = connectionStore.endConnection()
    }
    
    // 清理状态
    activeAnchor.value = null
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
}

// 从SVG元素找到对应的canvas元素ID
const findElementIdFromTarget = (target: SVGElement): string | null => {
  // 向上遍历DOM树找到带有data-element-id的元素
  let current = target
  while (current && current !== document.body) {
    if (current.getAttribute('data-element-id')) {
      return current.getAttribute('data-element-id')
    }
    current = current.parentElement as SVGElement
  }
  return null
}

// 监听元素位置变化，更新连接
const handleElementUpdate = () => {
  // 当元素移动时，更新相关连接
  canvasStore.selectedElements.forEach(element => {
    connectionStore.updateConnectionsForElement(element.id)
  })
}

onMounted(() => {
  // 监听画布变化
  canvasStore.$subscribe((mutation, state) => {
    if (mutation.events?.some((event: any) => 
      event.key === 'elements' && event.type === 'set'
    )) {
      handleElementUpdate()
    }
  })
})

onUnmounted(() => {
  // 清理事件监听
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})

// 监听键盘事件取消连接
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && connectionStore.tempConnection) {
    connectionStore.cancelTempConnection()
    activeAnchor.value = null
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.temp-connection {
  pointer-events: none;
}
</style> 