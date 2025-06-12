<template>
  <a-button-group>
    <a-button 
      :type="currentTool === 'rectangle' ? 'primary' : 'default'"
      @click="setTool('rectangle')"
      title="矩形"
    >
      <template #icon><BorderOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'circle' ? 'primary' : 'default'"
      @click="setTool('circle')"
      title="圆形"
    >
      <template #icon><RadiusBottomleftOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'ellipse' ? 'primary' : 'default'"
      @click="setTool('ellipse')"
      title="椭圆"
    >
      <template #icon><RadiusBottomrightOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'triangle' ? 'primary' : 'default'"
      @click="setTool('triangle')"
      title="三角形"
    >
      <template #icon><CaretUpOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'line' ? 'primary' : 'default'"
      @click="setTool('line')"
      title="直线"
    >
      <template #icon><LineOutlined /></template>
    </a-button>
    <a-button 
      :type="currentTool === 'arrow' ? 'primary' : 'default'"
      @click="setTool('arrow')"
      title="箭头"
    >
      <template #icon><ArrowRightOutlined /></template>
    </a-button>
  </a-button-group>
</template>

<script setup lang="ts">
import { ButtonGroup as AButtonGroup, Button as AButton } from 'ant-design-vue'
import {
  BorderOutlined,
  RadiusBottomleftOutlined,
  RadiusBottomrightOutlined,
  CaretUpOutlined,
  LineOutlined,
  ArrowRightOutlined
} from '@ant-design/icons-vue'
import { useCanvasStore } from '../stores/canvasStore'

const canvasStore = useCanvasStore()
const { currentTool } = canvasStore

const setTool = (tool: string) => {
  canvasStore.setCurrentTool(tool)
}
</script> 