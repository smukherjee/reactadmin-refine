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
      if (userStr) {
        const user: AuthUser = JSON.parse(userStr);
        setCurrentTenant(user.current_tenant);
        setAvailableTenants(user.available_tenants || []);
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