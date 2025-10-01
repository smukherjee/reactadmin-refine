import React from 'react';
import { Alert, AlertTitle, Box, Button, Stack, Typography } from '@mui/material';
import { Refresh as RefreshIcon, Home as HomeIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface TenantRequiredErrorProps {
  resource?: string;
  onRetry?: () => void;
}

export const TenantRequiredError: React.FC<TenantRequiredErrorProps> = ({ 
  resource, 
  onRetry 
}) => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/', { replace: true });
  };

  return (
    <Box sx={{ p: 3, maxWidth: 500, mx: 'auto' }}>
      <Alert severity="warning" sx={{ mb: 2 }}>
        <AlertTitle>Tenant Selection Required</AlertTitle>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {resource 
            ? `To access ${resource}, you need to select a tenant first.`
            : 'A tenant must be selected to access this resource.'
          }
        </Typography>
        
        <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<HomeIcon />}
            onClick={handleGoHome}
            size="small"
          >
            Go to Dashboard
          </Button>
          {onRetry && (
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={onRetry}
              size="small"
            >
              Retry
            </Button>
          )}
        </Stack>
      </Alert>
    </Box>
  );
};

export default TenantRequiredError;