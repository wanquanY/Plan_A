<template>
  <g class="image-element" :class="{ selected: isSelected }">
    <image 
      :x="element.x"
      :y="element.y"
      :width="element.width"
      :height="element.height"
      :href="element.data?.src || ''"
      :opacity="element.style.opacity || 1"
      :transform="getTransform()"
      @click="$emit('select', element.id, $event)"
      @error="handleImageError"
    />
    <!-- 图片加载失败时的占位符 -->
    <rect 
      v-if="imageError"
      :x="element.x"
      :y="element.y"
      :width="element.width"
      :height="element.height"
      fill="#f0f0f0"
      stroke="#d9d9d9"
      stroke-width="1"
      stroke-dasharray="5,5"
      @click="$emit('select', element.id, $event)"
    />
    <text 
      v-if="imageError"
      :x="element.x + element.width / 2"
      :y="element.y + element.height / 2"
      text-anchor="middle"
      dominant-baseline="middle"
      fill="#999"
      font-size="14"
    >
      图片加载失败
    </text>
  </g>
</template>

<script setup lang="ts">
import { ref } from 'vue'
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

const imageError = ref(false)

const getTransform = () => {
  if (props.element.rotation) {
    const cx = props.element.x + props.element.width / 2
    const cy = props.element.y + props.element.height / 2
    return `rotate(${props.element.rotation} ${cx} ${cy})`
  }
  return ''
}

const handleImageError = () => {
  imageError.value = true
}
</script>

<style scoped>
.image-element.selected image,
.image-element.selected rect {
  filter: drop-shadow(0 0 4px #1890ff);
}
</style> 