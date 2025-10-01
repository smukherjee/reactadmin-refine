// Test user data retrieval
console.log('=== User Data Debug ===');

// Check localStorage
console.log('Access Token:', localStorage.getItem('access_token') ? 'Present' : 'Missing');
console.log('Current Tenant ID:', localStorage.getItem('current_tenant_id'));
console.log('User Data:', localStorage.getItem('user'));

// Test API call
fetch('/api/v2/async/users/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Current User API Response:', data);
  console.log('User has current_tenant:', !!data.current_tenant);
  console.log('User available_tenants:', data.available_tenants);
})
.catch(error => {
  console.error('Error fetching user:', error);
});

// Test tenants endpoint
fetch('/api/v2/tenants', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Tenants API Response:', data);
})
.catch(error => {
  console.error('Error fetching tenants:', error);
});