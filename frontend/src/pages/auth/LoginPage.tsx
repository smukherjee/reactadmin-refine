import React, { useState } from 'react';
import { useLogin } from '@refinedev/core';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  Avatar,
  FormControlLabel,
  Checkbox,
  CircularProgress,
} from '@mui/material';
import { LockOutlined as LockIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate, useLocation } from 'react-router-dom';
import type { Location } from 'react-router-dom';
import type { LoginRequest } from '../../types';

interface LoginFormData extends LoginRequest {
  remember?: boolean;
}

export const LoginPage: React.FC = () => {
  const { mutate: login } = useLogin<LoginRequest>();
  const navigate = useNavigate();
  const location = useLocation();
  const fromLocation = (location.state as { from?: Location } | undefined)?.from;
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      tenant_id: '',
      remember: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      setError('');
      setIsLoading(true);
      await login(
        {
          email: data.email.trim(),
          password: data.password,
          tenant_id: data.tenant_id?.trim() || undefined,
        },
        {
          onSuccess: () => {
            const storedRedirect = sessionStorage.getItem('post_login_redirect');

            let redirectPath = '/';

            if (fromLocation && fromLocation.pathname && fromLocation.pathname !== '/login') {
              redirectPath = `${fromLocation.pathname}${fromLocation.search ?? ''}${fromLocation.hash ?? ''}`;
            } else if (storedRedirect && storedRedirect !== '/login') {
              redirectPath = storedRedirect;
            }

            sessionStorage.removeItem('post_login_redirect');

            navigate(redirectPath || '/', { replace: true });
          },
        }
      );
    } catch (err: any) {
      setError(err?.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          minHeight: '80vh',
          justifyContent: 'center',
        }}
      >
        <Card elevation={3} sx={{ width: '100%', maxWidth: 400 }}>
          <CardContent sx={{ p: 4 }}>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                mb: 3,
              }}
            >
              <Avatar sx={{ m: 1, bgcolor: 'primary.main' }}>
                <LockIcon />
              </Avatar>
              <Typography component="h1" variant="h4" fontWeight={600}>
                {import.meta.env.VITE_APP_TITLE || 'Admin Dashboard'}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Sign in to your account
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
              <Controller
                name="email"
                control={control}
                rules={{
                  required: 'Email is required',
                  pattern: {
                    value:
                      /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Enter a valid email address',
                  },
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    margin="normal"
                    required
                    fullWidth
                    label="Email"
                    type="email"
                    autoComplete="email"
                    autoFocus
                    error={!!errors.email}
                    helperText={errors.email?.message}
                    disabled={isLoading}
                  />
                )}
              />

              <Controller
                name="password"
                control={control}
                rules={{
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters',
                  },
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    margin="normal"
                    required
                    fullWidth
                    label="Password"
                    type="password"
                    autoComplete="current-password"
                    error={!!errors.password}
                    helperText={errors.password?.message}
                    disabled={isLoading}
                  />
                )}
              />

              <Controller
                name="tenant_id"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    margin="normal"
                    fullWidth
                    label="Tenant ID (optional)"
                    autoComplete="organization"
                    helperText="Provide a tenant/client identifier if required."
                    disabled={isLoading}
                  />
                )}
              />

              <Controller
                name="remember"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Checkbox
                        {...field}
                        checked={field.value}
                        color="primary"
                        disabled={isLoading}
                      />
                    }
                    label="Remember me"
                    sx={{ mt: 1 }}
                  />
                )}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2, py: 1.5 }}
                disabled={isLoading}
                size="large"
              >
                {isLoading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Sign In'
                )}
              </Button>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Demo Credentials:
                </Typography>
                <Typography variant="caption" display="block">
                  Admin: admin@example.com / password123
                </Typography>
                <Typography variant="caption" display="block">
                  User: user@example.com / password123
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 4 }}>
          © {new Date().getFullYear()} {import.meta.env.VITE_APP_TITLE || 'Admin Dashboard'}. 
          Built with Refine & Material-UI.
        </Typography>
      </Box>
    </Container>
  );
};

export default LoginPage;