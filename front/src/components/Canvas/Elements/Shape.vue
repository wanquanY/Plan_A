<template>
  <g class="shape-element" :class="{ selected: isSelected }">
    <!-- 矩形 -->
    <rect 
      v-if="element.type === 'rectangle'"
      :x="element.x"
      :y="element.y"
      :width="element.width"
      :height="element.height"
      :fill="element.style.fill || '#ffffff'"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :opacity="element.style.opacity || 1"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
    />
    
    <!-- 圆形 -->
    <circle 
      v-else-if="element.type === 'circle'"
      :cx="element.x + element.width / 2"
      :cy="element.y + element.height / 2"
      :r="Math.min(element.width, element.height) / 2"
      :fill="element.style.fill || '#ffffff'"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :opacity="element.style.opacity || 1"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
    />
    
    <!-- 椭圆 -->
    <ellipse 
      v-else-if="element.type === 'ellipse'"
      :cx="element.x + element.width / 2"
      :cy="element.y + element.height / 2"
      :rx="element.width / 2"
      :ry="element.height / 2"
      :fill="element.style.fill || '#ffffff'"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :opacity="element.style.opacity || 1"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
    />
    
    <!-- 三角形 -->
    <polygon 
      v-else-if="element.type === 'triangle'"
      :points="getTrianglePoints()"
      :fill="element.style.fill || '#ffffff'"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :opacity="element.style.opacity || 1"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
    />
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CanvasElement } from '../types/canvas'

interface Props {
  element: CanvasElement
  isSelected?: boolean
}

interface Emits {
  (e: 'select', id: string, event: MouseEvent): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

const getTransform = () => {
  if (props.element.rotation) {
    const cx = props.element.x + props.element.width / 2
    const cy = props.element.y + props.element.height / 2
    return `rotate(${props.element.rotation} ${cx} ${cy})`
  }
  return ''
}

const getTrianglePoints = () => {
  const x = props.element.x
  const y = props.element.y
  const w = props.element.width
  const h = props.element.height
  return `${x + w/2},${y} ${x},${y + h} ${x + w},${y + h}`
}
</script>

<style scoped>
.shape-element.selected {
  filter: drop-shadow(0 0 4px #1890ff);
}
</style> 