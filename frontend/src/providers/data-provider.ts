import { DataProvider } from "@refinedev/core";

const API_URL = "http://localhost:8000";

export const dataProvider: DataProvider = {
  getList: async ({ resource, pagination, filters, sorters, meta }) => {
    const { current = 1, pageSize = 10 } = pagination ?? {};

    const query = {
      _start: (current - 1) * pageSize,
      _end: current * pageSize,
    };

    if (sorters && sorters.length > 0) {
      query._sort = sorters[0].field;
      query._order = sorters[0].order;
    }

    if (filters && filters.length > 0) {
      filters.forEach((filter) => {
        query[filter.field] = filter.value;
      });
    }

    const response = await fetch(`${API_URL}/${resource}?${new URLSearchParams(query)}`);

    if (response.status < 200 || response.status > 299) {
      throw new Error("Failed to fetch data");
    }

    const data = await response.json();
    const total = parseInt(response.headers.get("x-total-count") || "0");

    return {
      data,
      total,
    };
  },

  getOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`);

    if (response.status < 200 || response.status > 299) {
      throw new Error("Failed to fetch data");
    }

    const data = await response.json();

    return {
      data,
    };
  },

  create: async ({ resource, variables }) => {
    const response = await fetch(`${API_URL}/${resource}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(variables),
    });

    if (response.status < 200 || response.status > 299) {
      throw new Error("Failed to create data");
    }

    const data = await response.json();

    return {
      data,
    };
  },

  update: async ({ resource, id, variables }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(variables),
    });

    if (response.status < 200 || response.status > 299) {
      throw new Error("Failed to update data");
    }

    const data = await response.json();

    return {
      data,
    };
  },

  deleteOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "DELETE",
    });

    if (response.status < 200 || response.status > 299) {
      throw new Error("Failed to delete data");
    }

    return {
      data: { id },
    };
  },

  getApiUrl: () => API_URL,
};