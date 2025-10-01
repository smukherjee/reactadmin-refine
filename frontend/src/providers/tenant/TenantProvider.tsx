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

  const loadTenantData = async () => {
    try {
      const userStr = localStorage.getItem('user');
      const currentTenantId = localStorage.getItem('current_tenant_id');
      
      if (userStr) {
        const user: AuthUser = JSON.parse(userStr);
        setCurrentTenant(user.current_tenant);
        setAvailableTenants(user.available_tenants || []);
        
        // Check if user is superadmin (has access to multiple tenants)
        const isSuperAdmin = user.available_tenants && user.available_tenants.length > 1;
        
        // If user has no current tenant but has available tenants
        if (!user.current_tenant && user.available_tenants && user.available_tenants.length > 0) {
          if (isSuperAdmin) {
            // Superadmin should go to tenant selection page - don't auto-select
            console.log('Superadmin detected, requiring manual tenant selection');
          } else {
            // Regular user - auto-select their only tenant
            console.log('Regular user detected, auto-selecting assigned tenant');
            const firstTenant = user.available_tenants[0];
            await switchTenant(firstTenant.id);
            return;
          }
        }
        
        // If we have a stored tenant ID but no current tenant in user data, try to fetch updated user info
        if (currentTenantId && !user.current_tenant) {
          console.log('Found stored tenant ID but no current tenant, fetching user data');
          try {
            const updatedUser = await apiService.getCurrentUser();
            localStorage.setItem('user', JSON.stringify(updatedUser));
            setCurrentTenant(updatedUser.current_tenant);
            setAvailableTenants(updatedUser.available_tenants || []);
          } catch (error) {
            console.error('Error fetching updated user data:', error);
          }
        }
      } else {
        // No user data in localStorage, try to fetch it if we're authenticated
        const token = localStorage.getItem('access_token');
        if (token) {
          try {
            console.log('No user data found, fetching from API');
            const user = await apiService.getCurrentUser();
            localStorage.setItem('user', JSON.stringify(user));
            setCurrentTenant(user.current_tenant);
            setAvailableTenants(user.available_tenants || []);
            
            if (user.current_tenant) {
              localStorage.setItem('current_tenant_id', user.current_tenant.id);
            }
          } catch (error) {
            console.error('Error fetching user data:', error);
          }
        }
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
      await apiService.switchTenant(tenantId);
      
      // Reload user data to get updated tenant info
      const updatedUser = await apiService.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      setCurrentTenant(updatedUser.current_tenant);
      
      // Refresh the page to reload all data with new tenant context
  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  sessionStorage.setItem('post_login_redirect', currentPath);
      window.location.reload();
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