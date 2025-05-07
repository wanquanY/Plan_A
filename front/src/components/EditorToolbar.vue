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
    
    <!-- 字体颜色选择器 -->
    <div class="spacing-select">
      <button class="toolbar-button" title="字体颜色">
        <font-colors-outlined />
      </button>
      <div class="spacing-dropdown color-dropdown">
        <div class="color-grid">
          <button 
            v-for="color in textColors" 
            :key="color.value" 
            class="color-btn" 
            :style="{ backgroundColor: color.value }"
            :title="color.name"
            @click="setFontColor(color.value)">
          </button>
        </div>
      </div>
    </div>
    
    <!-- 背景颜色选择器 -->
    <div class="spacing-select">
      <button class="toolbar-button" title="背景颜色">
        <bg-colors-outlined />
      </button>
      <div class="spacing-dropdown color-dropdown">
        <div class="color-grid">
          <button 
            v-for="color in bgColors" 
            :key="color.value" 
            class="color-btn" 
            :style="{ backgroundColor: color.value }"
            :title="color.name"
            @click="setBackgroundColor(color.value)">
          </button>
        </div>
      </div>
    </div>
    
    <div class="toolbar-divider"></div>
    
    <!-- 文本对齐方式 -->
    <button class="toolbar-button" @click="applyFormatting('justifyLeft')" title="左对齐">
      <align-left-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('justifyCenter')" title="居中对齐">
      <align-center-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('justifyRight')" title="右对齐">
      <align-right-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('justifyFull')" title="两端对齐">
      <menu-outlined style="transform: rotate(90deg);" />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <!-- 中文段落格式 -->
    <div class="spacing-select">
      <button class="toolbar-button" title="段落格式">
        <format-painter-outlined />
      </button>
      <div class="spacing-dropdown format-dropdown">
        <button @click="setParagraphFormat('indentFirstLine')" class="format-btn">
          <format-painter-outlined class="format-icon" />
          <span>首行缩进</span>
        </button>
        <button @click="setParagraphFormat('noIndent')" class="format-btn">
          <format-painter-outlined class="format-icon" />
          <span>取消缩进</span>
        </button>
        <button @click="setParagraphFormat('increaseParagraphSpacing')" class="format-btn">
          <column-height-outlined class="format-icon" />
          <span>增加段间距</span>
        </button>
        <button @click="setParagraphFormat('decreaseParagraphSpacing')" class="format-btn">
          <column-height-outlined class="format-icon" style="transform: scaleY(-1);" />
          <span>减少段间距</span>
        </button>
        <button @click="setParagraphFormat('punctuationDefault')" class="format-btn">
          <OrderedListOutlined class="format-icon" />
          <span>标点默认间距</span>
        </button>
        <button @click="setParagraphFormat('punctuationDense')" class="format-btn">
          <ColumnWidthOutlined class="format-icon" style="transform: scaleX(-1);" />
          <span>标点紧缩</span>
        </button>
      </div>
    </div>
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="applyFormatting('insertOrderedList')">
      <ordered-list-outlined />
    </button>
    <button class="toolbar-button" @click="applyFormatting('insertUnorderedList')">
      <unordered-list-outlined />
    </button>
    
    <div class="toolbar-divider"></div>
    
    <div class="spacing-select">
      <button class="toolbar-button" title="字间距">
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
      <button class="toolbar-button" title="字号">
        <font-size-outlined />
      </button>
      <div class="spacing-dropdown font-size-dropdown">
        <div class="font-size-buttons">
          <button class="increase-decrease-btn" @click="changeFontSize('decrease')" title="缩小字号">
            <span class="small-a">A</span>
          </button>
          <button class="increase-decrease-btn" @click="changeFontSize('increase')" title="增大字号">
            <span class="large-a">A</span>
          </button>
        </div>
        <div class="font-size-divider"></div>
        <button @click="setFontSize('12px')">12px</button>
        <button @click="setFontSize('14px')">14px</button>
        <button @click="setFontSize('16px')">16px</button>
        <button @click="setFontSize('18px')">18px</button>
        <button @click="setFontSize('20px')">20px</button>
        <button @click="setFontSize('24px')">24px</button>
        <button @click="setFontSize('30px')">30px</button>
        <button @click="setFontSize('36px')">36px</button>
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
    
    <div class="toolbar-divider"></div>
    
    <button class="toolbar-button" @click="createLink">
      <link-outlined />
    </button>
    
    <button class="toolbar-button" @click="handleImageClick" title="插入图片">
      <picture-outlined />
    </button>
    <input
      type="file"
      ref="fileInputRef"
      style="display: none;"
      accept="image/*"
      @change="handleImageUpload"
    />
    
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
  AlignRightOutlined,
  MenuOutlined,
  LinkOutlined,
  RedoOutlined,
  UndoOutlined,
  DownOutlined,
  ColumnWidthOutlined,
  LineHeightOutlined,
  FontSizeOutlined,
  BgColorsOutlined,
  FontColorsOutlined,
  FormatPainterOutlined,
  ColumnHeightOutlined,
  PictureOutlined,
} from '@ant-design/icons-vue';
import { ref } from 'vue';
import uploadService from '../services/uploadService';
import { message } from 'ant-design-vue';

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

