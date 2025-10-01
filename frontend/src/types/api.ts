// Enhanced types for better API integration
export interface BackendListResponse<T> {
  data: T[];
  total?: number;
  page?: number;
  pages?: number;
  size?: number;
}

export interface ApiErrorResponse {
  detail: string | { msg: string; type: string }[];
  message?: string;
}

export interface ListQueryParams {
  skip?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
  search?: string;
  tenant_id?: string;
  [key: string]: any;
}

// Better type for data provider responses
export interface DataProviderResponse<T> {
  data: T[];
  total: number;
}

// Authentication types with better error handling
export interface LoginError {
  message: string;
  code?: string;
  field?: string;
}

export interface AuthResponse {
  success: boolean;
  error?: LoginError;
  redirectTo?: string;
}

// Enhanced user types to match backend
export interface BackendUser {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
  tenant_id: string;
  roles?: BackendRole[];
  permissions?: string[];
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface BackendRole {
  id: string;
  name: string;
  description?: string;
  permissions?: BackendPermission[];
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface BackendPermission {
  id: string;
  name: string;
  description?: string;
  resource: string;
  action: string;
  created_at: string;
  updated_at: string;
}

export interface BackendAuditLog {
  id: string;
  user_id: string;
  tenant_id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  changes_json?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

// API validation types
export interface ValidationError {
  field: string;
  message: string;
  type: string;
}

export interface ApiValidationResponse {
  detail: ValidationError[];
}