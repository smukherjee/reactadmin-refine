import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type {
  LoginRequest,
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
  async   login(credentials: { email: string; password: string; tenant_id?: string | null }): Promise<LoginResponse> {
    const payload: Record<string, string> = {
      email: credentials.email,
      password: credentials.password,
    };

    if (credentials.tenant_id) {
      payload.tenant_id = credentials.tenant_id;
    }

    const response = await this.api.post<LoginResponse>('/auth/login', payload);

    const { access_token, refresh_token, user, session_id } = response.data;
    this.setTokens(access_token, refresh_token);
    if (session_id) {
      localStorage.setItem('session_id', session_id);
    }
    
    // Store user data for tenant management
    localStorage.setItem('user', JSON.stringify(user));
    
    // Set current tenant
    if (user.current_tenant) {
      localStorage.setItem('current_tenant_id', user.current_tenant.id);
    }

    return response.data;
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
    if (['users', 'roles', 'audit-logs'].includes(resource)) {
      if (!tenantId) {
        throw new Error(`Tenant ID is required for ${resource} operations. Please switch tenant or login again.`);
      }
      queryParams.append('tenant_id', tenantId);
    }
    
    // Add filters
    if (params.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          queryParams.append(key, value.toString());
        }
      });
    }

    const response = await this.api.get<PaginatedResponse<T>>(
      `/${resource}?${queryParams.toString()}`
    );
    return response.data;
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
  async getCurrentUser() {
    try {
      const response = await this.api.get('/async/users/me');
      const userData = response.data;
      
      // If user has a tenant_id but no current_tenant, fetch tenant info
      if (userData.tenant_id && !userData.current_tenant) {
        try {
          // Fetch user roles to determine access level
          let userRoles = userData.roles || [];
          if (!userRoles.length) {
            try {
              const rolesResponse = await this.api.get(`/users/${userData.id}/roles`);
              userRoles = Array.isArray(rolesResponse.data) ? rolesResponse.data : rolesResponse.data.data || [];
            } catch (roleError) {
              console.warn('Could not fetch user roles:', roleError);
            }
          }
          
          // Check if user is superadmin by checking their roles
          const isSuperAdmin = userRoles.some((role: any) => 
            role.name === 'superadmin' || 
            (role.permissions && role.permissions.includes('*'))
          );
          
          if (isSuperAdmin) {
            // Superadmin can access all tenants
            const allTenantsResponse = await this.api.get('/tenants');
            const allTenants = Array.isArray(allTenantsResponse.data) 
              ? allTenantsResponse.data 
              : allTenantsResponse.data.data || [];
            
            userData.available_tenants = allTenants.map((tenant: any) => ({
              id: tenant.id,
              name: tenant.name,
              domain: tenant.domain
            }));
            
            // Check if there's a stored current tenant
            const storedTenantId = localStorage.getItem('current_tenant_id');
            if (storedTenantId) {
              userData.current_tenant = userData.available_tenants.find(
                (tenant: any) => tenant.id === storedTenantId
              ) || null;
            }
            
            // If no current tenant selected, superadmin needs to choose
            if (!userData.current_tenant && userData.available_tenants.length > 0) {
              userData.current_tenant = null; // Force tenant selection
            }
          } else {
            // Regular user - tied to their specific tenant
            const tenantResponse = await this.api.get(`/tenants/${userData.tenant_id}`);
            const tenantData = tenantResponse.data;
            
            userData.current_tenant = {
              id: tenantData.id,
              name: tenantData.name,
              domain: tenantData.domain
            };
            
            // Regular users only have access to their assigned tenant
            userData.available_tenants = [userData.current_tenant];
            
            // Auto-set the tenant for regular users
            localStorage.setItem('current_tenant_id', tenantData.id);
          }
        } catch (tenantError) {
          console.warn('Could not fetch tenant info:', tenantError);
        }
      }
      
      return userData;
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  }

  async switchTenant(tenantId: string) {
    const response = await this.api.post('/auth/switch-tenant', { tenant_id: tenantId });
    localStorage.setItem('current_tenant_id', tenantId);
    return response.data;
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