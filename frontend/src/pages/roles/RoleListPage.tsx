import React, { useState } from 'react';
import { useList } from '@refinedev/core';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
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
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Search as SearchIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import RBACGuard from '../../components/rbac/RBACGuard';
import type { Role } from '../../types';

export const RoleListPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const { query: { data, isLoading, isError } } = useList<Role>({
    resource: 'roles',
    filters: searchTerm
      ? [
          {
            field: 'q',
            operator: 'contains',
            value: searchTerm,
          },
        ]
      : [],
  });

  if (isError) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load roles. Please check your connection and try again.
        </Alert>
      </Box>
    );
  }

  const roles = data?.data || [];

  return (
    <RBACGuard permissions={['read:roles']}>
      <Box p={3}>
        {/* Header */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={3}
        >
          <Box>
            <Typography variant="h4" gutterBottom>
              Role Management
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage system roles and permissions
            </Typography>
          </Box>
          <RBACGuard permissions={['create:roles']}>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              size="large"
            >
              Add Role
            </Button>
          </RBACGuard>
        </Box>

        {/* Search */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TextField
              placeholder="Search roles by name or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              fullWidth
            />
          </CardContent>
        </Card>

        {/* Roles Table */}
        <Card>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Role Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Permissions</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      Loading roles...
                    </TableCell>
                  </TableRow>
                ) : roles.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      No roles found
                    </TableCell>
                  </TableRow>
                ) : (
                  roles.map((role) => (
                    <TableRow key={role.id} hover>
                      <TableCell>
                        <Typography variant="subtitle2" fontWeight={600}>
                          {role.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {role.description || 'No description'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={0.5} flexWrap="wrap">
                          {role.permissions?.slice(0, 3).map((permission, index) => (
                            <Chip
                              key={index}
                              label={permission.name}
                              size="small"
                              variant="outlined"
                              color="primary"
                            />
                          ))}
                          {role.permissions && role.permissions.length > 3 && (
                            <Chip
                              label={`+${role.permissions.length - 3}`}
                              size="small"
                              variant="outlined"
                              color="default"
                            />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        {new Date(role.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell align="center">
                        <Box display="flex" justifyContent="center" gap={1}>
                          <Tooltip title="View Details">
                            <IconButton size="small">
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <RBACGuard permissions={['update:roles']}>
                            <Tooltip title="Edit Role">
                              <IconButton size="small">
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                          </RBACGuard>
                          <RBACGuard permissions={['delete:roles']}>
                            <Tooltip title="Delete Role">
                              <IconButton size="small" color="error">
                                <DeleteIcon />
                              </IconButton>
                            </Tooltip>
                          </RBACGuard>
                        </Box>
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

export default RoleListPage;