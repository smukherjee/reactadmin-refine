import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type {
  LoginResponse,
  RefreshResponse,
  ApiResponse,
  PaginatedResponse,
  ListParams,
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = (import.meta.env.VITE_API_URL || '/api/v2').replace(/\/$/, '');
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token and tenant ID
    this.api.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        const tenantId = this.getCurrentTenantId();

        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }

        if (tenantId) {
          config.headers['X-Tenant-ID'] = tenantId;
          console.log(`API Request: ${config.method?.toUpperCase()} ${config.url} with tenant ${tenantId}`);
        } else {
          console.warn(`API Request: ${config.method?.toUpperCase()} ${config.url} WITHOUT tenant ID`);
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh and errors
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = this.getRefreshToken();
            if (refreshToken) {
              const response = await this.refreshToken(refreshToken);
              this.setTokens(response.access_token, response.refresh_token);
              
              // Retry the original request with new token
              originalRequest.headers['Authorization'] = `Bearer ${response.access_token}`;
              return this.api(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        // Log API errors for debugging
        console.error('API Error:', {
          url: error.config?.url,
          method: error.config?.method,
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          headers: error.config?.headers
        });

        return Promise.reject(error);
      }
    );
  }

  // Token management
  private getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('current_tenant_id');
    localStorage.removeItem('session_id');
    localStorage.removeItem('user');
  }

  private getCurrentTenantId(): string | null {
    return localStorage.getItem('current_tenant_id');
  }

  // Auth endpoints
  async login(credentials: { email: string; password: string }): Promise<LoginResponse> {
    const payload: Record<string, string> = {
      email: credentials.email,
      password: credentials.password,
    };

    const response = await this.api.post<LoginResponse>('/auth/login', payload);

    const { access_token, refresh_token, user, session_id } = response.data;
    this.setTokens(access_token, refresh_token);
    if (session_id) {
      localStorage.setItem('session_id', session_id);
    }
    
    // Enhance user data with tenant information based on their role
    let enhancedUser = user;
    try {
      console.log('Starting tenant enhancement for user:', user);
      enhancedUser = await this.enhanceUserWithTenantData(user);
      console.log('Tenant enhancement completed:', enhancedUser);
      localStorage.setItem('user', JSON.stringify(enhancedUser));
      
      // Set current tenant if available
      if (enhancedUser.current_tenant) {
        localStorage.setItem('current_tenant_id', enhancedUser.current_tenant.id);
        console.log('Set current tenant ID in localStorage:', enhancedUser.current_tenant.id);
      }
    } catch (error) {
      console.error('Could not enhance user data with tenant info:', error);
      // Fallback to basic user data from login response
      localStorage.setItem('user', JSON.stringify(user));
      
      if (user.tenant_id) {
        localStorage.setItem('current_tenant_id', user.tenant_id);
        console.log('Fallback: Set user tenant_id in localStorage:', user.tenant_id);
      }
    }
    
    return {
      ...response.data,
      user: enhancedUser
    };
  }

  async refreshToken(refreshToken: string): Promise<RefreshResponse> {
    const response = await this.api.post<RefreshResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      const sessionId = localStorage.getItem('session_id');
      const config = sessionId
        ? {
            params: {
              session_id: sessionId,
            },
          }
        : undefined;

      await this.api.post('/auth/logout', null, config);
    } finally {
      this.clearTokens();
    }
  }

  // Generic CRUD operations
  async getList<T>(
    resource: string, 
    params: ListParams = {}
  ): Promise<PaginatedResponse<T>> {
    const queryParams = new URLSearchParams();
    
    // Convert page/size to skip/limit for backend compatibility
    if (params.page && params.size) {
      const skip = (params.page - 1) * params.size;
      queryParams.append('skip', skip.toString());
      queryParams.append('limit', params.size.toString());
    } else {
      if (params.size) queryParams.append('limit', params.size.toString());
    }
    
    if (params.sort) queryParams.append('sort', params.sort);
    if (params.order) queryParams.append('order', params.order);
    if (params.search) queryParams.append('search', params.search);
    
    // Add tenant_id for tenant-aware resources (REQUIRED by backend)
    const tenantId = this.getCurrentTenantId();
    console.log(`API getList for ${resource}: tenant_id = ${tenantId}`);
    
    if (['users', 'roles', 'audit-logs'].includes(resource)) {
      if (!tenantId) {
        console.error(`No tenant ID found for ${resource} operation`);
        throw new Error(`Tenant ID is required for ${resource} operations. Please switch tenant or login again.`);
      }
      queryParams.append('tenant_id', tenantId);
      console.log(`Added tenant_id=${tenantId} to ${resource} request`);
    }
    
    // Add filters
    if (params.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          queryParams.append(key, value.toString());
        }
      });
    }

    try {
      const response = await this.api.get<PaginatedResponse<T>>(
        `/${resource}?${queryParams.toString()}`
      );
      return response.data;
    } catch (error: any) {
      console.error(`Failed to fetch ${resource}:`, error.response?.data || error.message);
      
      // For roles specifically, return empty data instead of throwing
      if (resource === 'roles') {
        console.warn('Roles API failed, returning empty list as fallback');
        return {
          data: [],
          total: 0,
          page: 1,
          size: 10,
          pages: 1
        } as PaginatedResponse<T>;
      }
      
      throw error;
    }
  }

  async getOne<T>(resource: string, id: string): Promise<T> {
    const response = await this.api.get<ApiResponse<T>>(`/${resource}/${id}`);
    return response.data.data;
  }

  async create<T>(resource: string, data: Partial<T>): Promise<T> {
    const response = await this.api.post<ApiResponse<T>>(`/${resource}`, data);
    return response.data.data;
  }

  async update<T>(resource: string, id: string, data: Partial<T>): Promise<T> {
    const response = await this.api.put<ApiResponse<T>>(`/${resource}/${id}`, data);
    return response.data.data;
  }

  async delete(resource: string, id: string): Promise<void> {
    await this.api.delete(`/${resource}/${id}`);
  }

  async deleteMany(resource: string, ids: string[]): Promise<void> {
    await this.api.post(`/${resource}/bulk-delete`, { ids });
  }

  // Custom endpoints
  async enhanceUserWithTenantData(user: any) {
    try {
      // Ensure we have an access token for API calls
      const token = this.getToken();
      if (!token) {
        console.warn('No access token available for tenant enhancement');
        return user;
      }
      
      // Check if user is superadmin by checking their roles
      const userRoles = user.roles || [];
      const isSuperAdmin = userRoles.includes('superadmin') || 
                          userRoles.includes('admin') || 
                          user.is_superuser;
      
      console.log('Enhancing user with tenant data:', { 
        user, 
        userRoles, 
        isSuperAdmin,
        user_tenant_id: user.tenant_id,
        is_superuser: user.is_superuser,
        has_token: !!token
      });
      
      if (isSuperAdmin) {
        // Superadmin can access all tenants
        try {
          console.log('Fetching all tenants for superadmin...');
          const allTenantsResponse = await this.api.get('/tenants');
          console.log('Tenants API response:', allTenantsResponse);
          
          const allTenants = Array.isArray(allTenantsResponse.data) 
            ? allTenantsResponse.data 
            : allTenantsResponse.data.data || [];
          
          console.log('Processed tenants:', allTenants);
          
          user.available_tenants = allTenants.map((tenant: any) => ({
            id: tenant.id,
            name: tenant.name,
            domain: tenant.domain
          }));
          
          console.log('User available_tenants after mapping:', user.available_tenants);
          
          // Check if there's a stored current tenant
          const storedTenantId = localStorage.getItem('current_tenant_id');
          console.log('Stored tenant ID:', storedTenantId);
          
          if (storedTenantId && user.available_tenants.length > 0) {
            user.current_tenant = user.available_tenants.find(
              (tenant: any) => tenant.id === storedTenantId
            ) || null;
            console.log('Found matching stored tenant:', user.current_tenant);
          }
          
          // If superadmin has only one tenant, auto-assign it
          if (!user.current_tenant && user.available_tenants.length === 1) {
            user.current_tenant = user.available_tenants[0];
            localStorage.setItem('current_tenant_id', user.available_tenants[0].id);
            console.log('Auto-assigned single tenant for superadmin:', user.current_tenant);
          }
          // If multiple tenants and no current selection, force selection
          else if (!user.current_tenant && user.available_tenants.length > 1) {
            user.current_tenant = null; // Force tenant selection
            console.log('Multiple tenants available, forcing selection');
          }
          
          console.log('Final superadmin tenant data:', { 
            available: user.available_tenants, 
            current: user.current_tenant,
            available_count: user.available_tenants.length 
          });
        } catch (tenantFetchError) {
          console.error('Superadmin could not fetch all tenants:', tenantFetchError);
          console.log('Error details:', {
            status: (tenantFetchError as any).response?.status,
            statusText: (tenantFetchError as any).response?.statusText,
            data: (tenantFetchError as any).response?.data,
            message: (tenantFetchError as any).message
          });
          
          // Fallback to user's assigned tenant if fetching all tenants fails
          if (user.tenant_id) {
            try {
              console.log('Trying fallback: fetching single tenant:', user.tenant_id);
              const tenantResponse = await this.api.get(`/tenants/${user.tenant_id}`);
              const tenantData = tenantResponse.data;
              
              user.current_tenant = {
                id: tenantData.id,
                name: tenantData.name,
                domain: tenantData.domain
              };
              user.available_tenants = [user.current_tenant];
              localStorage.setItem('current_tenant_id', tenantData.id);
              console.log('Fallback successful, assigned single tenant:', user.current_tenant);
            } catch (singleTenantError) {
              console.error('Could not fetch user\'s assigned tenant:', singleTenantError);
              console.log('Single tenant error details:', {
                status: (singleTenantError as any).response?.status,
                data: (singleTenantError as any).response?.data
              });
            }
          } else {
            console.warn('No tenant_id found for user, cannot fetch tenant data');
          }
        }
      } else {
        // Regular user - tied to their specific tenant
        if (user.tenant_id) {
          try {
            const tenantResponse = await this.api.get(`/tenants/${user.tenant_id}`);
            const tenantData = tenantResponse.data;
            
            user.current_tenant = {
              id: tenantData.id,
              name: tenantData.name,
              domain: tenantData.domain
            };
            
            // Regular users only have access to their assigned tenant
            user.available_tenants = [user.current_tenant];
            
            // Auto-set the tenant for regular users
            localStorage.setItem('current_tenant_id', tenantData.id);
            
            console.log('Regular user tenant data:', { current: user.current_tenant });
          } catch (tenantError) {
            console.warn('Could not fetch user\'s assigned tenant:', tenantError);
          }
        }
      }
      
      return user;
    } catch (error) {
      console.error('ERROR in enhanceUserWithTenantData:', error);
      console.error('Error type:', typeof error);
      console.error('Error details:', {
        message: (error as any)?.message,
        response: (error as any)?.response,
        stack: (error as any)?.stack
      });
      return user;
    }
  }
  
  async getCurrentUser() {
    // For v2 API, we get user data from login response and enhance it
    // This method is kept for compatibility but now just returns stored user data
    const userStr = localStorage.getItem('user');
    if (!userStr) {
      throw new Error('No user data found');
    }
    return JSON.parse(userStr);
  }

  async switchTenant(tenantId: string) {
    // For v2 API, we handle tenant switching on the frontend
    // No backend call needed since users already have access to their allowed tenants
    localStorage.setItem('current_tenant_id', tenantId);
    console.log('Updated current_tenant_id in localStorage:', tenantId);
    return { success: true };
  }

  async getTenants() {
    const response = await this.api.get('/tenants');
    return response.data;
  }

  async getUserPermissions(userId: string) {
    const response = await this.api.get(`/users/${userId}/permissions`);
    return response.data;
  }

  async getUserRoles(userId: string) {
    const response = await this.api.get(`/users/${userId}/roles`);
    return response.data;
  }

  async assignRole(userId: string, roleId: string) {
    const response = await this.api.post(`/users/${userId}/roles`, { role_id: roleId });
    return response.data;
  }

  async removeRole(userId: string, roleId: string) {
    const response = await this.api.delete(`/users/${userId}/roles/${roleId}`);
    return response.data;
  }

  async getAuditLogs(params: ListParams = {}) {
    return this.getList('audit-logs', params);
  }

  // Health check
  async healthCheck() {
    const response = await this.api.get('/health');
    return response.data;
  }

  // Utility methods
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    const tenantId = this.getCurrentTenantId();
    
    const headers: Record<string, string> = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (tenantId) {
      headers['X-Tenant-ID'] = tenantId;
    }
    
    return headers;
  }
}

export const apiService = new ApiService();
export default apiService;