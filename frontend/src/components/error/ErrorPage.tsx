import React from 'react';
import {
  Box,
  Button,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

interface ErrorPageProps {
  error?: Error | null;
  errorInfo?: React.ErrorInfo | null;
  onRetry?: () => void;
}

const isDebugMode = (import.meta.env.VITE_DEBUG_MODE || '').toLowerCase() === 'true';

export const ErrorPage: React.FC<ErrorPageProps> = ({ error, errorInfo, onRetry }) => {
  const handleReload = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        px: 2,
      }}
    >
      <Paper elevation={3} sx={{ maxWidth: 720, width: '100%', p: 4 }}>
        <Stack spacing={3} alignItems="center">
          <WarningAmberIcon color="warning" sx={{ fontSize: 48 }} />
          <Box textAlign="center">
            <Typography variant="h4" gutterBottom>
              Something went wrong
            </Typography>
            <Typography variant="body1" color="text.secondary">
              We couldn&apos;t load the page. Please try again in a moment.
            </Typography>
          </Box>

          {error?.message && (
            <Typography
              variant="subtitle2"
              color="error"
              sx={{
                fontWeight: 600,
                textAlign: 'center',
              }}
            >
              {error.message}
            </Typography>
          )}

          <Button variant="contained" color="primary" onClick={handleReload}>
            Reload page
          </Button>

          {isDebugMode && (error || errorInfo) && (
            <Box sx={{ width: '100%' }}>
              <Typography variant="subtitle1" gutterBottom>
                Debug information
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  maxHeight: 320,
                  overflow: 'auto',
                  p: 2,
                  bgcolor: 'background.paper',
                  fontFamily: 'monospace',
                  fontSize: 14,
                }}
              >
                {error?.stack && (
                  <Box component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {error.stack}
                  </Box>
                )}
                {errorInfo?.componentStack && (
                  <Box component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {errorInfo.componentStack}
                  </Box>
                )}
                {!error?.stack && !errorInfo?.componentStack && (
                  <Typography variant="body2" color="text.secondary">
                    No additional debug information is available.
                  </Typography>
                )}
              </Paper>
            </Box>
          )}
        </Stack>
      </Paper>
    </Box>
  );
};

export default ErrorPage;
