<template>
  <g class="connection-anchor" v-if="visible">
    <circle
      :cx="position.x"
      :cy="position.y"
      :r="radius"
      :fill="fillColor"
      :stroke="strokeColor"
      :stroke-width="strokeWidth"
      class="anchor-point"
      :class="{ 'anchor-hover': isHover, 'anchor-active': isActive }"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @mousedown="handleMouseDown"
    />
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Point } from '../types/canvas'
import type { AnchorPosition } from '../utils/connectionUtils'

interface Props {
  position: Point
  anchorPosition: AnchorPosition
  elementId: string
  visible?: boolean
  isHover?: boolean
  isActive?: boolean
  size?: 'small' | 'medium' | 'large'
}

interface Emits {
  (e: 'start-connection', elementId: string, anchor: AnchorPosition): void
  (e: 'hover', elementId: string, anchor: AnchorPosition): void
  (e: 'leave', elementId: string, anchor: AnchorPosition): void
}

const props = withDefaults(defineProps<Props>(), {
  visible: true,
  isHover: false,
  isActive: false,
  size: 'medium'
})

const emit = defineEmits<Emits>()

const radius = computed(() => {
  const sizes = {
    small: 4,
    medium: 6,
    large: 8
  }
  return sizes[props.size]
})

const fillColor = computed(() => {
  if (props.isActive) return '#ff4757'
  if (props.isHover) return '#2f90ff'
  return '#1890ff'
})

const strokeColor = computed(() => {
  return '#ffffff'
})

const strokeWidth = computed(() => {
  return props.isHover || props.isActive ? 3 : 2
})

const handleMouseEnter = () => {
  emit('hover', props.elementId, props.anchorPosition)
}

const handleMouseLeave = () => {
  emit('leave', props.elementId, props.anchorPosition)
}

const handleMouseDown = (e: MouseEvent) => {
  e.stopPropagation()
  e.preventDefault()
  emit('start-connection', props.elementId, props.anchorPosition)
}
</script>

<style scoped>
.anchor-point {
  cursor: crosshair;
  transition: all 0.2s ease;
}

.anchor-hover {
  filter: drop-shadow(0 0 4px rgba(24, 144, 255, 0.6));
}

.anchor-active {
  filter: drop-shadow(0 0 6px rgba(255, 71, 87, 0.8));
}
</style> 