import api from './api';
import { API_ENDPOINTS } from '../config/api';
import {
  ImageEnhanceRequest,
  ImageEnhanceResponse,
  VideoEnhanceRequest,
  VideoEnhanceResponse,
  ImageListResponse,
  VideoListResponse,
  ImageDetailResponse,
  VideoDetailResponse,
} from '../types/media';

export const mediaService = {
  async enhanceImage(data: ImageEnhanceRequest): Promise<ImageEnhanceResponse> {
    const response = await api.post<ImageEnhanceResponse>(
      API_ENDPOINTS.IMAGES.ENHANCE,
      data
    );
    return response.data;
  },

  async enhanceVideo(data: VideoEnhanceRequest): Promise<VideoEnhanceResponse> {
    const response = await api.post<VideoEnhanceResponse>(
      API_ENDPOINTS.VIDEOS.ENHANCE,
      data
    );
    return response.data;
  },

  async getImageHistory(page: number = 1, perPage: number = 10): Promise<ImageListResponse> {
    const response = await api.get<ImageListResponse>(
      `${API_ENDPOINTS.IMAGES.LIST}?page=${page}&per_page=${perPage}`
    );
    return response.data;
  },

  async getVideoHistory(page: number = 1, perPage: number = 10): Promise<VideoListResponse> {
    const response = await api.get<VideoListResponse>(
      `${API_ENDPOINTS.VIDEOS.LIST}?page=${page}&per_page=${perPage}`
    );
    return response.data;
  },

  async getImageDetail(id: string): Promise<ImageDetailResponse> {
    const response = await api.get<ImageDetailResponse>(
      API_ENDPOINTS.IMAGES.DETAIL(id)
    );
    return response.data;
  },

  async getVideoDetail(id: string): Promise<VideoDetailResponse> {
    const response = await api.get<VideoDetailResponse>(
      API_ENDPOINTS.VIDEOS.DETAIL(id)
    );
    return response.data;
  },

  fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const result = reader.result as string;
        // Remove the data URL prefix (e.g., "data:image/png;base64,")
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = (error) => reject(error);
    });
  },

  downloadBase64File(base64: string, filename: string, mimeType: string): void {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: mimeType });

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  },

  getEnhancedFilename(originalFilename: string): string {
    const lastDotIndex = originalFilename.lastIndexOf('.');
    if (lastDotIndex === -1) {
      return `${originalFilename}_enhanced`;
    }
    const name = originalFilename.substring(0, lastDotIndex);
    const ext = originalFilename.substring(lastDotIndex);
    return `${name}_enhanced${ext}`;
  },

  getMimeType(filename: string): string {
    const ext = filename.toLowerCase().split('.').pop();
    const mimeTypes: Record<string, string> = {
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      png: 'image/png',
      webp: 'image/webp',
      gif: 'image/gif',
      mp4: 'video/mp4',
      mkv: 'video/x-matroska',
      avi: 'video/x-msvideo',
      mov: 'video/quicktime',
      webm: 'video/webm',
    };
    return mimeTypes[ext || ''] || 'application/octet-stream';
  },

  isValidImageFile(file: File): boolean {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    return validTypes.includes(file.type);
  },

  isValidVideoFile(file: File): boolean {
    const validTypes = ['video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime', 'video/webm'];
    return validTypes.includes(file.type) || file.name.toLowerCase().endsWith('.mkv');
  },

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },
};

export default mediaService;
