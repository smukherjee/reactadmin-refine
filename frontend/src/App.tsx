import { Refine } from '@refinedev/core';
import { RefineSnackbarProvider, useNotificationProvider } from '@refinedev/mui';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';

import { authProvider } from './providers/auth/authProvider';
import { dataProvider } from './providers/data/dataProvider';
import { RBACProvider } from './providers/rbac/RBACProvider';
import { TenantProvider } from './providers/tenant/TenantProvider';
import { theme } from './styles/theme';

// Import pages
import { DashboardPage } from './pages/DashboardPage';

// Simple test components
const TestDashboard = () => (
  <div style={{ padding: '20px' }}>
    <h1>Dashboard</h1>
    <p>Welcome to the React Admin Dashboard!</p>
    <p>Refine is initialized successfully!</p>
    <div style={{ marginTop: '20px', border: '1px solid #ccc', padding: '10px' }}>
      <h2>Real Dashboard Component:</h2>
      <DashboardPage />
    </div>
  </div>
);

const TestLogin = () => (
  <div style={{ padding: '20px' }}>
    <h1>Login</h1>
    <p>Login page placeholder</p>
  </div>
);

function App() {
  const notificationProvider = useNotificationProvider();

  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <RefineSnackbarProvider>
          <TenantProvider>
            <RBACProvider>
              <Refine
              authProvider={authProvider}
              dataProvider={dataProvider}
              notificationProvider={notificationProvider}
              options={{
                syncWithLocation: true,
                warnWhenUnsavedChanges: true,
                disableTelemetry: true,
              }}
            >
              <Routes>
                <Route index element={<TestDashboard />} />
                <Route path="/login" element={<TestLogin />} />
              </Routes>
            </Refine>
            </RBACProvider>
          </TenantProvider>
        </RefineSnackbarProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
