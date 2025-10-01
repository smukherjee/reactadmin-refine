import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Paper,
  Typography,
  Stack,
  Chip,
} from '@mui/material';
import { LockOutlined as LockIcon, Home as HomeIcon } from '@mui/icons-material';

export interface AccessDeniedProps {
  title?: string;
  description?: string;
  requiredPermissions?: string[];
  requiredRoles?: string[];
  showHomeButton?: boolean;
}

export const AccessDenied: React.FC<AccessDeniedProps> = ({
  title = 'Access Denied',
  description = "You don't have the required permissions to view this content.",
  requiredPermissions,
  requiredRoles,
  showHomeButton = true,
}) => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/', { replace: true });
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 6,
        textAlign: 'center',
        maxWidth: 560,
        mx: 'auto',
        my: { xs: 4, md: 8 },
        borderRadius: 3,
        background: (theme) =>
          theme.palette.mode === 'dark'
            ? theme.palette.grey[900]
            : theme.palette.grey[50],
      }}
    >
      <Stack spacing={3} alignItems="center">
        <Box
          sx={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: (theme) => theme.palette.primary.light,
            color: (theme) => theme.palette.primary.main,
          }}
        >
          <LockIcon sx={{ fontSize: 36 }} />
        </Box>

        <Typography component="h1" variant="h4" fontWeight={600}>
          {title}
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 420 }}>
          {description}
        </Typography>

        {(requiredPermissions?.length || requiredRoles?.length) && (
          <Stack spacing={1.5} sx={{ width: '100%' }}>
            {requiredPermissions?.length ? (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Required permissions
                </Typography>
                <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
                  {requiredPermissions.map((permission) => (
                    <Chip key={permission} label={permission} size="small" color="warning" />
                  ))}
                </Stack>
              </Box>
            ) : null}

            {requiredRoles?.length ? (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Required roles
                </Typography>
                <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
                  {requiredRoles.map((role) => (
                    <Chip key={role} label={role} size="small" color="primary" variant="outlined" />
                  ))}
                </Stack>
              </Box>
            ) : null}
          </Stack>
        )}

        {showHomeButton ? (
          <Button
            variant="contained"
            color="primary"
            startIcon={<HomeIcon />}
            onClick={handleGoHome}
          >
            Back to dashboard
          </Button>
        ) : null}
      </Stack>
    </Paper>
  );
};

export default AccessDenied;
