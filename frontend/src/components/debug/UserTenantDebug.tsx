import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Alert,
  Box,
  Chip,
  CircularProgress,
} from '@mui/material';
import { Refresh as RefreshIcon, Person as PersonIcon } from '@mui/icons-material';
import { apiService } from '../../services/api';
import { useTenant } from '../../providers/tenant/TenantProvider';
import type { AuthUser } from '../../types';

export const UserTenantDebug: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { currentTenant, availableTenants, isLoading: tenantLoading } = useTenant();

  const fetchUserData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const user = await apiService.getCurrentUser();
      setCurrentUser(user);
      console.log('Fetched user data:', user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch user data');
      console.error('Error fetching user:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, []);

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <PersonIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">User & Tenant Status</Typography>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={fetchUserData}
            disabled={loading}
            sx={{ ml: 'auto' }}
          >
            Refresh
          </Button>
        </Box>

        <Stack spacing={2}>
          {/* Current User Info */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Current User (from API)
            </Typography>
            {loading ? (
              <CircularProgress size={20} />
            ) : error ? (
              <Alert severity="error">
                {error}
              </Alert>
            ) : currentUser ? (
              <Box sx={{ pl: 1 }}>
                <Typography variant="body2">
                  <strong>Email:</strong> {currentUser.email}
                </Typography>
                <Typography variant="body2">
                  <strong>ID:</strong> {currentUser.id}
                </Typography>
                <Typography variant="body2">
                  <strong>Current Tenant:</strong> {currentUser.current_tenant?.name || 'None'}
                </Typography>
                <Typography variant="body2">
                  <strong>Available Tenants:</strong> {currentUser.available_tenants?.length || 0}
                </Typography>
                {currentUser.available_tenants && currentUser.available_tenants.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    {currentUser.available_tenants.map((tenant) => (
                      <Chip
                        key={tenant.id}
                        label={tenant.name}
                        size="small"
                        variant="outlined"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ))}
                  </Box>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No user data
              </Typography>
            )}
          </Box>

          {/* Tenant Provider Status */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Tenant Provider Status
            </Typography>
            <Box sx={{ pl: 1 }}>
              <Typography variant="body2">
                <strong>Loading:</strong> {tenantLoading ? 'Yes' : 'No'}
              </Typography>
              <Typography variant="body2">
                <strong>Current Tenant:</strong> {currentTenant?.name || 'None'}
              </Typography>
              <Typography variant="body2">
                <strong>Available Tenants:</strong> {availableTenants?.length || 0}
              </Typography>
            </Box>
          </Box>

          {/* LocalStorage Status */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              LocalStorage Status
            </Typography>
            <Box sx={{ pl: 1 }}>
              <Typography variant="body2">
                <strong>Access Token:</strong> {localStorage.getItem('access_token') ? 'Present' : 'Missing'}
              </Typography>
              <Typography variant="body2">
                <strong>Current Tenant ID:</strong> {localStorage.getItem('current_tenant_id') || 'None'}
              </Typography>
              <Typography variant="body2">
                <strong>User Data:</strong> {localStorage.getItem('user') ? 'Present' : 'Missing'}
              </Typography>
              <Typography variant="body2">
                <strong>Session ID:</strong> {localStorage.getItem('session_id') ? 'Present' : 'Missing'}
              </Typography>
            </Box>
          </Box>

          {/* User Role Info */}
          {currentUser && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                User Role Information
              </Typography>
              <Box sx={{ pl: 1 }}>
                <Typography variant="body2">
                  <strong>User ID:</strong> {currentUser.id}
                </Typography>
                <Typography variant="body2">
                  <strong>Tenant ID:</strong> {currentUser.tenant_id || 'Not set'}
                </Typography>
                {currentUser.roles && currentUser.roles.length > 0 && (
                  <Typography variant="body2">
                    <strong>Roles:</strong> {currentUser.roles.map((role: any) => role.name).join(', ')}
                  </Typography>
                )}
              </Box>
            </Box>
          )}

          {/* Recommendations */}
          {currentUser && !currentUser.current_tenant && (
            <Alert severity="warning">
              <Typography variant="body2">
                <strong>Issue:</strong> User is authenticated but has no current tenant selected.
                <br />
                {currentUser.available_tenants && currentUser.available_tenants.length > 0
                  ? `Available tenants (${currentUser.available_tenants.length}): ${currentUser.available_tenants.map(t => t.name).join(', ')}`
                  : 'No tenants are available for this user.'
                }
                <br />
                {currentUser.available_tenants && currentUser.available_tenants.length > 1
                  ? 'User appears to be superadmin with access to multiple tenants.'
                  : 'User appears to be regular user with single tenant access.'
                }
              </Typography>
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default UserTenantDebug;