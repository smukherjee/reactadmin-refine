import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Stack,
} from '@mui/material';
import { Business as BusinessIcon, SwapHoriz as SwitchIcon } from '@mui/icons-material';
import { useTenant } from '../../providers/tenant/TenantProvider';
import type { Tenant } from '../../types';

export const TenantSelector: React.FC = () => {
  const { currentTenant, availableTenants, switchTenant, isLoading } = useTenant();
  const [selectedTenantId, setSelectedTenantId] = useState<string>(currentTenant?.id || '');
  const [switching, setSwitching] = useState(false);

  const handleTenantSwitch = async () => {
    if (!selectedTenantId || selectedTenantId === currentTenant?.id) {
      return;
    }

    try {
      setSwitching(true);
      await switchTenant(selectedTenantId);
    } catch (error) {
      console.error('Failed to switch tenant:', error);
    } finally {
      setSwitching(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={24} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!availableTenants || availableTenants.length === 0) {
    return (
      <Alert severity="warning">
        <Typography variant="body2">
          No tenants available. Please contact your administrator.
        </Typography>
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <BusinessIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">
            Tenant Selection
          </Typography>
        </Box>

        {!currentTenant && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              Please select a tenant to access tenant-specific data and features.
            </Typography>
          </Alert>
        )}

        <Stack spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Select Tenant</InputLabel>
            <Select
              value={selectedTenantId}
              label="Select Tenant"
              onChange={(e) => setSelectedTenantId(e.target.value)}
              disabled={switching}
            >
              {availableTenants.map((tenant: Tenant) => (
                <MenuItem key={tenant.id} value={tenant.id}>
                  <Box>
                    <Typography variant="body1">
                      {tenant.name}
                    </Typography>
                    {tenant.domain && (
                      <Typography variant="caption" color="text.secondary">
                        {tenant.domain}
                      </Typography>
                    )}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="contained"
            startIcon={switching ? <CircularProgress size={16} /> : <SwitchIcon />}
            onClick={handleTenantSwitch}
            disabled={
              switching || 
              !selectedTenantId || 
              selectedTenantId === currentTenant?.id
            }
            fullWidth
          >
            {switching ? 'Switching...' : 'Switch Tenant'}
          </Button>

          {currentTenant && (
            <Box sx={{ mt: 1, p: 1, bgcolor: 'success.light', borderRadius: 1 }}>
              <Typography variant="body2" color="success.dark">
                <strong>Current:</strong> {currentTenant.name}
              </Typography>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default TenantSelector;