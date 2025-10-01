import React from 'react';
import { useRBAC } from '../../providers/rbac/RBACProvider';
import type { RBACGuardProps } from '../../types';
import { AccessDenied } from './AccessDenied';

const RBACGuard: React.FC<RBACGuardProps> = ({
  permissions = [],
  roles = [],
  requireAll = false,
  children,
  fallback,
}) => {
  const { hasRole, hasAnyPermission, hasAllPermissions } = useRBAC();

  // Check permissions
  let hasRequiredPermissions = true;
  if (permissions.length > 0) {
    hasRequiredPermissions = requireAll 
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions);
  }

  // Check roles
  let hasRequiredRoles = true;
  if (roles.length > 0) {
    hasRequiredRoles = requireAll
      ? roles.every(role => hasRole(role))
      : roles.some(role => hasRole(role));
  }

  const isAuthorized = hasRequiredPermissions && hasRequiredRoles;

  if (!isAuthorized) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <AccessDenied
        requiredPermissions={permissions}
        requiredRoles={roles}
        showHomeButton
      />
    );
  }

  return <>{children}</>;
};

export default RBACGuard;