// 字体颜色列表
const textColors = ref([
  { name: '黑色', value: '#000000' },
  { name: '深灰色', value: '#444444' },
  { name: '灰色', value: '#888888' },
  { name: '银色', value: '#cccccc' },
  { name: '红色', value: '#d81e06' },
  { name: '橙色', value: '#f4af3d' },
  { name: '黄色', value: '#f1ca17' },
  { name: '绿色', value: '#27a93f' },
  { name: '深青色', value: '#1abb9c' },
  { name: '天蓝色', value: '#07a9fe' },
  { name: '蓝色', value: '#0000ff' },
  { name: '紫色', value: '#9d00ff' },
  { name: '粉红色', value: '#f570a5' },
  { name: '深红色', value: '#a61b29' },
  { name: '棕色', value: '#8c4b31' },
  { name: '白色', value: '#ffffff' }
]);

// 背景颜色列表
const bgColors = ref([
  { name: '白色', value: '#ffffff' },
  { name: '淡灰色', value: '#f5f5f5' },
  { name: '浅灰色', value: '#e9e9e9' },
  { name: '淡黄色', value: '#fcf8e3' },
  { name: '浅黄色', value: '#fff9c4' },
  { name: '淡红色', value: '#fce4e4' },
  { name: '浅红色', value: '#ffcdd2' },
  { name: '淡蓝色', value: '#e1f5fe' },
  { name: '浅蓝色', value: '#b3e5fc' },
  { name: '淡绿色', value: '#e8f5e9' },
  { name: '浅绿色', value: '#c8e6c9' },
  { name: '淡紫色', value: '#f3e5f5' },
  { name: '浅紫色', value: '#e1bee7' },
  { name: '米色', value: '#f9f2e7' },
  { name: '黑色', value: '#000000' },
  { name: '透明', value: 'transparent' }
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

// 设置字体颜色
const setFontColor = (color: string) => {
  document.execCommand('foreColor', false, color);
};

// 设置背景颜色
const setBackgroundColor = (color: string) => {
  document.execCommand('hiliteColor', false, color);
};

// 设置中文段落格式
const setParagraphFormat = (formatType: string) => {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  
  // 获取选中的范围
  const range = selection.getRangeAt(0);
  
  // 查找选中范围内或光标所在位置的段落
  let paragraphs: HTMLElement[] = [];
  
  // 如果没有选择任何内容，只是光标
  if (range.collapsed) {
    let node = range.startContainer;
    
    // 查找光标所在的段落
    while (node && node.nodeName !== 'P') {
      if (node.nodeName === 'DIV' && node.classList.contains('editor-content')) {
        // 已经到达编辑器根节点，没有找到段落
        break;
      }
      node = node.parentNode;
    }
    
    if (node && node.nodeName === 'P') {
      paragraphs.push(node as HTMLElement);
    }
  } else {
    // 如果选择了内容，找到所有在选择范围内的段落
    const container = range.commonAncestorContainer;
    const allParagraphs = container.nodeName === 'P' 
      ? [container] 
      : Array.from(container.querySelectorAll('p'));
    
    // 检查每个段落是否在选择范围内
    for (const para of allParagraphs) {
      if (range.intersectsNode(para)) {
        paragraphs.push(para as HTMLElement);
      }
    }
  }
  
  if (paragraphs.length === 0) {
    // 没有找到段落，创建新段落
    const p = document.createElement('p');
    if (range.collapsed) {
      // 在光标位置插入段落
      range.insertNode(p);
    } else {
      // 将选中内容移动到新段落
      p.appendChild(range.extractContents());
      range.insertNode(p);
    }
    paragraphs.push(p);
  }
  
  // 应用段落格式
  paragraphs.forEach(p => {
    switch(formatType) {
      case 'indentFirstLine':
        p.style.textIndent = '2em';
        break;
      case 'noIndent':
        p.style.textIndent = '0';
        break;
      case 'increaseParagraphSpacing':
        p.style.marginBottom = '1em';
        break;
      case 'decreaseParagraphSpacing':
        p.style.marginBottom = '0.5em';
        break;
      case 'punctuationDefault':
        p.style.fontVariantEastAsian = 'normal';
        break;
      case 'punctuationDense':
        p.style.fontVariantEastAsian = 'proportional-width';
        break;
    }
  });
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

// 增大/减小字号
const changeFontSize = (direction: string) => {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  
  // 获取选中的范围
  const range = selection.getRangeAt(0);
  
  // 如果没有选中内容，就什么都不做
  if (range.collapsed) return;
  
  // 创建一个span元素来包装选中内容
  const span = document.createElement('span');
  
  // 复制选中内容到新的span
  span.appendChild(range.extractContents());
  
  // 获取现有字体大小
  let currentSize = 16; // 默认16px
  
  // 尝试从所选内容中获取当前字体大小
  const computedStyle = window.getComputedStyle(span);
  const fontSize = computedStyle.fontSize;
  
  if (fontSize) {
    // 提取数字部分
    const sizeMatch = fontSize.match(/(\d+(\.\d+)?)px/);
    if (sizeMatch && sizeMatch[1]) {
      currentSize = parseFloat(sizeMatch[1]);
    }
  }
  
  // 计算新字体大小
  let newSize;
  if (direction === 'increase') {
    // 增大字号
    if (currentSize < 12) newSize = 12;
    else if (currentSize < 14) newSize = 14;
    else if (currentSize < 16) newSize = 16;
    else if (currentSize < 18) newSize = 18;
    else if (currentSize < 20) newSize = 20;
    else if (currentSize < 24) newSize = 24;
    else if (currentSize < 30) newSize = 30;
    else if (currentSize < 36) newSize = 36;
    else newSize = 36; // 最大36px
  } else {
    // 减小字号
    if (currentSize > 30) newSize = 30;
    else if (currentSize > 24) newSize = 24;
    else if (currentSize > 20) newSize = 20;
    else if (currentSize > 18) newSize = 18;
    else if (currentSize > 16) newSize = 16;
    else if (currentSize > 14) newSize = 14;
    else if (currentSize > 12) newSize = 12;
    else newSize = 12; // 最小12px
  }
  
  // 设置新字体大小
  span.style.fontSize = `${newSize}px`;
  
  // 将span插入到原始范围位置
  range.insertNode(span);
  
  // 更新选区以包含新的span
  selection.removeAllRanges();
  const newRange = document.createRange();
  newRange.selectNodeContents(span);
  selection.addRange(newRange);
};

const fileInputRef = ref(null);

const handleImageClick = () => {
  fileInputRef.value.click();
};

const handleImageUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    const file = target.files[0];
    if (file) {
      message.loading({ content: '正在上传图片...', key: 'uploadImage', duration: 0 });
      
      try {
        // 直接上传文件，获取URL
        const imageUrl = await uploadService.uploadImage(file);
        
        // 使用获取到的URL插入图片
        emit('apply-formatting', { command: 'insertImage', value: imageUrl });
        
        message.success({ content: '图片上传成功', key: 'uploadImage' });
      } catch (error) {
        console.error('上传图片失败:', error);
        message.error({ content: '上传图片失败', key: 'uploadImage' });
      }
      
      // 清除文件输入，允许再次选择同一文件
      target.value = '';
    }
  }
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
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  box-sizing: border-box;
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

/* 颜色选择器样式 */
.color-dropdown {
  width: 170px;
  padding: 8px;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 5px;
}

.color-btn {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  cursor: pointer;
  padding: 0;
  transition: transform 0.2s;
}

.color-btn:hover {
  transform: scale(1.1);
  z-index: 1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 段落格式下拉菜单 */
.format-dropdown {
  width: 160px;
}

.format-btn {
  display: flex;
  align-items: center;
  gap: 8px;
}

.format-icon {
  font-size: 14px;
  color: #555;
}

.font-size-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
}

.font-size-divider {
  height: 1px;
  background-color: rgba(0, 0, 0, 0.1);
  margin: 4px 0;
}

.increase-decrease-btn {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.small-a {
  font-size: 14px;
  font-weight: bold;
}

.large-a {
  font-size: 20px;
  font-weight: bold;
}
</style> 