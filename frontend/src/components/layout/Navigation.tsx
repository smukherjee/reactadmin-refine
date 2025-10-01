import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Chip } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Security as SecurityIcon,
  Assignment as AssignmentIcon,
  Login as LoginIcon,
  Business as BusinessIcon,
} from '@mui/icons-material';
import { useTenant } from '../../providers/tenant/TenantProvider';

export const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentTenant } = useTenant();

  const navigationItems = [
    { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/users', label: 'Users', icon: <PeopleIcon /> },
    { path: '/roles', label: 'Roles', icon: <SecurityIcon /> },
    { path: '/audit-logs', label: 'Audit Logs', icon: <AssignmentIcon /> },
    ...(import.meta.env.MODE === 'development' ? [
      { path: '/debug', label: 'Debug', icon: <AssignmentIcon /> }
    ] : []),
    { path: '/login', label: 'Login', icon: <LoginIcon /> },
  ];

  return (
    <AppBar position="static" sx={{ mb: 2 }}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          React Admin Dashboard
        </Typography>
        
        {currentTenant && (
          <Chip
            icon={<BusinessIcon />}
            label={currentTenant.name}
            variant="outlined"
            size="small"
            sx={{ 
              color: 'white', 
              borderColor: 'white',
              mr: 2,
              '& .MuiChip-icon': { color: 'white' }
            }}
            onClick={() => navigate('/tenant-selection')}
            clickable
          />
        )}
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          {navigationItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              variant={location.pathname === item.path ? 'outlined' : 'text'}
              sx={{ 
                color: 'white',
                borderColor: location.pathname === item.path ? 'white' : 'transparent'
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>
      </Toolbar>
    </AppBar>
  );
};