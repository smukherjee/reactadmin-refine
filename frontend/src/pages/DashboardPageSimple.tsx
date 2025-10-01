import React from 'react';
import { Box, Typography, Alert } from '@mui/material';
import TenantSelector from '../components/tenant/TenantSelector';

export const DashboardPage: React.FC = () => {
  const tenantId = localStorage.getItem('current_tenant_id');
  const hasTenant = Boolean(tenantId);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Dashboard
      </Typography>

      {!hasTenant && (
        <Box sx={{ mb: 3 }}>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              <strong>No Tenant Selected</strong>
            </Typography>
            <Typography variant="body2">
              Please select a tenant to view detailed analytics and manage tenant-specific data.
            </Typography>
          </Alert>
          <Box sx={{ maxWidth: 400 }}>
            <TenantSelector />
          </Box>
        </Box>
      )}

      {hasTenant && (
        <Box>
          <Typography variant="h6" color="success.main">
            Tenant selected! Data loading will work now.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Current tenant: {tenantId}
          </Typography>
        </Box>
      )}
    </Box>
  );
};