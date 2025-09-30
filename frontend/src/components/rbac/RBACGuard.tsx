import React from 'react';
import { Typography, Paper } from '@mui/material';
import { Lock as LockIcon } from '@mui/icons-material';
import { useRBAC } from '../../providers/rbac/RBACProvider';
import type { RBACGuardProps } from '../../types';

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
      <Paper 
        elevation={1} 
        sx={{ 
          p: 4, 
          textAlign: 'center', 
          backgroundColor: 'grey.50',
          border: '1px solid',
          borderColor: 'grey.300'
        }}
      >
        <LockIcon 
          sx={{ 
            fontSize: 48, 
            color: 'grey.400',
            mb: 2
          }} 
        />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="body2" color="text.secondary">
          You don't have the required permissions to view this content.
        </Typography>
        {permissions.length > 0 && (
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            Required permissions: {permissions.join(', ')}
          </Typography>
        )}
        {roles.length > 0 && (
          <Typography variant="caption" display="block">
            Required roles: {roles.join(', ')}
          </Typography>
        )}
      </Paper>
    );
  }

  return <>{children}</>;
};

export default RBACGuard;