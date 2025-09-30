import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type { 
  LoginRequest, 
  LoginResponse, 
  ApiResponse,
  PaginatedResponse,
  ListParams 
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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
  }

  private getCurrentTenantId(): string | null {
    return localStorage.getItem('current_tenant_id');
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await this.api.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    const { access_token, refresh_token, user } = response.data;
    this.setTokens(access_token, refresh_token);
    
    // Set current tenant
    if (user.current_tenant) {
      localStorage.setItem('current_tenant_id', user.current_tenant.id);
    }

    return response.data;
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await this.api.post<LoginResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout');
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
    
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.size) queryParams.append('size', params.size.toString());
    if (params.sort) queryParams.append('sort', params.sort);
    if (params.order) queryParams.append('order', params.order);
    if (params.search) queryParams.append('search', params.search);
    
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
    const response = await this.api.get('/auth/me');
    return response.data;
  }

  async switchTenant(tenantId: string) {
    const response = await this.api.post('/auth/switch-tenant', { tenant_id: tenantId });
    localStorage.setItem('current_tenant_id', tenantId);
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