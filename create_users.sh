#!/bin/bash

BASE_URL="http://localhost:8000"
TENANT_ID="c802c2fe-f0e6-442d-bbd1-52581ee4c24a"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyOGEwNDE5NC04ZDA0LTQyYmItOGNiMS01YTQ0Y2Y3NThjOTYiLCJlbWFpbCI6InN1cGVyYWRtaW5AZXhhbXBsZS5jb20iLCJjbGllbnRfaWQiOiJjODAyYzJmZS1mMGU2LTQ0MmQtYmJkMS01MjU4MWVlNGMyNGEiLCJleHAiOjE3NTkzNzM2NDUsImp0aSI6ImI4ZjYyY2UzLTMxNjYtNDQ3Ni1iNjliLTFkZDBhMDQ3ODQwNiJ9.h1sclDVIoWb-ufiVwvuAmzYpt698mUTze48qukfFgOQ"

HEADERS="-H 'Authorization: Bearer $TOKEN' -H 'Content-Type: application/json'"

echo "Creating roles..."

# Create superadmin role
SUPERADMIN_ROLE=$(curl -s -X POST "$BASE_URL/api/v1/roles" \
  $HEADERS \
  -d '{"name":"superadmin","description":"Super administrator","permissions":["*"],"client_id":"'$TENANT_ID'"}')

if echo "$SUPERADMIN_ROLE" | grep -q '"id"'; then
  SUPERADMIN_ROLE_ID=$(echo "$SUPERADMIN_ROLE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Created superadmin role: $SUPERADMIN_ROLE_ID"
else
  echo "Failed to create superadmin role: $SUPERADMIN_ROLE"
  exit 1
fi

# Create clientadmin role
CLIENTADMIN_ROLE=$(curl -s -X POST "$BASE_URL/api/v1/roles" \
  $HEADERS \
  -d '{"name":"clientadmin","description":"Client administrator","permissions":["users:create","roles:manage"],"client_id":"'$TENANT_ID'"}')

if echo "$CLIENTADMIN_ROLE" | grep -q '"id"'; then
  CLIENTADMIN_ROLE_ID=$(echo "$CLIENTADMIN_ROLE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Created clientadmin role: $CLIENTADMIN_ROLE_ID"
else
  echo "Failed to create clientadmin role: $CLIENTADMIN_ROLE"
  exit 1
fi

# Create user role
USER_ROLE=$(curl -s -X POST "$BASE_URL/api/v1/roles" \
  $HEADERS \
  -d '{"name":"user","description":"Regular user","permissions":["read:protected"],"client_id":"'$TENANT_ID'"}')

if echo "$USER_ROLE" | grep -q '"id"'; then
  USER_ROLE_ID=$(echo "$USER_ROLE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Created user role: $USER_ROLE_ID"
else
  echo "Failed to create user role: $USER_ROLE"
  exit 1
fi

echo "Assigning superadmin role to superadmin user..."
USER_ID="28a04194-8d04-42bb-8cb1-5a44cf758c96"
ASSIGN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/users/$USER_ID/roles" \
  $HEADERS \
  -d '{"role_id": "'$SUPERADMIN_ROLE_ID'"}')

if echo "$ASSIGN_RESP" | grep -q '"message"'; then
  echo "Assigned superadmin role to superadmin user"
else
  echo "Failed to assign role: $ASSIGN_RESP"
fi

echo "Creating admin user..."
ADMIN_USER=$(curl -s -X POST "$BASE_URL/api/v1/users" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123","client_id":"'$TENANT_ID'","first_name":"Admin","last_name":"User"}')

if echo "$ADMIN_USER" | grep -q '"id"'; then
  ADMIN_USER_ID=$(echo "$ADMIN_USER" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Created admin user: $ADMIN_USER_ID"
  # Assign clientadmin role
  ASSIGN_ADMIN=$(curl -s -X POST "$BASE_URL/api/v1/users/$ADMIN_USER_ID/roles" \
    $HEADERS \
    -d '{"role_id": "'$CLIENTADMIN_ROLE_ID'"}')
  if echo "$ASSIGN_ADMIN" | grep -q '"message"'; then
    echo "Assigned clientadmin role to admin user"
  else
    echo "Failed to assign role to admin: $ASSIGN_ADMIN"
  fi
else
  echo "Failed to create admin user: $ADMIN_USER"
fi

echo "Creating regular user..."
REGULAR_USER=$(curl -s -X POST "$BASE_URL/api/v1/users" \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"user123","client_id":"'$TENANT_ID'","first_name":"Regular","last_name":"User"}')

if echo "$REGULAR_USER" | grep -q '"id"'; then
  REGULAR_USER_ID=$(echo "$REGULAR_USER" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Created regular user: $REGULAR_USER_ID"
  # Assign user role
  ASSIGN_REGULAR=$(curl -s -X POST "$BASE_URL/api/v1/users/$REGULAR_USER_ID/roles" \
    $HEADERS \
    -d '{"role_id": "'$USER_ROLE_ID'"}')
  if echo "$ASSIGN_REGULAR" | grep -q '"message"'; then
    echo "Assigned user role to regular user"
  else
    echo "Failed to assign role to regular user: $ASSIGN_REGULAR"
  fi
else
  echo "Failed to create regular user: $REGULAR_USER"
fi

echo "Done!"