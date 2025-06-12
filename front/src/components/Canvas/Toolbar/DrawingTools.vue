<template>
  <a-button-group>
    <a-button 
      :type="currentTool === 'brush' ? 'primary' : 'default'"
      @click="setTool('brush')"
      title="画笔"
    >
      <template #icon><BgColorsOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'eraser' ? 'primary' : 'default'"
      @click="setTool('eraser')"
      title="橡皮擦"
    >
      <template #icon><DeleteOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'highlighter' ? 'primary' : 'default'"
      @click="setTool('highlighter')"
      title="荧光笔"
    >
      <template #icon><HighlightOutlined /></template>
    </a-button>
  </a-button-group>
</template>

<script setup lang="ts">
import { ButtonGroup as AButtonGroup, Button as AButton } from 'ant-design-vue'
import {
  BgColorsOutlined,
  DeleteOutlined,
  HighlightOutlined
} from '@ant-design/icons-vue'
import { useCanvasStore } from '../stores/canvasStore'

const canvasStore = useCanvasStore()
const { currentTool } = canvasStore

const setTool = (tool: string) => {
  canvasStore.setCurrentTool(tool)
}
</script> 