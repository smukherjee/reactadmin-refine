import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useTenant } from '../../providers/tenant/TenantProvider';

interface TenantGuardProps {
  children: React.ReactNode;
}

export const TenantGuard: React.FC<TenantGuardProps> = ({ children }) => {
  const { currentTenant, isLoading } = useTenant();
  const location = useLocation();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '50vh',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // If no current tenant and not already on tenant selection page, redirect
  if (!currentTenant && location.pathname !== '/tenant-selection') {
    return <Navigate to="/tenant-selection" replace />;
  }

  // If on tenant selection page but has a tenant, redirect to dashboard
  if (currentTenant && location.pathname === '/tenant-selection') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default TenantGuard;