import axios from 'axios';

const API_URL = 'http://101.42.168.191:18000/api/upload';

interface UploadResponse {
  success: boolean;
  message: string;
  file_info: {
    filename: string;
    saved_as: string;
    content_type: string;
    file_type: string;
    file_size: number;
    file_path: string;
    url: string;
  };
}

/**
 * 上传图片到服务器
 * @param file 图片文件
 * @param folder 可选的文件夹参数
 * @returns 上传成功后的图片URL
 */
export const uploadImage = async (file: File, folder: string = ''): Promise<string> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);

    const response = await axios.post<UploadResponse>(API_URL, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    if (response.data.success) {
      return response.data.file_info.url;
    } else {
      throw new Error(response.data.message || '图片上传失败');
    }
  } catch (error) {
    console.error('上传图片失败:', error);
    throw error;
  }
};

/**
 * 从Base64数据URL创建文件并上传
 * @param dataUrl Base64格式的图片数据
 * @param fileName 文件名
 * @returns 上传成功后的图片URL
 */
export const uploadImageFromDataUrl = async (dataUrl: string, fileName: string = 'pasted-image.png'): Promise<string> => {
  try {
    // 从dataUrl中提取MIME类型和Base64数据
    const match = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
    if (!match) {
      throw new Error('无效的图片数据格式');
    }

    const [, mimeType, base64Data] = match;
    
    // 将Base64转换为Blob
    const byteCharacters = atob(base64Data);
    const byteArrays = [];
    
    for (let i = 0; i < byteCharacters.length; i += 512) {
      const slice = byteCharacters.slice(i, i + 512);
      const byteNumbers = new Array(slice.length);
      
      for (let j = 0; j < slice.length; j++) {
        byteNumbers[j] = slice.charCodeAt(j);
      }
      
      const byteArray = new Uint8Array(byteNumbers);
      byteArrays.push(byteArray);
    }
    
    const blob = new Blob(byteArrays, { type: mimeType });
    
    // 创建File对象
    const file = new File([blob], fileName, { type: mimeType });
    
    // 上传文件
    return await uploadImage(file);
  } catch (error) {
    console.error('从数据URL上传图片失败:', error);
    throw error;
  }
};

export default {
  uploadImage,
  uploadImageFromDataUrl
}; 