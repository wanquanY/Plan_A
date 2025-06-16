import jsPDF from 'jspdf';

class PDFExportService {
  /**
   * 导出笔记为PDF - 先转换Mermaid为图片，再合成PDF
   */
  async exportNoteAsPDF(content: string, title: string): Promise<void> {
    try {
      console.log('开始导出PDF，先转换Mermaid为图片');
      console.log('内容长度:', content.length);
      console.log('标题:', title);
      
      // 检查内容
      if (!content || content.trim() === '') {
        throw new Error('笔记内容为空');
      }
      
      // 动态导入html2canvas
      const html2canvas = (await import('html2canvas')).default;
      
      // 查找编辑器内容区域
      let editorElement = this.findEditorElement();
      if (!editorElement) {
        throw new Error('无法找到编辑器内容区域，请确保编辑器已加载');
      }
      
      console.log('找到编辑器元素:', editorElement);
      
      // 克隆编辑器元素，避免影响原始内容
      const clonedEditor = editorElement.cloneNode(true) as HTMLElement;
      clonedEditor.style.position = 'absolute';
      clonedEditor.style.top = '-9999px';
      clonedEditor.style.left = '-9999px';
      clonedEditor.style.width = '800px';
      clonedEditor.style.minWidth = '800px';
      clonedEditor.style.maxWidth = 'none';
      clonedEditor.style.padding = '40px';
      clonedEditor.style.backgroundColor = '#ffffff';
      clonedEditor.style.zIndex = '-1';
      
      // 添加到页面
      document.body.appendChild(clonedEditor);
      
      try {
        // 等待克隆元素渲染
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 步骤1：转换所有Mermaid图表为图片
        await this.convertMermaidToImages(clonedEditor);
        
        // 步骤2：等待其他内容渲染
        await this.waitForOtherContentRender(clonedEditor);
        
        // 步骤3：生成PDF
        await this.generatePDF(clonedEditor, title, html2canvas);
        
        console.log('PDF导出成功');
      } finally {
        // 清理克隆的元素
        document.body.removeChild(clonedEditor);
      }
    } catch (error: any) {
      console.error('PDF导出失败:', error);
      throw new Error(`PDF导出失败: ${error.message}`);
    }
  }
  
  /**
   * 查找编辑器元素
   */
  private findEditorElement(): HTMLElement | null {
    const selectors = [
      '.editor-content',
      '.ProseMirror',
      '[contenteditable="true"]',
      '.editor-main .editor-content'
    ];
    
    for (const selector of selectors) {
      const element = document.querySelector(selector) as HTMLElement;
      if (element) {
        return element;
      }
    }
    
    return null;
  }
  
