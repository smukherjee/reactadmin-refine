import type { AuthProvider } from '@refinedev/core';
import { apiService } from '../../services/api';
import type { AuthUser, LoginRequest } from '../../types';

export const authProvider: AuthProvider = {
  login: async ({ email, password }: LoginRequest) => {
    try {
      const response = await apiService.login({ email, password });
      
      // User data is already stored by the login method, including tenant info
      console.log('Login successful, user data:', response.user);
      
      return {
        success: true,
        redirectTo: '/',
      };
    } catch (error: any) {
      console.error('Login error:', error);
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
    const userStr = localStorage.getItem('user');
    
    if (!token || !userStr) {
      return {
        authenticated: false,
        redirectTo: '/login',
      };
    }

    try {
            // For v2 API, we rely on stored user data and token validity\n      // The token will be rejected by API if invalid, so we consider user authenticated if both exist\n      JSON.parse(userStr); // Validate JSON format
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