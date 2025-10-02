import React, { createContext, useContext, useEffect, useState } from 'react';
import type { Tenant, TenantContext as ITenantContext, AuthUser } from '../../types';
import { apiService } from '../../services/api';

const TenantContext = createContext<ITenantContext | null>(null);

interface TenantProviderProps {
  children: React.ReactNode;
}

export const TenantProvider: React.FC<TenantProviderProps> = ({ children }) => {
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [availableTenants, setAvailableTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadTenantData();
  }, []);

  // Also listen for storage changes to reload tenant data when user logs in
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'user' || e.key === 'current_tenant_id') {
        console.log('Storage changed, reloading tenant data:', e.key);
        loadTenantData();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const loadTenantData = async () => {
    try {
      const userStr = localStorage.getItem('user');
      const currentTenantId = localStorage.getItem('current_tenant_id');
      
      console.log('Loading tenant data, user string:', userStr ? 'present' : 'missing');
      console.log('Current tenant ID in storage:', currentTenantId);
      
      if (userStr) {
        const user: AuthUser = JSON.parse(userStr);
        console.log('Parsed user data:', user);
        setCurrentTenant(user.current_tenant || null);
        setAvailableTenants(user.available_tenants || []);
        
        // Check if user is superadmin based on roles and permissions
        const isSuperAdmin = user.is_superuser || 
          (user.roles && user.roles.some((role: any) => 
            role.name === 'superadmin' || 
            role.name === 'admin' ||
            (role.permissions && (role.permissions.includes('*') || role.permissions.includes('tenant:manage')))
          ));
        
        console.log('User role analysis:');
        console.log('- is_superuser:', user.is_superuser);
        console.log('- roles:', user.roles);
        console.log('- isSuperAdmin:', isSuperAdmin);
        console.log('- current_tenant:', user.current_tenant);
        console.log('- available_tenants:', user.available_tenants);

        // If user is authenticated but has no tenant data, try to enhance it
        if ((!user.available_tenants || user.available_tenants.length === 0) && localStorage.getItem('access_token')) {
          console.log('User lacks tenant data but is authenticated, attempting to re-enhance...');
          try {
            const enhancedUser = await apiService.enhanceUserWithTenantData(user);
            localStorage.setItem('user', JSON.stringify(enhancedUser));
            setCurrentTenant(enhancedUser.current_tenant || null);
            setAvailableTenants(enhancedUser.available_tenants || []);
            console.log('Re-enhancement completed:', enhancedUser);
            return; // Exit early since we've updated the data
          } catch (error) {
            console.error('Failed to re-enhance user data:', error);
          }
        }
        
        // If user has no current tenant but has available tenants
        if (!user.current_tenant && user.available_tenants && user.available_tenants.length > 0) {
          console.log('User has no current tenant but has available tenants');
          if (isSuperAdmin && user.available_tenants.length > 1) {
            // Superadmin with multiple tenants should go to tenant selection page
            console.log('Superadmin with multiple tenants detected, requiring manual tenant selection');
          } else {
            // Auto-select for: regular users OR superadmin with single tenant
            console.log(isSuperAdmin ? 'Superadmin with single tenant detected, auto-selecting' : 'Regular user detected, auto-selecting assigned tenant');
            const firstTenant = user.available_tenants[0];
            console.log('Auto-selecting tenant:', firstTenant);
            await switchTenant(firstTenant.id);
            return;
          }
        } else if (user.current_tenant) {
          console.log('User already has current tenant:', user.current_tenant);
        } else {
          console.log('User has no available tenants!');
        }
        
        // If we have a stored tenant ID but no current tenant in user data, 
        // and the user has available tenants, try to match the stored tenant
        if (currentTenantId && !user.current_tenant && user.available_tenants && user.available_tenants.length > 0) {
          console.log('Found stored tenant ID but no current tenant, attempting to match with available tenants');
          const matchedTenant = user.available_tenants.find((t: any) => t.id === currentTenantId);
          if (matchedTenant) {
            console.log('Matched stored tenant:', matchedTenant);
            // Update user data with the matched tenant
            user.current_tenant = matchedTenant;
            localStorage.setItem('user', JSON.stringify(user));
            setCurrentTenant(matchedTenant);
          } else {
            console.log('Stored tenant ID does not match any available tenants, clearing stored tenant');
            localStorage.removeItem('current_tenant_id');
          }
        }
      } else {
        console.log('No user data in localStorage - user needs to login');
      }
    } catch (error) {
      console.error('Error loading tenant data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const switchTenant = async (tenantId: string) => {
    try {
      setIsLoading(true);
      console.log('Switching to tenant:', tenantId);
      
      // Get current user data
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        throw new Error('No user data found');
      }
      
      const user = JSON.parse(userStr);
      console.log('Current user data:', user);
      
      // Find the selected tenant
      const selectedTenant = user.available_tenants?.find((tenant: any) => tenant.id === tenantId);
      if (!selectedTenant) {
        throw new Error(`Tenant ${tenantId} not found in available tenants`);
      }
      
      console.log('Selected tenant:', selectedTenant);
      
      // Update user data with new current tenant (preserve available_tenants)
      const updatedUser = {
        ...user,
        current_tenant: selectedTenant,
        available_tenants: user.available_tenants // Ensure we don't lose the available tenants
      };
      
      // Store updated user data and tenant ID
      localStorage.setItem('user', JSON.stringify(updatedUser));
      localStorage.setItem('current_tenant_id', tenantId);
      
      // Update context state (ensure availableTenants is also maintained)
      setCurrentTenant(selectedTenant);
      setAvailableTenants(user.available_tenants || []);
      
      console.log('Tenant switch completed successfully');
      
      // Don't reload the page - let the context update handle the navigation
    } catch (error) {
      console.error('Error switching tenant:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const contextValue: ITenantContext = {
    currentTenant,
    availableTenants,
    switchTenant,
    isLoading,
  };

  return (
    <TenantContext.Provider value={contextValue}>
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = (): ITenantContext => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};

export default TenantProvider;