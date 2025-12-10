import api, { setTokens, clearTokens, getRefreshToken } from './api';
import { API_ENDPOINTS } from '../config/api';
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
  MeResponse,
} from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      credentials
    );

    const { tokens } = response.data;
    setTokens(tokens.access_token, tokens.refresh_token);

    return response.data;
  },

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    const response = await api.post<RegisterResponse>(
      API_ENDPOINTS.AUTH.REGISTER,
      data
    );
    return response.data;
  },

  async logout(): Promise<void> {
    const refreshToken = getRefreshToken();

    try {
      if (refreshToken) {
        await api.post(API_ENDPOINTS.AUTH.LOGOUT, {
          refresh_token: refreshToken,
        });
      }
    } finally {
      clearTokens();
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<MeResponse>(API_ENDPOINTS.AUTH.ME);
    return response.data.user;
  },

  async refreshToken(): Promise<string> {
    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await api.post(API_ENDPOINTS.AUTH.REFRESH, {
      refresh_token: refreshToken,
    });

    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);

    return access_token;
  },
};

export default authService;
