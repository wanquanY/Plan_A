<template>
  <g class="text-element" :class="{ selected: isSelected }">
    <text 
      :x="element.x"
      :y="element.y + (element.style.fontSize || 16)"
      :font-size="element.style.fontSize || 16"
      :font-family="element.style.fontFamily || 'Arial'"
      :font-weight="element.style.fontWeight || 'normal'"
      :font-style="element.style.fontStyle || 'normal'"
      :fill="element.style.stroke || '#000000'"
      :opacity="element.style.opacity || 1"
      :text-anchor="element.style.textAlign || 'left'"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
      @dblclick="$emit('edit', element.id)"
    >
      {{ element.data?.text || '文本' }}
    </text>
  </g>
</template>

<script setup lang="ts">
import type { CanvasElement } from '../types/canvas'

interface Props {
  element: CanvasElement
  isSelected?: boolean
}

interface Emits {
  (e: 'select', id: string, event: MouseEvent): void
  (e: 'edit', id: string): void
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
</script>

<style scoped>
.text-element.selected text {
  filter: drop-shadow(0 0 2px #1890ff);
}

.text-element text {
  cursor: pointer;
  user-select: none;
}
</style> 