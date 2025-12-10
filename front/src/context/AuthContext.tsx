import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { LoginRequest, RegisterRequest, AuthState } from '../types/auth';
import authService from '../services/authService';
import { getAccessToken, getRefreshToken, clearTokens } from '../services/api';

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: getAccessToken(),
    refreshToken: getRefreshToken(),
    isAuthenticated: false,
    isLoading: true,
  });

  const checkAuth = useCallback(async () => {
    const token = getAccessToken();

    if (!token) {
      setState((prev) => ({
        ...prev,
        isAuthenticated: false,
        isLoading: false,
        user: null,
      }));
      return;
    }

    try {
      const user = await authService.getCurrentUser();
      setState({
        user,
        accessToken: getAccessToken(),
        refreshToken: getRefreshToken(),
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      clearTokens();
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (credentials: LoginRequest): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      await authService.login(credentials);
      const user = await authService.getCurrentUser();

      setState({
        user,
        accessToken: getAccessToken(),
        refreshToken: getRefreshToken(),
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const register = async (data: RegisterRequest): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      await authService.register(data);
      setState((prev) => ({ ...prev, isLoading: false }));
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await authService.logout();
    } finally {
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  };

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
