import React from 'react';
import { Box, Typography, Button, Alert, Stack } from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

interface ApiErrorDisplayProps {
  error: any;
  resource?: string;
  onRetry?: () => void;
}

export const ApiErrorDisplay: React.FC<ApiErrorDisplayProps> = ({ 
  error, 
  resource, 
  onRetry 
}) => {
  const getErrorMessage = (error: any): string => {
    // Handle tenant-specific errors
    if (error?.message?.includes('Tenant ID is required')) {
      return 'Please select a tenant to access this data.';
    }

    // Handle validation errors
    if (error?.response?.status === 422 && error?.response?.data?.detail) {
      const details = error.response.data.detail;
      if (Array.isArray(details)) {
        return details.map((d: any) => d.msg || d.message).join(', ');
      }
      return details;
    }

    // Handle forbidden errors
    if (error?.response?.status === 403) {
      return 'You do not have permission to access this resource.';
    }

    // Handle authentication errors
    if (error?.response?.status === 401) {
      return 'Your session has expired. Please log in again.';
    }

    // Handle network errors
    if (!error?.response) {
      return 'Network error. Please check your connection and try again.';
    }

    // Default error message
    return error?.message || error?.response?.data?.message || 'An unexpected error occurred.';
  };

  const getSeverity = (error: any): 'error' | 'warning' | 'info' => {
    if (error?.message?.includes('Tenant ID is required')) {
      return 'warning';
    }
    if (error?.response?.status === 403) {
      return 'warning';
    }
    return 'error';
  };

  return (
    <Box sx={{ p: 2 }}>
      <Alert severity={getSeverity(error)} sx={{ mb: 2 }}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          {resource ? `Error loading ${resource}:` : 'Error:'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {getErrorMessage(error)}
        </Typography>
        
        {onRetry && (
          <Stack direction="row" sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={onRetry}
            >
              Try Again
            </Button>
          </Stack>
        )}
      </Alert>
    </Box>
  );
};

export default ApiErrorDisplay;