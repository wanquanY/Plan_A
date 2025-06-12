<template>
  <g class="connector-line" :class="{ selected: isSelected }">
    <!-- 直线 -->
    <line 
      v-if="element.type === 'line'"
      :x1="element.x"
      :y1="element.y"
      :x2="element.x + element.width"
      :y2="element.y + element.height"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :opacity="element.style.opacity || 1"
      @click="$emit('select', element.id, $event)"
    />
    
    <!-- 箭头 -->
    <g v-else-if="element.type === 'arrow'">
      <defs>
        <marker 
          :id="`arrowhead-${element.id}`"
          markerWidth="10" 
          markerHeight="7"
          refX="9" 
          refY="3.5" 
          orient="auto"
        >
          <polygon 
            points="0 0, 10 3.5, 0 7" 
            :fill="element.style.stroke || '#000000'"
          />
        </marker>
      </defs>
      <line 
        :x1="element.x"
        :y1="element.y"
        :x2="element.x + element.width"
        :y2="element.y + element.height"
        :stroke="element.style.stroke || '#000000'"
        :stroke-width="element.style.strokeWidth || 1"
        :opacity="element.style.opacity || 1"
        :marker-end="`url(#arrowhead-${element.id})`"
        @click="$emit('select', element.id, $event)"
      />
    </g>
    
    <!-- 路径（用于复杂连接线） -->
    <path 
      v-else-if="element.type === 'path'"
      :d="element.data?.path || ''"
      :stroke="element.style.stroke || '#000000'"
      :stroke-width="element.style.strokeWidth || 1"
      :fill="element.style.fill || 'none'"
      :opacity="element.style.opacity || 1"
      @click="$emit('select', element.id, $event)"
    />
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
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped>
.connector-line.selected line,
.connector-line.selected path {
  stroke-dasharray: 3,3;
  filter: drop-shadow(0 0 2px #1890ff);
}
</style> 