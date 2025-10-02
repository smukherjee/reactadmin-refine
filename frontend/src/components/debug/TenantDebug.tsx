import React, { useState, useEffect } from 'react';
import { Box, Button, Typography, Paper, Alert } from '@mui/material';
import { apiService } from '../../services/api';
import { useTenant } from '../../providers/tenant/TenantProvider';

export const TenantDebug: React.FC = () => {
  const [userInfo, setUserInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { currentTenant, availableTenants, isLoading } = useTenant();

  const fetchUserInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const user = await apiService.getCurrentUser();
      setUserInfo(user);
      console.log('Fetched user info:', user);
    } catch (err: any) {
      console.error('Error fetching user info:', err);
      setError(err.message || 'Failed to fetch user info');
    } finally {
      setLoading(false);
    }
  };

  const reEnhanceUser = async () => {
    setLoading(true);
    setError(null);
    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        throw new Error('No user data found in localStorage');
      }
      
      const user = JSON.parse(userStr);
      console.log('Re-enhancing user:', user);
      
      const enhancedUser = await apiService.enhanceUserWithTenantData(user);
      localStorage.setItem('user', JSON.stringify(enhancedUser));
      
      if (enhancedUser.current_tenant) {
        localStorage.setItem('current_tenant_id', enhancedUser.current_tenant.id);
      }
      
      setUserInfo(enhancedUser);
      console.log('Re-enhanced user:', enhancedUser);
      
      // Trigger a page reload to update TenantProvider
      window.location.reload();
    } catch (err: any) {
      console.error('Error re-enhancing user:', err);
      setError(err.message || 'Failed to re-enhance user');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedTenant = localStorage.getItem('current_tenant_id');
    
    console.log('Debug Info:');
    console.log('- Stored user:', storedUser ? JSON.parse(storedUser) : null);
    console.log('- Stored tenant ID:', storedTenant);
    console.log('- Current tenant from context:', currentTenant);
    console.log('- Available tenants from context:', availableTenants);
    console.log('- Tenant loading state:', isLoading);
  }, [currentTenant, availableTenants, isLoading]);

  return (
    <Box sx={{ p: 2, maxWidth: 800 }}>
      <Typography variant="h5" gutterBottom>
        Tenant Debug Information
      </Typography>
      
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Tenant Context State
        </Typography>
        <Typography variant="body2">
          Loading: {isLoading ? 'Yes' : 'No'}
        </Typography>
        <Typography variant="body2">
          Current Tenant: {currentTenant ? `${currentTenant.name} (${currentTenant.id})` : 'None'}
        </Typography>
        <Typography variant="body2">
          Available Tenants: {availableTenants.length} tenant(s)
        </Typography>
        {availableTenants.map((tenant) => (
          <Typography key={tenant.id} variant="body2" sx={{ ml: 2 }}>
            - {tenant.name} ({tenant.id})
          </Typography>
        ))}
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          localStorage Data
        </Typography>
        <Typography variant="body2">
          Access Token: {localStorage.getItem('access_token') ? 'Present' : 'Missing'}
        </Typography>
        <Typography variant="body2">
          Current Tenant ID: {localStorage.getItem('current_tenant_id') || 'None'}
        </Typography>
        <Typography variant="body2">
          User Data: {localStorage.getItem('user') ? 'Present' : 'Missing'}
        </Typography>
      </Paper>

      <Button 
        variant="contained" 
        onClick={fetchUserInfo} 
        disabled={loading}
        sx={{ mb: 2, mr: 2 }}
      >
        {loading ? 'Fetching...' : 'Fetch Current User Info'}
      </Button>

      <Button 
        variant="outlined" 
        onClick={reEnhanceUser} 
        disabled={loading}
        sx={{ mb: 2 }}
      >
        Re-enhance User Data
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {userInfo && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            API Response
          </Typography>
          <pre style={{ fontSize: '12px', overflow: 'auto' }}>
            {JSON.stringify(userInfo, null, 2)}
          </pre>
        </Paper>
      )}
    </Box>
  );
};