  /**
   * 转换所有Mermaid图表为图片
   */
  private async convertMermaidToImages(containerElement: HTMLElement): Promise<void> {
    console.log('开始转换Mermaid图表为图片...');
    
    // 动态导入mermaid
    let mermaid: any;
    try {
      mermaid = (await import('mermaid')).default;
    } catch (error) {
      console.warn('无法加载mermaid库，跳过mermaid图表转换:', error);
      return;
    }
    
    // 初始化mermaid
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true
      }
    });
    
    // 策略1: 处理代码块形式的mermaid
    await this.convertCodeBlockMermaid(containerElement, mermaid);
    
    // 策略2: 处理已渲染的mermaid容器
    await this.convertRenderedMermaid(containerElement, mermaid);
    
    console.log('Mermaid图表转换完成');
  }
  
  /**
   * 转换代码块形式的Mermaid
   */
  private async convertCodeBlockMermaid(containerElement: HTMLElement, mermaid: any): Promise<void> {
    const codeBlocks = containerElement.querySelectorAll('pre code.language-mermaid');
    console.log('找到代码块形式的Mermaid:', codeBlocks.length);
    
    for (let i = 0; i < codeBlocks.length; i++) {
      try {
        const codeElement = codeBlocks[i] as HTMLElement;
        const preElement = codeElement.closest('pre');
        if (!preElement) continue;
        
        const code = codeElement.textContent?.trim();
        if (!code) continue;
        
        console.log(`转换代码块Mermaid ${i}:`, code.substring(0, 50) + '...');
        
        // 创建图片元素替换整个pre元素
        const imgElement = await this.createMermaidImage(code, mermaid, i);
        if (imgElement && preElement.parentNode) {
          preElement.parentNode.replaceChild(imgElement, preElement);
          console.log(`代码块Mermaid ${i} 替换成功`);
        }
      } catch (error) {
        console.error(`转换代码块Mermaid ${i} 失败:`, error);
      }
    }
  }
  
  /**
   * 转换已渲染的Mermaid容器
   */
  private async convertRenderedMermaid(containerElement: HTMLElement, mermaid: any): Promise<void> {
    const mermaidContainers = containerElement.querySelectorAll('.mermaid-container');
    console.log('找到已渲染的Mermaid容器:', mermaidContainers.length);
    
    for (let i = 0; i < mermaidContainers.length; i++) {
      try {
        const container = mermaidContainers[i] as HTMLElement;
        const mermaidElement = container.querySelector('.mermaid');
        if (!mermaidElement) continue;
        
        // 尝试从data-original-content获取代码
        let code = mermaidElement.getAttribute('data-original-content');
        if (!code) {
          // 如果没有，尝试从textContent获取（但要过滤SVG内容）
          const textContent = mermaidElement.textContent?.trim();
          if (textContent && !textContent.includes('<svg') && !textContent.startsWith('#mermaid-')) {
            code = textContent;
          }
        }
        
        if (!code) {
          console.warn(`容器Mermaid ${i} 没有找到有效代码`);
          continue;
        }
        
        console.log(`转换容器Mermaid ${i}:`, code.substring(0, 50) + '...');
        
        // 创建图片元素替换整个容器
        const imgElement = await this.createMermaidImage(code, mermaid, i + 1000);
        if (imgElement && container.parentNode) {
          container.parentNode.replaceChild(imgElement, container);
          console.log(`容器Mermaid ${i} 替换成功`);
        }
      } catch (error) {
        console.error(`转换容器Mermaid ${i} 失败:`, error);
      }
    }
  }
  
  /**
   * 创建Mermaid图片元素
   */
  private async createMermaidImage(code: string, mermaid: any, index: number): Promise<HTMLElement | null> {
    try {
      // 创建临时容器来渲染mermaid
      const tempContainer = document.createElement('div');
      tempContainer.style.position = 'absolute';
      tempContainer.style.top = '-9999px';
      tempContainer.style.left = '-9999px';
      tempContainer.style.width = '800px';
      tempContainer.style.backgroundColor = 'white';
      tempContainer.className = 'mermaid-temp';
      tempContainer.textContent = code;
      
      document.body.appendChild(tempContainer);
      
      try {
        // 渲染mermaid
        await mermaid.run({
          nodes: [tempContainer]
        });
        
        // 等待渲染完成
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // 查找生成的SVG
        const svgElement = tempContainer.querySelector('svg');
        if (!svgElement) {
          console.error(`Mermaid ${index} 没有生成SVG`);
          return null;
        }
        
        console.log(`Mermaid ${index} SVG生成成功`);
        
        // 转换SVG为图片
        const imageDataUrl = await this.svgToImage(svgElement);
        
                 // 创建img元素
         const imgElement = document.createElement('img');
         imgElement.src = imageDataUrl;
         imgElement.style.maxWidth = '100%';
         imgElement.style.height = 'auto';
         imgElement.style.display = 'block';
         imgElement.style.margin = '20px auto'; // 水平居中
         imgElement.style.textAlign = 'center';
         
         // 创建居中容器
         const centerContainer = document.createElement('div');
         centerContainer.style.textAlign = 'center';
         centerContainer.style.margin = '20px 0';
         centerContainer.appendChild(imgElement);
         
         return centerContainer;
        
      } finally {
        // 清理临时容器
        document.body.removeChild(tempContainer);
      }
      
    } catch (error) {
      console.error(`创建Mermaid图片 ${index} 失败:`, error);
      return null;
    }
  }
  

  
  /**
   * 将SVG转换为图片
   */
  private async svgToImage(svgElement: SVGElement): Promise<string> {
    return new Promise((resolve, reject) => {
      try {
        // 克隆SVG元素，避免修改原始元素
        const clonedSvg = svgElement.cloneNode(true) as SVGElement;
        
        // 确保SVG有正确的尺寸
        let bbox: DOMRect | null = null;
        try {
          bbox = (svgElement as any).getBBox();
        } catch (e) {
          bbox = null;
        }
        
        const width = bbox?.width || 600;
        const height = bbox?.height || 400;
        
        // 设置SVG属性以避免跨域问题
        clonedSvg.setAttribute('width', width.toString());
        clonedSvg.setAttribute('height', height.toString());
        clonedSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        
        // 清理可能导致跨域问题的属性
        this.cleanSvgForExport(clonedSvg);
        
        // 获取清理后的SVG字符串
        const svgData = new XMLSerializer().serializeToString(clonedSvg);
        
        // 使用data URL而不是blob URL来避免跨域问题
        const svgDataUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
        
        // 创建canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const img = new Image();
        
        // 设置crossOrigin以避免污染canvas
        img.crossOrigin = 'anonymous';
        
        img.onload = function() {
          try {
            // 设置canvas尺寸
            canvas.width = width;
            canvas.height = height;
            
            // 绘制SVG图片（不添加背景，保持透明）
            if (ctx) {
              ctx.drawImage(img, 0, 0, width, height);
            }
            
            // 转换为图片数据
            const imageDataUrl = canvas.toDataURL('image/png', 1.0);
            resolve(imageDataUrl);
          } catch (error) {
            console.error('Canvas转换失败:', error);
            reject(error);
          }
        };
        
        img.onerror = function(error) {
          console.error('SVG图片加载失败:', error);
          reject(new Error('SVG图片加载失败'));
        };
        
        img.src = svgDataUrl;
        
      } catch (error) {
        console.error('SVG转换准备失败:', error);
        reject(error);
      }
    });
  }
  
  /**
   * 清理SVG元素，移除可能导致跨域问题的属性
   */
  private cleanSvgForExport(svgElement: SVGElement): void {
    // 移除可能的外部引用
    const elementsToClean = svgElement.querySelectorAll('*');
    
    elementsToClean.forEach(element => {
      // 移除可能的外部链接属性
      element.removeAttribute('href');
      element.removeAttribute('xlink:href');
      
      // 移除可能的脚本
      if (element.tagName.toLowerCase() === 'script') {
        element.remove();
      }
      
      // 清理样式中的外部引用
      const style = element.getAttribute('style');
      if (style) {
        // 移除可能的url()引用
        const cleanedStyle = style.replace(/url\([^)]*\)/g, '');
        element.setAttribute('style', cleanedStyle);
      }
    });
    
    // 确保SVG本身没有外部引用
    svgElement.removeAttribute('href');
    svgElement.removeAttribute('xlink:href');
  }
  
  /**
   * 等待其他内容渲染完成
   */
  private async waitForOtherContentRender(containerElement: HTMLElement): Promise<void> {
    console.log('等待其他内容渲染...');
    
    // 等待LaTeX公式渲染
    await this.waitForLatexRender(containerElement);
    
    // 等待图片加载
    await this.waitForImagesLoad(containerElement);
    
    // 额外等待时间
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  /**
   * 生成PDF
   */
  private async generatePDF(containerElement: HTMLElement, title: string, html2canvas: any): Promise<void> {
    console.log('开始生成PDF...');
    
    // 强制重新计算布局
    containerElement.offsetHeight; // 触发重排
    
    // 获取容器尺寸
    const finalWidth = Math.max(containerElement.scrollWidth, containerElement.offsetWidth, 800);
    const finalHeight = Math.max(containerElement.scrollHeight, containerElement.offsetHeight);
    
    console.log('容器尺寸:', finalWidth, 'x', finalHeight);
    
    // 配置html2canvas选项
    const canvasOptions = {
      backgroundColor: '#ffffff',
      scale: 1.5,
      useCORS: true,
      allowTaint: true,
      logging: false,
      width: finalWidth,
      height: finalHeight,
      scrollX: 0,
      scrollY: 0,
      windowWidth: finalWidth,
      windowHeight: finalHeight,
      x: 0,
      y: 0
    };
    
    console.log('开始生成Canvas...');
    const canvas = await html2canvas(containerElement, canvasOptions);
    console.log('Canvas生成成功，尺寸:', canvas.width, 'x', canvas.height);
    
    // 创建PDF
    const imgData = canvas.toDataURL('image/jpeg', 0.95);
    const pdf = new jsPDF('p', 'mm', 'a4');
    
    // 计算PDF页面尺寸
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const margin = 15;
    const contentWidth = pdfWidth - 2 * margin;
    const contentHeight = pdfHeight - 2 * margin;
    
    // 计算图片在PDF中的尺寸
    const imgAspectRatio = canvas.width / canvas.height;
    const imgWidth = contentWidth;
    const imgHeight = contentWidth / imgAspectRatio;
    
    console.log('PDF尺寸计算:', {
      pdfWidth: pdfWidth + 'mm',
      pdfHeight: pdfHeight + 'mm',
      imgWidth: imgWidth + 'mm',
      imgHeight: imgHeight + 'mm',
      estimatedPages: Math.ceil(imgHeight / contentHeight)
    });
    
    // 分页处理
    let yPosition = 0;
    let pageCount = 0;
    
    while (yPosition < imgHeight) {
      if (pageCount > 0) {
        pdf.addPage();
      }
      
      const remainingHeight = imgHeight - yPosition;
      const currentPageHeight = Math.min(contentHeight, remainingHeight);
      
      const sourceY = (yPosition / imgHeight) * canvas.height;
      const sourceHeight = (currentPageHeight / imgHeight) * canvas.height;
      
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = Math.min(sourceHeight, canvas.height - sourceY);
      const pageCtx = pageCanvas.getContext('2d');
      
      if (pageCtx && pageCanvas.height > 0) {
        pageCtx.drawImage(
          canvas,
          0, sourceY, canvas.width, pageCanvas.height,
          0, 0, canvas.width, pageCanvas.height
        );
        
        const pageImgData = pageCanvas.toDataURL('image/jpeg', 0.95);
        pdf.addImage(pageImgData, 'JPEG', margin, margin, imgWidth, currentPageHeight);
      }
      
      yPosition += currentPageHeight;
      pageCount++;
      
      if (pageCount > 100) {
        console.warn('页数过多，停止分页');
        break;
      }
    }
    
    // 保存PDF
    const filename = `${title || '笔记'}.pdf`;
    pdf.save(filename);
    
    console.log('PDF导出成功:', filename, '共', pageCount, '页');
  }

  /**
   * 等待LaTeX公式渲染
   */
  private async waitForLatexRender(containerElement: HTMLElement): Promise<void> {
    console.log('等待LaTeX公式渲染...');
    
    // 查找LaTeX元素
    const latexElements = containerElement.querySelectorAll('.katex, .MathJax, [data-latex]');
    if (latexElements.length === 0) {
      console.log('没有找到LaTeX公式');
      return;
    }
    
    console.log('找到LaTeX元素数量:', latexElements.length);
    
    // 等待LaTeX渲染完成
    let attempts = 0;
    const maxAttempts = 20;
    
    while (attempts < maxAttempts) {
      let allRendered = true;
      
      for (const element of latexElements) {
        const htmlElement = element as HTMLElement;
        if (htmlElement.offsetWidth === 0 || htmlElement.offsetHeight === 0) {
          allRendered = false;
          break;
        }
      }
      
      if (allRendered) {
        console.log('LaTeX公式渲染完成');
        return;
      }
      
      await new Promise(resolve => setTimeout(resolve, 100));
      attempts++;
    }
    
    console.warn('LaTeX公式渲染等待超时');
  }
  
  /**
   * 等待图片加载完成
   */
  private async waitForImagesLoad(containerElement: HTMLElement): Promise<void> {
    console.log('等待图片加载...');
    
    const images = containerElement.querySelectorAll('img');
    if (images.length === 0) {
      console.log('没有找到图片');
      return;
    }
    
    console.log('找到图片数量:', images.length);
    
    const imagePromises = Array.from(images).map(img => {
      return new Promise((resolve) => {
        if (img.complete) {
          resolve(true);
        } else {
          img.onload = () => resolve(true);
          img.onerror = () => resolve(false);
          // 超时处理
          setTimeout(() => resolve(false), 5000);
        }
      });
    });
    
    await Promise.all(imagePromises);
    console.log('图片加载完成');
  }
}

export default new PDFExportService(); 