<template>
  <div class="editor-toolbar">
    <button class="toolbar-button" @click="setHeading('p')">
      <span>正文</span>
    </button>
    
    <div class="heading-select">
      <select class="heading-dropdown" @change="(e) => setHeading((e.target as HTMLSelectElement).value)">
        <option value="" disabled selected>标题</option>
        <option value="h1">标题1</option>
        <option value="h2">标题2</option>
        <option value="h3">标题3</option>
        <option value="h4">标题4</option>
        <option value="h5">标题5</option>
        <option value="h6">标题6</option>
      </select>
      <div class="dropdown-icon">
        <down-outlined />
      </div>
    </div>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="applyFormatting('bold')">
      <bold-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('italic')">
      <italic-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('underline')">
      <underline-outlined />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="applyFormatting('justifyLeft')">
      <align-left-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('justifyCenter')">
      <align-center-outlined />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="applyFormatting('insertOrderedList')">
      <ordered-list-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('insertUnorderedList')">
      <unordered-list-outlined />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <div class="spacing-select">
      <button class="toolbar-button">
        <column-width-outlined />
      </button>
      <div class="spacing-dropdown">
        <button @click="setLetterSpacing('normal')">默认间距</button>
        <button @click="setLetterSpacing('0.05em')">稍宽</button>
        <button @click="setLetterSpacing('0.1em')">宽</button>
        <button @click="setLetterSpacing('0.2em')">很宽</button>
      </div>
    </div>
    
    <div class="spacing-select">
      <button class="toolbar-button">
        <line-height-outlined />
      </button>
      <div class="spacing-dropdown">
        <button @click="setLineHeight('1.2')">紧凑</button>
        <button @click="setLineHeight('1.5')">默认</button>
        <button @click="setLineHeight('1.8')">宽松</button>
        <button @click="setLineHeight('2.0')">很宽松</button>
      </div>
    </div>
    
    <div class="spacing-select">
      <button class="toolbar-button">
        <font-size-outlined />
      </button>
      <div class="spacing-dropdown">
        <button @click="setFontSize('12px')">很小</button>
        <button @click="setFontSize('14px')">小</button>
        <button @click="setFontSize('16px')">默认</button>
        <button @click="setFontSize('18px')">大</button>
        <button @click="setFontSize('24px')">很大</button>
      </div>
    </div>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="createLink">
      <link-outlined />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="undoAction">
      <undo-outlined />
    </button>
    <button class="toolbar-button" @click="redoAction">
      <redo-outlined />
    </button>
  </div>
</template>

<script setup lang="ts">
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  LinkOutlined,
  RedoOutlined,
  UndoOutlined,
  DownOutlined,
  ColumnWidthOutlined,
  LineHeightOutlined,
  FontSizeOutlined,
} from '@ant-design/icons-vue';

defineProps({
  editorRef: {
    type: Object,
    required: false
  }
});

const emit = defineEmits([
  'update-model-value', 
  'apply-formatting', 
  'set-heading', 
  'set-letter-spacing', 
  'set-line-height', 
  'set-font-size',
  'undo',
  'redo'
]);

const applyFormatting = (command: string, value?: string) => {
  emit('apply-formatting', { command, value });
};

const setHeading = (level: string) => {
  emit('set-heading', level);
};

const setLetterSpacing = (spacing: string) => {
  emit('set-letter-spacing', spacing);
};

const setLineHeight = (height: string) => {
  emit('set-line-height', height);
};

const setFontSize = (size: string) => {
  emit('set-font-size', size);
};

const createLink = () => {
  const url = prompt('请输入链接URL', 'https://');
  if (url) {
    emit('apply-formatting', { command: 'createLink', value: url });
  }
};

const undoAction = () => {
  emit('undo');
};

const redoAction = () => {
  emit('redo');
};
</script>

<style scoped>
/* 工具栏样式 */
.editor-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background-color: #f9f9f9;
  border-radius: 8px 8px 0 0;
}

.toolbar-button {
  background: none;
  border: none;
  font-size: 16px;
  color: #555;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.toolbar-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background-color: rgba(0, 0, 0, 0.1);
  margin: 0 8px;
}

/* 添加标题下拉菜单样式 */
.heading-select {
  position: relative;
  display: flex;
  align-items: center;
}

.heading-dropdown {
  height: 28px;
  padding: 0 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  background-color: white;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 24px;
}

.heading-dropdown:focus {
  outline: none;
  border-color: rgba(0, 123, 255, 0.5);
}

.dropdown-icon {
  position: absolute;
  right: 8px;
  pointer-events: none;
  font-size: 12px;
  color: #666;
}

/* 字间距和行间距下拉菜单样式 */
.spacing-select {
  position: relative;
  display: inline-block;
}

.spacing-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background-color: white;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  width: 120px;
}

.spacing-select:hover .spacing-dropdown {
  display: block;
}

.spacing-dropdown button {
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  font-size: 14px;
  border: none;
  background: none;
  cursor: pointer;
  white-space: nowrap;
}

.spacing-dropdown button:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

/* 字号下拉菜单特殊样式 */
.font-size-dropdown {
  width: 150px;
}

.font-size-dropdown button {
  padding: 5px 12px;
  text-align: center;
}
</style> 