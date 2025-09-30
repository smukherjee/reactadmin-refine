import React, { useState } from 'react';
import { useList, useDelete, useNavigation } from '@refinedev/core';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  InputAdornment,
  Tooltip,
  Alert,
} from '@mui/material';
import { DataGrid, GridActionsCellItem } from '@mui/x-data-grid';
import type { GridColDef } from '@mui/x-data-grid';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Search as SearchIcon,
  PersonAdd as PersonAddIcon,
} from '@mui/icons-material';
import RBACGuard from '../../components/rbac/RBACGuard';
import type { User } from '../../types';

export const UserListPage: React.FC = () => {
  const { create, edit, show } = useNavigation();
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);

  // Fetch users with search and pagination
  const { query: { data, isLoading, isError } } = useList<User>({
    resource: 'users',
    filters: searchTerm
      ? [
          {
            field: 'q',
            operator: 'contains',
            value: searchTerm,
          },
        ]
      : [],
    pagination: {
      current: 1,
      pageSize: 25,
    } as any,
    sorters: [
      {
        field: 'created_at',
        order: 'desc',
      },
    ],
  });

  const { mutate: deleteUser } = useDelete();

  const handleDelete = (user: User) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (userToDelete) {
      deleteUser({
        resource: 'users',
        id: userToDelete.id,
      });
      setDeleteDialogOpen(false);
      setUserToDelete(null);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'avatar',
      headerName: '',
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Avatar sx={{ width: 32, height: 32 }}>
          {params.row.first_name?.[0] || params.row.username?.[0] || 'U'}
        </Avatar>
      ),
    },
    {
      field: 'username',
      headerName: 'Username',
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'email',
      headerName: 'Email',
      flex: 1,
      minWidth: 200,
    },
    {
      field: 'full_name',
      headerName: 'Full Name',
      flex: 1,
      minWidth: 180,
      valueGetter: (params: any) =>
        `${params.row.first_name || ''} ${params.row.last_name || ''}`.trim() ||
        params.row.username,
    },
    {
      field: 'roles',
      headerName: 'Roles',
      flex: 1,
      minWidth: 200,
      sortable: false,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {params.row.roles?.slice(0, 2).map((role: any) => (
            <Chip
              key={role.id}
              label={role.name}
              size="small"
              variant="outlined"
              color="primary"
            />
          ))}
          {params.row.roles?.length > 2 && (
            <Chip
              label={`+${params.row.roles.length - 2}`}
              size="small"
              variant="outlined"
              color="default"
            />
          )}
        </Box>
      ),
    },
    {
      field: 'is_active',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.row.is_active ? 'Active' : 'Inactive'}
          color={params.row.is_active ? 'success' : 'default'}
          variant="outlined"
          size="small"
        />
      ),
    },
    {
      field: 'last_login',
      headerName: 'Last Login',
      width: 140,
      valueFormatter: (params: any) =>
        params.value
          ? new Date(params.value).toLocaleDateString()
          : 'Never',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params) => [
        <GridActionsCellItem
          key="view"
          icon={
            <Tooltip title="View Details">
              <ViewIcon />
            </Tooltip>
          }
          label="View"
          onClick={() => show('users', params.id)}
        />,
        <RBACGuard key="edit" permissions={['update:users']}>
          <GridActionsCellItem
            icon={
              <Tooltip title="Edit User">
                <EditIcon />
              </Tooltip>
            }
            label="Edit"
            onClick={() => edit('users', params.id)}
          />
        </RBACGuard>,
        <RBACGuard key="delete" permissions={['delete:users']}>
          <GridActionsCellItem
            icon={
              <Tooltip title="Delete User">
                <DeleteIcon />
              </Tooltip>
            }
            label="Delete"
            onClick={() => handleDelete(params.row)}
            showInMenu
          />
        </RBACGuard>,
      ],
    },
  ];

  if (isError) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load users. Please check your connection and try again.
        </Alert>
      </Box>
    );
  }

  return (
    <RBACGuard permissions={['read:users']}>
      <Box p={3}>
        {/* Header */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={3}
        >
          <Box>
            <Typography variant="h4" gutterBottom>
              User Management
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage system users, roles, and permissions
            </Typography>
          </Box>
          <RBACGuard permissions={['create:users']}>
            <Button
              variant="contained"
              startIcon={<PersonAddIcon />}
              onClick={() => create('users')}
              size="large"
            >
              Add User
            </Button>
          </RBACGuard>
        </Box>

        {/* Search and Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" gap={2} alignItems="center">
              <TextField
                placeholder="Search users by name, email, or username..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ flexGrow: 1 }}
              />
              <Button
                variant="outlined"
                onClick={() => setSearchTerm('')}
                disabled={!searchTerm}
              >
                Clear
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card>
          <DataGrid
            rows={data?.data || []}
            columns={columns}
            loading={isLoading}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: {
                paginationModel: { pageSize: 25 },
              },
            }}
            checkboxSelection
            disableRowSelectionOnClick
            autoHeight
            sx={{
              border: 'none',
              '& .MuiDataGrid-cell': {
                borderBottom: '1px solid #f0f0f0',
              },
              '& .MuiDataGrid-columnHeaders': {
                backgroundColor: '#fafafa',
                borderBottom: '2px solid #e0e0e0',
              },
            }}
          />
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteDialogOpen}
          onClose={() => setDeleteDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Delete User</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to delete the user{' '}
              <strong>{userToDelete?.username}</strong>? This action cannot be
              undone.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={confirmDelete}
              color="error"
              variant="contained"
              startIcon={<DeleteIcon />}
            >
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </RBACGuard>
  );
};

export default UserListPage;