import React from 'react';
import { useList } from '@refinedev/core';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  People as PeopleIcon,
  Security as SecurityIcon,
  Assignment as AssignmentIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';

import type { User, Role, AuditLog } from '../types';
import RBACGuard from '../components/rbac/RBACGuard';
import TenantSelector from '../components/tenant/TenantSelector';

interface StatCard {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'warning';
}

export const DashboardPage: React.FC = () => {
  const tenantId = localStorage.getItem('current_tenant_id');
  const hasTenant = Boolean(tenantId);

  const { data: usersData, isLoading: usersLoading, error: usersError } = useList<User>({
    resource: 'users',
    pagination: { pageSize: 5 },
    queryOptions: {
      enabled: hasTenant,
    },
  });

  const { data: rolesData, isLoading: rolesLoading, error: rolesError } = useList<Role>({
    resource: 'roles',
    pagination: { pageSize: 5 },
    queryOptions: {
      enabled: hasTenant,
    },
  });

  const { data: auditLogsData, isLoading: auditLogsLoading, error: auditError } = useList<AuditLog>({
    resource: 'audit-logs',
    pagination: { pageSize: 10 },
    sorters: [{ field: 'created_at', order: 'desc' }],
    queryOptions: {
      enabled: hasTenant,
    },
  });

  const stats: StatCard[] = [
    {
      title: 'Total Users',
      value: hasTenant ? (usersData?.total || 0) : 0,
      icon: <PeopleIcon fontSize="large" />,
      color: 'primary',
    },
    {
      title: 'Active Roles',
      value: hasTenant ? (rolesData?.total || 0) : 0,
      icon: <SecurityIcon fontSize="large" />,
      color: 'secondary',
    },
    {
      title: 'Recent Activities',
      value: hasTenant ? (auditLogsData?.total || 0) : 0,
      icon: <AssignmentIcon fontSize="large" />,
      color: 'success',
    },
    {
      title: 'System Health',
      value: 98,
      icon: <TrendingUpIcon fontSize="large" />,
      color: 'warning',
    },
  ];

  if (hasTenant && (usersLoading || rolesLoading || auditLogsLoading)) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <RBACGuard permissions={['dashboard:read']}>
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

        {hasTenant && (usersError || rolesError || auditError) && (
          <Alert severity="error" sx={{ mb: 3 }}>
            <Typography variant="body2">
              Some data could not be loaded. This might be due to insufficient permissions or connectivity issues.
            </Typography>
          </Alert>
        )}

        <Box sx={{ 
          display: 'flex',
          flexWrap: 'wrap',
          gap: 3,
          mb: 4,
        }}>
          {stats.map((stat, index) => (
            <Card 
              key={index}
              sx={{ 
                flex: '1 1 250px',
                minWidth: 200,
                maxWidth: 300,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box sx={{ color: `${stat.color}.main` }}>
                    {stat.icon}
                  </Box>
                  <Box>
                    <Typography variant="h4" component="div">
                      {stat.value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {stat.title}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>

        {hasTenant && (
          <Typography variant="h6" color="success.main">
            ✅ Tenant selected! All data should load properly now.
          </Typography>
        )}

        {!hasTenant && (
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              Welcome to the Admin Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select a tenant above to access your organization's data and analytics.
            </Typography>
          </Box>
        )}
      </Box>
    </RBACGuard>
  );
};