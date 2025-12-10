export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8888';

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/auth/login',
    REGISTER: '/api/auth/register',
    REFRESH: '/api/auth/refresh',
    LOGOUT: '/api/auth/logout',
    ME: '/api/auth/me',
  },
  IMAGES: {
    ENHANCE: '/api/images/enhance',
    LIST: '/api/images',
    DETAIL: (id: string) => `/api/images/${id}`,
  },
  VIDEOS: {
    ENHANCE: '/api/videos/enhance',
    LIST: '/api/videos',
    DETAIL: (id: string) => `/api/videos/${id}`,
  },
  SYSTEM: {
    HEALTH: '/api/health',
    INFO: '/api/info',
    MODELS: '/api/models',
  },
};
