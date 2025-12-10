export type MediaType = 'image' | 'video';

export type ModelType = 'general_x4' | 'general_x2' | 'anime' | 'anime_video' | 'general_v3';

export interface ModelInfo {
  id: ModelType;
  name: string;
  description: string;
  icon: 'photo' | 'photo-2x' | 'anime' | 'video' | 'fast';
  scale: number;
}

export const MODELS: ModelInfo[] = [
  {
    id: 'general_x4',
    name: 'General 4x',
    description: 'Fotos reales, retratos, paisajes - Alta calidad',
    icon: 'photo',
    scale: 4,
  },
  {
    id: 'general_x2',
    name: 'General 2x',
    description: 'Fotos reales - Escala menor, más rápido',
    icon: 'photo-2x',
    scale: 2,
  },
  {
    id: 'anime',
    name: 'Anime',
    description: 'Anime, manga, ilustraciones',
    icon: 'anime',
    scale: 4,
  },
  {
    id: 'anime_video',
    name: 'Anime Video',
    description: 'Optimizado para frames de video anime',
    icon: 'video',
    scale: 4,
  },
  {
    id: 'general_v3',
    name: 'General V3',
    description: 'Uso general - Más rápido',
    icon: 'fast',
    scale: 4,
  },
];

export interface ImageEnhanceRequest {
  image_base64: string;
  filename: string;
  model_type: ModelType;
  scale?: number;
  face_enhance: boolean;
}

export interface VideoEnhanceRequest {
  video_base64: string;
  filename: string;
  model_type: ModelType;
  scale?: number;
  face_enhance: boolean;
}

export interface ImageEnhanceResponse {
  message: string;
  image: {
    id: string;
    original_filename: string;
    original_width: number;
    original_height: number;
    enhanced_width: number;
    enhanced_height: number;
    model_type: string;
    scale: number;
    face_enhance: boolean;
    status: string;
    processing_time_ms: number;
    gpu_used: boolean;
    created_at: string;
    completed_at: string;
    original_base64: string;
    enhanced_base64: string;
    error_message: string | null;
  };
}

export interface VideoEnhanceResponse {
  message: string;
  video: {
    id: string;
    original_filename: string;
    status: string;
    duration_seconds: number;
    fps: number;
    frame_count: number;
    original_width: number;
    original_height: number;
    frames_processed: number;
  };
}

export interface ProcessingState {
  mediaType: MediaType;
  file: File | null;
  filePreview: string | null;
  modelType: ModelType;
  faceEnhance: boolean;
  isProcessing: boolean;
  progress: number;
  error: string | null;
  success: string | null;
}

// History types
export type JobStatus = 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed' | 'error';

export interface ImageHistoryItem {
  id: string;
  original_filename: string;
  description?: string;
  original_width: number;
  original_height: number;
  enhanced_width: number | null;
  enhanced_height: number | null;
  model_type: string;
  scale: number;
  face_enhance: boolean;
  status: JobStatus;
  processing_time_ms: number | null;
  gpu_used: boolean | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface VideoHistoryItem {
  id: string;
  original_filename: string;
  description?: string;
  original_width: number;
  original_height: number;
  enhanced_width: number | null;
  enhanced_height: number | null;
  model_type: string;
  scale: number;
  face_enhance: boolean;
  status: JobStatus;
  duration_seconds: number;
  fps: number;
  frame_count: number;
  frames_processed: number;
  processing_time_ms: number | null;
  gpu_used: boolean | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface ImageListResponse {
  total: number;
  page: number;
  per_page: number;
  images: ImageHistoryItem[];
}

export interface VideoListResponse {
  total: number;
  page: number;
  per_page: number;
  videos: VideoHistoryItem[];
}

export interface ImageDetailResponse {
  image: ImageHistoryItem & {
    original_base64: string;
    enhanced_base64: string;
  };
}

export interface VideoDetailResponse {
  video: VideoHistoryItem & {
    original_base64: string | null;
    enhanced_base64: string | null;
  };
}
