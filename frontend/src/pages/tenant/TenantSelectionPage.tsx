import React from 'react';
import {
  Box,
  Container,
  Card,
  CardContent,
  Typography,
  Alert,
  Stack,
} from '@mui/material';
import { Business as BusinessIcon } from '@mui/icons-material';
import { TenantSelector } from '../../components/tenant/TenantSelector';

export const TenantSelectionPage: React.FC = () => {
  return (
    <Container maxWidth="md">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '70vh',
          gap: 3,
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <BusinessIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
          <Typography variant="h4" component="h1" gutterBottom>
            Select Your Tenant
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            You need to select a tenant to access the application features.
          </Typography>
        </Box>

        <Card sx={{ width: '100%', maxWidth: 500 }}>
          <CardContent>
            <Stack spacing={2}>
              <Alert severity="info">
                <Typography variant="body2">
                  Please select a tenant below to continue. All data and permissions 
                  are tenant-specific, so you'll only see information related to the 
                  selected tenant.
                </Typography>
              </Alert>
              
              <TenantSelector />
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default TenantSelectionPage;