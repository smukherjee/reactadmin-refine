import React from 'react';
import { useList } from '@refinedev/core';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  CircularProgress,
  Stack,
} from '@mui/material';
import {
  People as PeopleIcon,
  Security as SecurityIcon,
  Assignment as AssignmentIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';

import type { User, Role, AuditLog } from '../types';
import RBACGuard from '../components/rbac/RBACGuard';

interface StatCard {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'warning';
}

export const DashboardPage: React.FC = () => {
  const { 
    query: { data: usersData, isLoading: usersLoading } 
  } = useList<User>({
    resource: 'users',
    pagination: { pageSize: 5 },
  });

  const { 
    query: { data: rolesData, isLoading: rolesLoading } 
  } = useList<Role>({
    resource: 'roles',
    pagination: { pageSize: 5 },
  });

  const { 
    query: { data: auditLogsData, isLoading: auditLogsLoading } 
  } = useList<AuditLog>({
    resource: 'audit-logs',
    pagination: { pageSize: 10 },
    sorters: [{ field: 'created_at', order: 'desc' }],
  });

  const users = usersData?.data || [];
  const roles = rolesData?.data || [];
  const auditLogs = auditLogsData?.data || [];

  const stats: StatCard[] = [
    {
      title: 'Total Users',
      value: usersData?.total || 0,
      icon: <PeopleIcon fontSize="large" />,
      color: 'primary',
    },
    {
      title: 'Active Roles',
      value: rolesData?.total || 0,
      icon: <SecurityIcon fontSize="large" />,
      color: 'secondary',
    },
    {
      title: 'Recent Activities',
      value: auditLogsData?.total || 0,
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

  if (usersLoading || rolesLoading || auditLogsLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <RBACGuard permissions={['dashboard:read']} fallback={<Alert severity="warning">Access denied to dashboard</Alert>}>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>
          Dashboard
        </Typography>

        {/* Statistics Cards */}
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

        {/* Main Content */}
        <Box sx={{ 
          display: 'flex',
          gap: 3,
          flexDirection: { xs: 'column', md: 'row' },
        }}>
          {/* Recent Activity */}
          <Card sx={{ flex: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Recent Activity
              </Typography>
              
              {auditLogs.length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>User</TableCell>
                        <TableCell>Action</TableCell>
                        <TableCell>Resource</TableCell>
                        <TableCell>Time</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {auditLogs.slice(0, 5).map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>{log.user_id}</TableCell>
                          <TableCell>
                            <Chip
                              label={log.action}
                              size="small"
                              color={
                                log.action === 'create' ? 'success' :
                                log.action === 'update' ? 'primary' :
                                log.action === 'delete' ? 'error' : 'default'
                              }
                            />
                          </TableCell>
                          <TableCell>{log.resource}</TableCell>
                          <TableCell>
                            {new Date(log.created_at).toLocaleDateString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No recent activity
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Quick Stats
              </Typography>
              
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Active Users
                  </Typography>
                  <Typography variant="h6">
                    {users.filter(user => user.is_active).length} / {users.length}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    System Roles
                  </Typography>
                  <Typography variant="h6">
                    {roles.length}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Today's Activities
                  </Typography>
                  <Typography variant="h6">
                    {auditLogs.filter(log => 
                      new Date(log.created_at).toDateString() === new Date().toDateString()
                    ).length}
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    System Status
                  </Typography>
                  <Chip 
                    label="Healthy" 
                    color="success" 
                    size="small" 
                    sx={{ mt: 0.5 }}
                  />
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </RBACGuard>
  );
};