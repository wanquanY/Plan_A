<template>
  <div class="input-section">
    <UnifiedInput 
      @send="$emit('send', $event)"
      @select-agent="$emit('select-agent', $event)"
      @upload-file="$emit('upload-file')"
      ref="unifiedInputRef"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import UnifiedInput from '../../unified-input/UnifiedInput.vue';

const emit = defineEmits(['send', 'select-agent', 'upload-file']);

const unifiedInputRef = ref(null);

// 聚焦输入框
const focus = () => {
  unifiedInputRef.value?.focus();
};

// 暴露方法
defineExpose({
  focus
});
</script>

<style scoped>
.input-section {
  padding: 20px;
  background: #ffffff;
}
</style> 