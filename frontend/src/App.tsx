import { useEffect } from 'react';
import { Refine, useIsAuthenticated } from '@refinedev/core';
import { RefineSnackbarProvider } from '@refinedev/mui';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { CssBaseline, Box, CircularProgress } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';

import { authProvider } from './providers/auth/authProvider';
import { dataProvider } from './providers/data/dataProvider';
import { theme } from './styles/theme';

// Import pages
import { LoginPage } from './pages/auth/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { UserListPage } from './pages/users/UserListPage';
import { UserCreatePage } from './pages/users/UserCreatePage';
import { RoleListPage } from './pages/roles/RoleListPage';
import { AuditLogListPage } from './pages/audit/AuditLogListPage';
import { AccessDeniedPage } from './pages/errors/AccessDeniedPage';
import { TenantSelectionPage } from './pages/tenant/TenantSelectionPage';

// Debug components (only in development)
import { DebugDashboard } from './components/debug/DebugDashboard';

// Import components
import { Navigation } from './components/layout/Navigation';
import { ErrorBoundary } from './components/error/ErrorBoundary';
import { TenantGuard } from './components/guards/TenantGuard';
import { RBACProvider } from './providers/rbac/RBACProvider';
import { TenantProvider } from './providers/tenant/TenantProvider';

function App() {
  const AppLayout = () => {
    const { data, isLoading } = useIsAuthenticated();
    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
      if (!data?.authenticated) {
        return;
      }

      const storedRedirect = sessionStorage.getItem('post_login_redirect');

      if (storedRedirect && storedRedirect !== '/login') {
        const currentPath = `${location.pathname}${location.search ?? ''}${location.hash ?? ''}`;

        sessionStorage.removeItem('post_login_redirect');

        if (storedRedirect !== currentPath) {
          navigate(storedRedirect, { replace: true });
        }
      }
    }, [data?.authenticated, location, navigate]);

    if (isLoading) {
      return (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
          }}
        >
          <CircularProgress />
        </Box>
      );
    }

    if (!data?.authenticated) {
      if (location.pathname !== '/login') {
        const redirectTarget = `${location.pathname}${location.search ?? ''}${location.hash ?? ''}`;
        sessionStorage.setItem('post_login_redirect', redirectTarget);
      }
      return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return (
      <div style={{ width: '100%', minHeight: '100vh' }}>
        <Navigation />
        <div style={{ padding: '20px' }}>
          <Outlet />
        </div>
      </div>
    );
  };

  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <RefineSnackbarProvider>
          <Refine
            authProvider={authProvider}
            dataProvider={dataProvider}
            options={{
              syncWithLocation: true,
              warnWhenUnsavedChanges: true,
              disableTelemetry: true,
            }}
          >
            <TenantProvider>
              <RBACProvider>
                <ErrorBoundary>
                  <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route element={<AppLayout />}>
                      <Route path="/tenant-selection" element={<TenantSelectionPage />} />
                      <Route element={<TenantGuard><Outlet /></TenantGuard>}>
                        <Route index element={<DashboardPage />} />
                        <Route path="/users" element={<UserListPage />} />
                        <Route path="/users/create" element={<UserCreatePage />} />
                        <Route path="/roles" element={<RoleListPage />} />
                        <Route path="/audit-logs" element={<AuditLogListPage />} />
                        <Route path="/access-denied" element={<AccessDeniedPage />} />
                        {import.meta.env.MODE === 'development' && (
                          <Route path="/debug" element={<DebugDashboard />} />
                        )}
                      </Route>
                    </Route>
                  </Routes>
                </ErrorBoundary>
              </RBACProvider>
            </TenantProvider>
          </Refine>
        </RefineSnackbarProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
