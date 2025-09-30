import type { DataProvider } from '@refinedev/core';
import { apiService } from '../../services/api';
import type { ListParams } from '../../types';

export const dataProvider: DataProvider = {
  getList: async ({ resource, pagination, sorters, filters }) => {
    const params: ListParams = {};

    // Handle pagination
    if (pagination) {
      params.page = (pagination as any).current ?? 1;
      params.size = (pagination as any).pageSize ?? 10;
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
      
      return {
        data: response.data,
        total: response.total,
      };
    } catch (error) {
      console.error(`Error fetching ${resource}:`, error);
      throw error;
    }
  },

  getOne: async ({ resource, id }) => {
    try {
      const data = await apiService.getOne(resource, id as string);
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
      const data = await apiService.update(resource, id as string, variables as any);
      return { data } as any;
    } catch (error) {
      console.error(`Error updating ${resource} with id ${id}:`, error);
      throw error;
    }
  },

  deleteOne: async ({ resource, id }) => {
    try {
      await apiService.delete(resource, id as string);
      return { data: { id } } as any;
    } catch (error) {
      console.error(`Error deleting ${resource} with id ${id}:`, error);
      throw error;
    }
  },

  deleteMany: async ({ resource, ids }) => {
    try {
      await apiService.deleteMany(resource, ids as string[]);
      return { data: ids.map(id => ({ id })) } as any;
    } catch (error) {
      console.error(`Error deleting multiple ${resource}:`, error);
      throw error;
    }
  },

  getApiUrl: () => {
    return import.meta.env.VITE_API_URL || 'http://localhost:8000';
  },
};

export default dataProvider;