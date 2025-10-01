import type { AuthProvider } from '@refinedev/core';
import { apiService } from '../../services/api';
import type { AuthUser, LoginRequest } from '../../types';

export const authProvider: AuthProvider = {
  login: async ({ email, password, tenant_id }: LoginRequest) => {
    try {
      const response = await apiService.login({ email, password, tenant_id });
      
      // Store user data
      localStorage.setItem('user', JSON.stringify(response.user));
      
      return {
        success: true,
        redirectTo: '/',
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          name: 'LoginError',
          message: error?.response?.data?.message || 'Login failed',
        },
      };
    }
  },

  logout: async () => {
    try {
      await apiService.logout();
    } catch (error) {
      // Continue with logout even if API call fails
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      localStorage.removeItem('current_tenant_id');
      localStorage.removeItem('session_id');
      sessionStorage.removeItem('post_login_redirect');
    }

    return {
      success: true,
      redirectTo: '/login',
    };
  },

  check: async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      return {
        authenticated: false,
        redirectTo: '/login',
      };
    }

    try {
      // Verify token is still valid
      await apiService.getCurrentUser();
      return {
        authenticated: true,
      };
    } catch (error) {
      return {
        authenticated: false,
        redirectTo: '/login',
      };
    }
  },

  getPermissions: async () => {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;

    try {
      const user: AuthUser = JSON.parse(userStr);
      return user.permissions || [];
    } catch (error) {
      return null;
    }
  },

  getIdentity: async () => {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;

    try {
      const user: AuthUser = JSON.parse(userStr);
      return {
        id: user.id,
        name: `${user.first_name} ${user.last_name}`.trim() || user.username,
        email: user.email,
        avatar: undefined, // Add avatar URL if available in backend
      };
    } catch (error) {
      return null;
    }
  },

  onError: async (error) => {
    if (error?.response?.status === 401) {
      return {
        logout: true,
        redirectTo: '/login',
      };
    }

    return {
      error: {
        message: error?.message || 'An error occurred',
        name: error?.name || 'Error',
      },
    };
  },
};

export default authProvider;