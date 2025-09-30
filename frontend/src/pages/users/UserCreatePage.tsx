import React from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useCreate, useNavigation } from '@refinedev/core';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  FormControlLabel,
  Switch,
  Chip,
  Alert,
  Stack,
  CircularProgress,
} from '@mui/material';
import { Save as SaveIcon, ArrowBack as BackIcon } from '@mui/icons-material';
import RBACGuard from '../../components/rbac/RBACGuard';
import type { UserFormData } from '../../types';

export const UserCreatePage: React.FC = () => {
  const { mutate: createUser } = useCreate();
  const { list } = useNavigation();
  const [error, setError] = React.useState<string>('');
  
  // Create a manual loading state since useCreate doesn't have isLoading directly
  const [isLoading, setIsLoading] = React.useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<UserFormData>({
    defaultValues: {
      email: '',
      username: '',
      first_name: '',
      last_name: '',
      password: '',
      confirm_password: '',
      is_active: true,
      role_ids: [],
    },
  });

  const handleFormSubmit = (data: UserFormData) => {
    setIsLoading(true);
    setError('');
    
    createUser(
      {
        resource: 'users',
        values: data,
      },
      {
        onSuccess: () => {
          setIsLoading(false);
          list('users');
        },
        onError: (error: any) => {
          setIsLoading(false);
          setError(error?.message || 'Failed to create user');
        },
      }
    );
  };

  const availableRoles = [
    { id: 'admin', name: 'Administrator' },
    { id: 'manager', name: 'Manager' },
    { id: 'user', name: 'User' },
    { id: 'viewer', name: 'Viewer' },
  ];

  const watchedRoleIds = watch('role_ids') || [];

  const toggleRole = (roleId: string) => {
    const currentRoles = watchedRoleIds;
    const newRoles = currentRoles.includes(roleId)
      ? currentRoles.filter(r => r !== roleId)
      : [...currentRoles, roleId];
    
    return newRoles;
  };

  return (
    <RBACGuard permissions={['users:write']} fallback={<div>Access denied</div>}>
      <Box sx={{ p: 3 }}>
        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<BackIcon />}
            onClick={() => list('users')}
            variant="outlined"
          >
            Back to Users
          </Button>
          <Typography variant="h4">Create New User</Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Card>
          <CardContent>
            <Box component="form" onSubmit={handleSubmit(handleFormSubmit)}>
              {/* Basic Information Section */}
              <Typography variant="h6" sx={{ mb: 2 }}>
                Basic Information
              </Typography>
              
              <Stack spacing={3} sx={{ mb: 4 }}>
                <Controller
                  name="email"
                  control={control}
                  rules={{
                    required: 'Email is required',
                    pattern: {
                      value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                      message: 'Please enter a valid email address',
                    },
                  }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Email"
                      type="email"
                      fullWidth
                      error={!!errors.email}
                      helperText={errors.email?.message}
                      required
                    />
                  )}
                />

                <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
                  <Controller
                    name="first_name"
                    control={control}
                    rules={{ required: 'First name is required' }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="First Name"
                        fullWidth
                        error={!!errors.first_name}
                        helperText={errors.first_name?.message}
                        required
                      />
                    )}
                  />

                  <Controller
                    name="last_name"
                    control={control}
                    rules={{ required: 'Last name is required' }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Last Name"
                        fullWidth
                        error={!!errors.last_name}
                        helperText={errors.last_name?.message}
                        required
                      />
                    )}
                  />
                </Box>

                <Controller
                  name="username"
                  control={control}
                  rules={{ required: 'Username is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Username"
                      fullWidth
                      error={!!errors.username}
                      helperText={errors.username?.message}
                      required
                    />
                  )}
                />

                <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
                  <Controller
                    name="password"
                    control={control}
                    rules={{ required: 'Password is required', minLength: { value: 8, message: 'Password must be at least 8 characters' } }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Password"
                        type="password"
                        fullWidth
                        error={!!errors.password}
                        helperText={errors.password?.message}
                        required
                      />
                    )}
                  />

                  <Controller
                    name="confirm_password"
                    control={control}
                    rules={{ 
                      required: 'Please confirm password',
                      validate: (value) => value === watch('password') || 'Passwords do not match'
                    }}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Confirm Password"
                        type="password"
                        fullWidth
                        error={!!errors.confirm_password}
                        helperText={errors.confirm_password?.message}
                        required
                      />
                    )}
                  />
                </Box>
              </Stack>

              {/* Roles Section */}
              <Typography variant="h6" sx={{ mb: 2 }}>
                User Roles
              </Typography>
              
              <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {availableRoles.map((role) => (
                    <Controller
                      key={role.id}
                      name="role_ids"
                      control={control}
                      render={({ field }) => (
                        <Chip
                          label={role.name}
                          clickable
                          color={watchedRoleIds.includes(role.id) ? 'primary' : 'default'}
                          onClick={() => {
                            const newRoles = toggleRole(role.id);
                            field.onChange(newRoles);
                          }}
                        />
                      )}
                    />
                  ))}
                </Box>
              </Box>

              {/* Status Section */}
              <Typography variant="h6" sx={{ mb: 2 }}>
                Status
              </Typography>
              
              <Box sx={{ mb: 4 }}>
                <Controller
                  name="is_active"
                  control={control}
                  render={({ field: { value, onChange } }) => (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={value}
                          onChange={(e) => onChange(e.target.checked)}
                        />
                      }
                      label="Active User"
                    />
                  )}
                />
              </Box>

              {/* Form Actions */}
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button
                  type="button"
                  variant="outlined"
                  onClick={() => list('users')}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={isLoading ? <CircularProgress size={20} /> : <SaveIcon />}
                  disabled={isLoading}
                >
                  {isLoading ? 'Creating...' : 'Create User'}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </RBACGuard>
  );
};