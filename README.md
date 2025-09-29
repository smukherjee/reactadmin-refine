# Multitenant Admin Application

This is a comprehensive React-Admin + Refine multitenant application with role-based access control.

## Project Structure

- `frontend/` - React application with Refine framework
- `backend/` - FastAPI backend with PostgreSQL
- `database/` - Database setup and migrations

## Features

- Multitenant architecture with tenant isolation
- JWT-based authentication with OAuth2 support
- Role-based access control (RBAC)
- User management with CRUD operations
- Tenant management (Superadmin only)
- Role and permission management
- Audit logging
- Responsive UI with Material-UI

## Setup Instructions

### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables in `.env` file

5. Create PostgreSQL database:
   ```bash
   createdb multitenant_db
   ```

6. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

## API Endpoints

- `GET /` - Health check
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /users` - List users
- `POST /users` - Create user
- `GET /tenants` - List tenants
- `POST /tenants` - Create tenant
- `GET /roles` - List roles
- `POST /roles` - Create role
- `GET /audit-logs` - List audit logs

## Authentication

The application uses JWT tokens for authentication. Include the token in the Authorization header as `Bearer <token>` for protected endpoints.

## Database Schema

The application uses PostgreSQL with the following main tables:
- `tenants` - Tenant information
- `users` - User accounts
- `roles` - User roles
- `user_roles` - User-role assignments
- `audit_logs` - Activity logging
- `sessions` - User sessions

## Security Features

- Password hashing with bcrypt
- JWT token authentication
- Tenant data isolation
- Audit logging for all actions
- CORS protection
- Input validation

## Development

Both frontend and backend support hot reloading during development.

## Deployment

For production deployment:
1. Set up PostgreSQL database
2. Configure environment variables
3. Build frontend: `npm run build`
4. Deploy backend with uvicorn or gunicorn
5. Serve frontend static files