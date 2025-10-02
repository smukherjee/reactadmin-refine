import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  BugReport as BugIcon,
} from '@mui/icons-material';
import { runApiTests, type ApiTestResult } from '../../utils/apiTester';
import { validateConfiguration, type ConfigValidationResult } from '../../utils/configValidator';
import { TenantDebug } from './TenantDebug';
import { UserTenantDebug } from './UserTenantDebug';
import { UserDebug } from './UserDebug';

interface DebugInfo {
  environment: Record<string, any>;
  localStorage: Record<string, any>;
  apiTests: ApiTestResult[];
  configValidation: ConfigValidationResult;
  userAgent: string;
  currentUrl: string;
  timestamp: string;
}

export const DebugDashboard: React.FC = () => {
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState<ApiTestResult[]>([]);

  const collectDebugInfo = async () => {
    setLoading(true);
    
    try {
      // Run configuration validation
      const configValidation = validateConfiguration();
      
      // Run API tests
      const apiTests = await runApiTests();
      setTestResults(apiTests);

      // Collect environment info
      const environment = {
        NODE_ENV: import.meta.env.NODE_ENV,
        MODE: import.meta.env.MODE,
        VITE_API_URL: import.meta.env.VITE_API_URL,
        VITE_BACKEND_URL: import.meta.env.VITE_BACKEND_URL,
        VITE_DEBUG_MODE: import.meta.env.VITE_DEBUG_MODE,
        VITE_APP_TITLE: import.meta.env.VITE_APP_TITLE,
      };

      // Collect localStorage info
      const localStorage = {
        access_token: !!window.localStorage.getItem('access_token'),
        refresh_token: !!window.localStorage.getItem('refresh_token'),
        user: !!window.localStorage.getItem('user'),
        current_tenant_id: window.localStorage.getItem('current_tenant_id'),
        session_id: !!window.localStorage.getItem('session_id'),
      };

      const info: DebugInfo = {
        environment,
        localStorage,
        apiTests,
        configValidation,
        userAgent: navigator.userAgent,
        currentUrl: window.location.href,
        timestamp: new Date().toISOString(),
      };

      setDebugInfo(info);
    } catch (error) {
      console.error('Error collecting debug info:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    collectDebugInfo();
  }, []);

  const getStatusColor = (success: boolean) => {
    return success ? 'success' : 'error';
  };

  const downloadDebugInfo = () => {
    if (!debugInfo) return;

    const dataStr = JSON.stringify(debugInfo, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `debug-info-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
  };

  if (!debugInfo) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <BugIcon sx={{ mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" gutterBottom>
          Debug Dashboard
        </Typography>
      </Box>

      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={collectDebugInfo}
          disabled={loading}
        >
          Refresh
        </Button>
        <Button
          variant="outlined"
          onClick={downloadDebugInfo}
        >
          Download Debug Info
        </Button>
      </Stack>

      {/* Configuration Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Configuration Status
          </Typography>
          
          <Box sx={{ mb: 2 }}>
            <Chip
              label={debugInfo.configValidation.isValid ? 'Valid' : 'Issues Found'}
              color={debugInfo.configValidation.isValid ? 'success' : 'error'}
              sx={{ mr: 1 }}
            />
            <Typography variant="body2" component="span">
              {debugInfo.configValidation.errors.length} errors, {debugInfo.configValidation.warnings.length} warnings
            </Typography>
          </Box>

          {debugInfo.configValidation.errors.length > 0 && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Errors:</Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {debugInfo.configValidation.errors.map((error: string, index: number) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </Alert>
          )}

          {debugInfo.configValidation.warnings.length > 0 && (
            <Alert severity="warning">
              <Typography variant="subtitle2" gutterBottom>Warnings:</Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {debugInfo.configValidation.warnings.map((warning: string, index: number) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* User Debug */}
      <Box sx={{ mb: 3 }}>
        <UserDebug />
      </Box>
      
      {/* User & Tenant Debug */}
      <Box sx={{ mb: 3 }}>
        <UserTenantDebug />
      </Box>

      {/* API Test Results */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            API Test Results
          </Typography>
          
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Endpoint</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Error</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {testResults.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell>{result.endpoint}</TableCell>
                    <TableCell>
                      <Chip
                        label={result.success ? 'Success' : 'Failed'}
                        color={getStatusColor(result.success)}
                        size="small"
                      />
                      {result.statusCode && (
                        <Typography variant="caption" sx={{ ml: 1 }}>
                          [{result.statusCode}]
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="error">
                        {result.error || '-'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Detailed Information */}
      <Box>
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Environment Variables</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  {Object.entries(debugInfo.environment).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell component="th" scope="row">
                        {key}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {String(value) || '<not set>'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Local Storage</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  {Object.entries(debugInfo.localStorage).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell component="th" scope="row">
                        {key}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {typeof value === 'boolean' ? (value ? '✅ Present' : '❌ Missing') : String(value)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">System Information</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell component="th" scope="row">Current URL</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {debugInfo.currentUrl}
                      </Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row">User Agent</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {debugInfo.userAgent}
                      </Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row">Timestamp</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {debugInfo.timestamp}
                      </Typography>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>
      </Box>
    </Box>
  );
};

export default DebugDashboard;