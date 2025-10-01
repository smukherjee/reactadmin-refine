import React from 'react';
import { Box } from '@mui/material';
import { AccessDenied } from '../../components/rbac/AccessDenied';

export const AccessDeniedPage: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <AccessDenied showHomeButton />
    </Box>
  );
};

export default AccessDeniedPage;
