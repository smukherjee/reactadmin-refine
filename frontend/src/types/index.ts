export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
  tenant_id: string;
  roles: Role[];
  permissions: string[];
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: string;
  name: string;
  description?: string;
  resource: string;
  action: string;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  domain?: string;
  is_active: boolean;
  settings?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  tenant_id: string;
  action: string;
  resource: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  tenant_id?: string;
  roles?: Role[];
  permissions?: string[];
  current_tenant?: Tenant;
  available_tenants?: Tenant[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  session_id: string;
  user: AuthUser;
  expires_in?: number;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface PaginationParams {
  page?: number;
  size?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T = any> {
  data: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface FilterParams {
  search?: string;
  filters?: Record<string, any>;
}

export interface ListParams extends PaginationParams, FilterParams {}

// RBAC Types
export type PermissionAction = 'create' | 'read' | 'update' | 'delete' | 'manage';
export type PermissionResource = 'users' | 'roles' | 'tenants' | 'audit_logs' | 'settings';

export interface RBACContext {
  user: AuthUser | null;
  permissions: string[];
  roles: Role[];
  hasPermission: (permission: string) => boolean;
  hasRole: (roleName: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

export interface TenantContext {
  currentTenant: Tenant | null;
  availableTenants: Tenant[];
  switchTenant: (tenantId: string) => void;
  isLoading: boolean;
}

// Component Props Types
export interface ProtectedRouteProps {
  children: React.ReactNode;
  permissions?: string[];
  roles?: string[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
}

export interface RBACGuardProps {
  permissions?: string[];
  roles?: string[];
  requireAll?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

// Form Types
export interface UserFormData {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  password?: string;
  confirm_password?: string;
  is_active: boolean;
  role_ids: string[];
}

export interface RoleFormData {
  name: string;
  description?: string;
  permission_ids: string[];
}

export interface TenantFormData {
  name: string;
  domain?: string;
  is_active: boolean;
  settings?: Record<string, any>;
}

// Table Column Types
export interface TableColumn<T = any> {
  field: keyof T;
  headerName: string;
  width?: number;
  sortable?: boolean;
  filterable?: boolean;
  renderCell?: (params: { row: T; value: any }) => React.ReactNode;
}

// API Error Types
export interface ApiError {
  message: string;
  details?: Record<string, any>;
  status: number;
  timestamp: string;
}

// Theme Types
export interface ThemeConfig {
  mode: 'light' | 'dark';
  primaryColor: string;
  secondaryColor: string;
}