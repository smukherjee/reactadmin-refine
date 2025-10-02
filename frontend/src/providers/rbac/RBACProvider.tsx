import React, { createContext, useContext, useEffect, useState } from 'react';
import type { AuthUser, RBACContext as IRBACContext, Role } from '../../types';

const RBACContext = createContext<IRBACContext | null>(null);

interface RBACProviderProps {
  children: React.ReactNode;
}

export const RBACProvider: React.FC<RBACProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const userData: AuthUser = JSON.parse(userStr);
        console.log('RBAC Provider loading user data:', {
          userId: userData.id,
          email: userData.email,
          is_superuser: userData.is_superuser,
          permissions: userData.permissions,
          roles: userData.roles
        });
        setUser(userData);
        
        // If user is superadmin but has no permissions, provide comprehensive default permissions
        let userPermissions = userData.permissions || [];
        if (userData.is_superuser && userPermissions.length === 0) {
          userPermissions = [
            'dashboard:read',
            'read:users', 'create:users', 'update:users', 'delete:users',
            'read:roles', 'create:roles', 'update:roles', 'delete:roles',
            'read:audit_logs',
            'tenant:manage', 'tenant:switch'
          ];
          console.log('Superadmin user detected with no permissions, providing default permissions:', userPermissions);
        }
        
        setPermissions(userPermissions);
        setRoles(userData.roles || []);
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    } finally {
      setLoading(false);
    }
  };

  const hasPermission = (permission: string): boolean => {
    console.log('RBAC hasPermission check:', {
      permission,
      user: user ? { id: user.id, email: user.email, is_superuser: user.is_superuser } : null,
      permissions,
      result: user ? (user.is_superuser ? true : permissions.includes(permission)) : false
    });
    
    if (!user) return false;
    if (user.is_superuser) return true;
    return permissions.includes(permission);
  };

  const hasRole = (roleName: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return roles.some(role => role.name.toLowerCase() === roleName.toLowerCase());
  };

  const hasAnyPermission = (requiredPermissions: string[]): boolean => {
    console.log('RBAC hasAnyPermission check:', {
      requiredPermissions,
      user: user ? { id: user.id, email: user.email, is_superuser: user.is_superuser } : null,
      permissions,
      result: user ? (user.is_superuser ? true : requiredPermissions.some(permission => permissions.includes(permission))) : false
    });
    
    if (!user) return false;
    if (user.is_superuser) return true;
    return requiredPermissions.some(permission => permissions.includes(permission));
  };

  const hasAllPermissions = (requiredPermissions: string[]): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return requiredPermissions.every(permission => permissions.includes(permission));
  };

  const contextValue: IRBACContext = {
    user,
    permissions,
    roles,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <RBACContext.Provider value={contextValue}>
      {children}
    </RBACContext.Provider>
  );
};

export const useRBAC = (): IRBACContext => {
  const context = useContext(RBACContext);
  if (!context) {
    throw new Error('useRBAC must be used within a RBACProvider');
  }
  return context;
};

export default RBACProvider;