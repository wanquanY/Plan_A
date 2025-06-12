import { defineStore } from 'pinia'
import type { CanvasData, CanvasHistory } from '../types/canvas'
import { deepClone } from '../utils/canvasUtils'

export const useHistoryStore = defineStore('canvasHistory', {
  state: (): CanvasHistory => ({
    index: -1,
    states: [],
    maxStates: 50
  }),

  getters: {
    canUndo: (state) => state.index > 0,
    canRedo: (state) => state.index < state.states.length - 1,
    currentState: (state) => state.states[state.index] || null
  },

  actions: {
    /**
     * 推入新状态
     */
    pushState(canvasData: CanvasData) {
      // 移除当前位置之后的所有状态（当用户在撤销后进行新操作时）
      if (this.index < this.states.length - 1) {
        this.states.splice(this.index + 1)
      }

      // 深拷贝状态以避免引用问题
      const newState = deepClone(canvasData)
      this.states.push(newState)

      // 限制历史记录数量
      if (this.states.length > this.maxStates) {
        this.states.shift()
      } else {
        this.index++
      }
    },

    /**
     * 撤销操作
     */
    undo(): CanvasData | null {
      if (this.canUndo) {
        this.index--
        return deepClone(this.currentState)
      }
      return null
    },

    /**
     * 重做操作
     */
    redo(): CanvasData | null {
      if (this.canRedo) {
        this.index++
        return deepClone(this.currentState)
      }
      return null
    },

    /**
     * 清空历史记录
     */
    clear() {
      this.states = []
      this.index = -1
    },

    /**
     * 初始化历史记录
     */
    init(canvasData: CanvasData) {
      this.clear()
      this.pushState(canvasData)
    },

    /**
     * 获取历史记录信息
     */
    getHistoryInfo() {
      return {
        total: this.states.length,
        current: this.index + 1,
        canUndo: this.canUndo,
        canRedo: this.canRedo
      }
    },

    /**
     * 跳转到指定历史状态
     */
    jumpToState(index: number): CanvasData | null {
      if (index >= 0 && index < this.states.length) {
        this.index = index
        return deepClone(this.currentState)
      }
      return null
    },

    /**
     * 设置最大历史记录数量
     */
    setMaxStates(max: number) {
      this.maxStates = Math.max(1, max)
      
      // 如果当前记录超过新的最大值，则移除最旧的记录
      while (this.states.length > this.maxStates) {
        this.states.shift()
        if (this.index > 0) {
          this.index--
        }
      }
    }
  }
}) 