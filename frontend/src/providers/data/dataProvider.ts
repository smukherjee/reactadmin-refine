import type { DataProvider } from '@refinedev/core';
import { apiService } from '../../services/api';
import type { ListParams } from '../../types';

export const dataProvider: DataProvider = {
  getList: async ({ resource, pagination, sorters, filters }) => {
    const params: ListParams = {};

    // Handle pagination with proper type safety
    if (pagination) {
      const paginationData = pagination as { current?: number; pageSize?: number };
      params.page = paginationData.current ?? 1;
      params.size = paginationData.pageSize ?? 10;
    }

    // Handle sorting
    if (sorters && sorters.length > 0) {
      const sorter = sorters[0];
      params.sort = sorter.field as string;
      params.order = sorter.order;
    }

    // Handle filters
    if (filters && filters.length > 0) {
      params.filters = {};
      
      filters.forEach((filter) => {
        if (filter.operator === 'contains' || filter.operator === 'eq') {
          if (filter.field === 'q') {
            params.search = filter.value as string;
          } else {
            params.filters![filter.field] = filter.value;
          }
        }
      });
    }

    try {
      const response = await apiService.getList<any>(resource, params);
      
      // Backend returns direct arrays, normalize for Refine
      if (Array.isArray(response)) {
        return {
          data: response,
          total: response.length,
        };
      } else if (response.data && Array.isArray(response.data)) {
        // Handle wrapped responses
        return {
          data: response.data,
          total: response.total || response.data.length,
        };
      } else {
        // Handle single items or unknown formats
        const data = Array.isArray(response) ? response : [response];
        return {
          data,
          total: data.length,
        };
      }
    } catch (error: any) {
      // Enhanced error handling for tenant issues
      if (error?.message?.includes('Tenant ID is required')) {
        throw new Error('Please select a tenant to view this data.');
      }
      console.error(`Error fetching ${resource}:`, error);
      throw error;
    }
  },

  getOne: async ({ resource, id }) => {
    try {
      const data = await apiService.getOne(resource, String(id));
      return { data } as any;
    } catch (error) {
      console.error(`Error fetching ${resource} with id ${id}:`, error);
      throw error;
    }
  },

  create: async ({ resource, variables }) => {
    try {
      const data = await apiService.create(resource, variables as any);
      return { data } as any;
    } catch (error) {
      console.error(`Error creating ${resource}:`, error);
      throw error;
    }
  },

  update: async ({ resource, id, variables }) => {
    try {
      const data = await apiService.update(resource, String(id), variables as any);
      return { data } as any;
    } catch (error) {
      console.error(`Error updating ${resource} with id ${id}:`, error);
      throw error;
    }
  },

  deleteOne: async ({ resource, id }) => {
    try {
      await apiService.delete(resource, String(id));
      return { data: { id } } as any;
    } catch (error) {
      console.error(`Error deleting ${resource} with id ${id}:`, error);
      throw error;
    }
  },

  deleteMany: async ({ resource, ids }) => {
    try {
      const stringIds = ids.map(id => String(id));
      await apiService.deleteMany(resource, stringIds);
      return { data: ids.map(id => ({ id })) } as any;
    } catch (error) {
      console.error(`Error deleting multiple ${resource}:`, error);
      throw error;
    }
  },

  getApiUrl: () => {
    return import.meta.env.VITE_API_URL || '/api/v2';
  },
};

export default dataProvider;