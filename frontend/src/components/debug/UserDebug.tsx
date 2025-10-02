import React from 'react';
import { Box, Typography, Paper, Chip, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { useRBAC } from '../../providers/rbac/RBACProvider';

export const UserDebug: React.FC = () => {
  const { user, permissions, roles } = useRBAC();

  const storedUser = localStorage.getItem('user');
  let parsedStoredUser = null;
  try {
    parsedStoredUser = storedUser ? JSON.parse(storedUser) : null;
  } catch (e) {
    console.error('Failed to parse stored user:', e);
  }

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        User Debug Information
      </Typography>
      
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Current RBAC User Context</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="textSecondary">User Object:</Typography>
            <Box component="pre" sx={{ fontSize: 12, backgroundColor: '#f5f5f5', p: 1, borderRadius: 1, overflow: 'auto' }}>
              {JSON.stringify(user, null, 2)}
            </Box>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="textSecondary">Permissions Array:</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              {permissions.length > 0 ? (
                permissions.map((perm) => (
                  <Chip key={perm} label={perm} size="small" variant="outlined" />
                ))
              ) : (
                <Typography variant="body2" color="error">No permissions found</Typography>
              )}
            </Box>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="textSecondary">Roles Array:</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              {roles.length > 0 ? (
                roles.map((role) => (
                  <Chip key={role.id || role.name} label={role.name} size="small" color="primary" />
                ))
              ) : (
                <Typography variant="body2" color="error">No roles found</Typography>
              )}
            </Box>
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Raw localStorage Data</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box component="pre" sx={{ fontSize: 12, backgroundColor: '#f5f5f5', p: 1, borderRadius: 1, overflow: 'auto' }}>
            {JSON.stringify(parsedStoredUser, null, 2)}
          </Box>
        </AccordionDetails>
      </Accordion>

      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="textSecondary">
          Key Flags:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <Chip 
            label={`is_superuser: ${user?.is_superuser || false}`}
            color={user?.is_superuser ? 'success' : 'default'}
            size="small"
          />
          <Chip 
            label={`is_active: ${user?.is_active || false}`}
            color={user?.is_active ? 'success' : 'default'}
            size="small"
          />
        </Box>
      </Box>
    </Paper>
  );
};

export default UserDebug;