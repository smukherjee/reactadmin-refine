import React, { useState } from 'react';
import { useList } from '@refinedev/core';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import RBACGuard from '../../components/rbac/RBACGuard';
import type { AuditLog } from '../../types';

const getActionColor = (action: string) => {
  switch (action.toLowerCase()) {
    case 'create':
      return 'success';
    case 'update':
      return 'info';
    case 'delete':
      return 'error';
    case 'login':
      return 'primary';
    case 'logout':
      return 'secondary';
    default:
      return 'default';
  }
};

export const AuditLogListPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');

  const filters = [];
  if (searchTerm) {
    filters.push({
      field: 'q',
      operator: 'contains' as const,
      value: searchTerm,
    });
  }
  if (actionFilter) {
    filters.push({
      field: 'action',
      operator: 'eq' as const,
      value: actionFilter,
    });
  }
  if (resourceFilter) {
    filters.push({
      field: 'resource',
      operator: 'eq' as const,
      value: resourceFilter,
    });
  }

  const { data, isLoading, isError } = useList<AuditLog>({
    resource: 'audit-logs',
    filters,
    sorters: [
      {
        field: 'created_at',
        order: 'desc',
      },
    ],
  });

  if (isError) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load audit logs. This may be due to missing tenant selection or insufficient permissions.
        </Alert>
      </Box>
    );
  }

  const auditLogs: AuditLog[] = data?.data ?? [];

  return (
    <RBACGuard permissions={['read:audit_logs']}>
      <Box p={3}>
        {/* Header */}
        <Box mb={3}>
          <Typography variant="h4" gutterBottom>
            Audit Logs
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Monitor system activities and user actions
          </Typography>
        </Box>

        {/* Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" gap={2} flexWrap="wrap">
              <TextField
                placeholder="Search by user or details..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ minWidth: 300, flexGrow: 1 }}
              />
              
              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel>Action</InputLabel>
                <Select
                  value={actionFilter}
                  label="Action"
                  onChange={(e) => setActionFilter(e.target.value)}
                >
                  <MenuItem value="">All Actions</MenuItem>
                  <MenuItem value="create">Create</MenuItem>
                  <MenuItem value="update">Update</MenuItem>
                  <MenuItem value="delete">Delete</MenuItem>
                  <MenuItem value="login">Login</MenuItem>
                  <MenuItem value="logout">Logout</MenuItem>
                </Select>
              </FormControl>

              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel>Resource</InputLabel>
                <Select
                  value={resourceFilter}
                  label="Resource"
                  onChange={(e) => setResourceFilter(e.target.value)}
                >
                  <MenuItem value="">All Resources</MenuItem>
                  <MenuItem value="users">Users</MenuItem>
                  <MenuItem value="roles">Roles</MenuItem>
                  <MenuItem value="tenants">Tenants</MenuItem>
                  <MenuItem value="auth">Authentication</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </CardContent>
        </Card>

        {/* Audit Logs Table */}
        <Card>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Timestamp</TableCell>
                  <TableCell>User</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell>Resource</TableCell>
                  <TableCell>Details</TableCell>
                  <TableCell>IP Address</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      Loading audit logs...
                    </TableCell>
                  </TableRow>
                ) : auditLogs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      No audit logs found
                    </TableCell>
                  </TableRow>
                ) : (
                  auditLogs.map((log: AuditLog) => (
                    <TableRow key={log.id} hover>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(log.created_at).toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="subtitle2">
                          {log.user_id || 'System'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.action}
                          size="small"
                          color={getActionColor(log.action) as any}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {log.resource}
                          {log.resource_id && (
                            <Typography variant="caption" display="block">
                              ID: {log.resource_id}
                            </Typography>
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            maxWidth: 200,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {log.details ? JSON.stringify(log.details) : 'No details'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {log.ip_address || 'Unknown'}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="View Details">
                          <IconButton size="small">
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      </Box>
    </RBACGuard>
  );
};

export default AuditLogListPage;